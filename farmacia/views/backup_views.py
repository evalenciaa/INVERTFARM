"""Copias de seguridad verificables de INVENTFARM.

Las copias nuevas se publican como un conjunto indivisible: base de datos,
archivos ``media`` y un manifiesto firmado. No se restauran archivos SQL
externos ni copias antiguas sin manifiesto, porque hacerlo permitiría ejecutar
instrucciones arbitrarias con las credenciales de MySQL del sistema.
"""
import glob
import gzip
import hashlib
import json
import logging
import os
import shutil
import tarfile
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import sqlparse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from auditoria.services import registrar_evento
from farmacia.decorators import superuser_required
from farmacia.models import ControlRespaldo, TrabajoRespaldo


FORMATO_RESPALDO = 2
PREFIJO_MANIFIESTO = 'backup_'
SUFIJO_MANIFIESTO = '.manifest.json'
MAX_ARCHIVOS_MEDIA_RESTAURACION = 10_000
MAX_BYTES_MEDIA_RESTAURACION = 2 * 1024 * 1024 * 1024
logger = logging.getLogger(__name__)


class CopiaNoRestaurable(Exception):
    """La copia no cumple las garantías necesarias para restaurarse."""


def _firmador_estado_trabajo():
    return signing.TimestampSigner(salt='inventfarm.backups.job-status.v1')


def _token_estado_trabajo(trabajo):
    return _firmador_estado_trabajo().sign_object({'id': str(trabajo.identificador)})


def _trabajo_activo():
    return TrabajoRespaldo.objects.filter(
        estado__in=(TrabajoRespaldo.Estado.PENDIENTE, TrabajoRespaldo.Estado.EJECUTANDO),
    ).order_by('creado_en').first()


def _limpiar_trabajos_atrasados():
    """Libera la cola si un proceso de Windows se interrumpió sin finalizar."""
    limite = timezone.now() - timedelta(
        minutes=getattr(settings, 'BACKUP_JOB_STALE_MINUTES', 240),
    )
    return TrabajoRespaldo.objects.filter(
        estado=TrabajoRespaldo.Estado.EJECUTANDO,
        iniciado_en__lt=limite,
    ).update(
        estado=TrabajoRespaldo.Estado.ERROR,
        etapa='Interrumpido por tiempo excedido',
        error='El proceso no informó resultado antes del límite de seguridad.',
        finalizado_en=timezone.now(),
    )


def _solicitar_trabajo(tipo, *, solicitado_por='', archivo_base_datos=''):
    """Encola una única operación pesada, incluso con varios procesos web."""
    with transaction.atomic():
        # Esta fila se crea con la migración y se bloquea durante la decisión.
        ControlRespaldo.objects.select_for_update().get(clave=1)
        _limpiar_trabajos_atrasados()
        activo = _trabajo_activo()
        if activo:
            return activo, False
        return TrabajoRespaldo.objects.create(
            tipo=tipo,
            solicitado_por=solicitado_por[:150],
            archivo_base_datos=archivo_base_datos[:255],
        ), True


def _actualizar_trabajo(trabajo_id, progreso, etapa, **campos):
    campos.update({'progreso': max(0, min(100, int(progreso))), 'etapa': etapa})
    TrabajoRespaldo.objects.filter(pk=trabajo_id).update(**campos)


def _serializar_trabajo(trabajo, *, incluir_token=False):
    datos = {
        'id': str(trabajo.identificador),
        'tipo': trabajo.tipo,
        'estado': trabajo.estado,
        'progreso': trabajo.progreso,
        'etapa': trabajo.etapa,
        'archivo_base_datos': trabajo.archivo_base_datos,
        'error': trabajo.error,
        'creado_en': trabajo.creado_en.isoformat() if trabajo.creado_en else None,
        'iniciado_en': trabajo.iniciado_en.isoformat() if trabajo.iniciado_en else None,
        'finalizado_en': trabajo.finalizado_en.isoformat() if trabajo.finalizado_en else None,
    }
    if incluir_token:
        datos['token'] = _token_estado_trabajo(trabajo)
    return datos


def _directorio_backups():
    directorio = Path(settings.BACKUP_STORAGE_DIR)
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio.resolve()


def _ruta_backup_segura(filename, *, directorio=None):
    """Resuelve un nombre simple dentro de backups e impide path traversal."""
    if not filename or Path(filename).name != filename:
        return None
    backups_dir = Path(directorio or _directorio_backups()).resolve()
    candidato = (backups_dir / filename).resolve()
    if candidato.parent != backups_dir:
        return None
    return candidato


def _nombre_manifiesto(nombre_bd):
    if not nombre_bd.endswith('.sql.gz'):
        raise CopiaNoRestaurable('El respaldo debe ser un archivo .sql.gz generado por el sistema.')
    return f'{nombre_bd[:-7]}{SUFIJO_MANIFIESTO}'


def _hash_archivo(ruta):
    digest = hashlib.sha256()
    with open(ruta, 'rb') as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
            digest.update(bloque)
    return digest.hexdigest()


def _firmador_manifiesto():
    # La firma se deriva de SECRET_KEY. Una copia alterada o externa no puede
    # pasar la verificación sin conocer el secreto del servidor.
    return signing.Signer(salt='inventfarm.backups.v2')


def _carga_manifiesto(nombre_bd, *, verificar_archivos, directorio=None):
    """Obtiene y valida el manifiesto firmado de una copia v2."""
    nombre_manifiesto = _nombre_manifiesto(nombre_bd)
    ruta_bd = _ruta_backup_segura(nombre_bd, directorio=directorio)
    ruta_manifiesto = _ruta_backup_segura(nombre_manifiesto, directorio=directorio)
    if not ruta_bd or not ruta_bd.is_file() or not ruta_manifiesto or not ruta_manifiesto.is_file():
        raise CopiaNoRestaurable('La copia no tiene un manifiesto verificable.')

    try:
        with open(ruta_manifiesto, encoding='utf-8') as archivo:
            manifiesto = json.load(archivo)
        firma = manifiesto.pop('firma', None)
        if not firma or _firmador_manifiesto().unsign_object(firma) != manifiesto:
            raise CopiaNoRestaurable('La firma del manifiesto no es válida.')
    except (OSError, ValueError, signing.BadSignature) as error:
        raise CopiaNoRestaurable('No fue posible verificar el manifiesto de la copia.') from error

    bd = manifiesto.get('base_datos', {})
    media = manifiesto.get('media', {})
    if (
        manifiesto.get('formato') != FORMATO_RESPALDO
        or bd.get('archivo') != nombre_bd
        or not isinstance(media.get('archivo'), str)
    ):
        raise CopiaNoRestaurable('El manifiesto tiene una estructura no compatible.')

    ruta_media = _ruta_backup_segura(media['archivo'], directorio=directorio)
    if not ruta_media or not ruta_media.is_file() or not media['archivo'].endswith('.tar.gz'):
        raise CopiaNoRestaurable('Falta el respaldo de archivos media asociado.')

    if verificar_archivos:
        for datos, ruta in ((bd, ruta_bd), (media, ruta_media)):
            if datos.get('bytes') != ruta.stat().st_size or datos.get('sha256') != _hash_archivo(ruta):
                raise CopiaNoRestaurable('La copia fue alterada o está incompleta.')
    return manifiesto, ruta_bd, ruta_media


def _estado_restauracion(nombre_bd):
    """Estado ligero para la interfaz; el hash se valida al restaurar."""
    try:
        manifiesto, _, _ = _carga_manifiesto(nombre_bd, verificar_archivos=False)
        return True, 'Copia verificada', manifiesto
    except CopiaNoRestaurable as error:
        return False, str(error), None


def _rutas_del_conjunto(filename):
    """Devuelve los tres archivos de una copia v2, si el nombre pertenece a ella."""
    directorio = _directorio_backups()
    for ruta_manifiesto in directorio.glob(f'{PREFIJO_MANIFIESTO}*{SUFIJO_MANIFIESTO}'):
        try:
            nombre_bd = ruta_manifiesto.name[:-len(SUFIJO_MANIFIESTO)] + '.sql.gz'
            manifiesto, ruta_bd, ruta_media = _carga_manifiesto(nombre_bd, verificar_archivos=False)
            if filename in {nombre_bd, manifiesto['media']['archivo'], ruta_manifiesto.name}:
                return (ruta_bd, ruta_media, ruta_manifiesto)
        except (CopiaNoRestaurable, OSError):
            continue
    return None


def _directorio_remoto():
    """Resuelve el repositorio externo sin mezclarlo con la copia local."""
    configurado = str(getattr(settings, 'BACKUP_REMOTE_DIRECTORY', '')).strip()
    if not configurado:
        return None
    remoto = Path(configurado)
    remoto.mkdir(parents=True, exist_ok=True)
    remoto = remoto.resolve()
    local = _directorio_backups()
    if remoto == local or remoto in local.parents or local in remoto.parents:
        raise CopiaNoRestaurable('El repositorio externo no puede ser la misma ruta que la copia local.')
    unidad_local = os.path.splitdrive(str(local))[0].casefold()
    unidad_remota = os.path.splitdrive(str(remoto))[0].casefold()
    if (
        unidad_local and unidad_remota and unidad_local == unidad_remota
        and not getattr(settings, 'BACKUP_ALLOW_SAME_VOLUME', False)
    ):
        raise CopiaNoRestaurable('El repositorio externo debe estar en otro volumen o recurso de red.')
    return remoto


def _verificar_espacio(directorio):
    libre = shutil.disk_usage(directorio).free
    minimo = int(getattr(settings, 'BACKUP_MIN_FREE_GB', 5)) * 1024 ** 3
    if libre < minimo:
        raise CopiaNoRestaurable(
            f'No hay espacio suficiente para crear la copia. Se requieren al menos '
            f'{getattr(settings, "BACKUP_MIN_FREE_GB", 5)} GB libres.'
        )
    return libre


def _alertar_respaldo(asunto, detalle):
    """Registra y, si TI lo configuró, envía una alerta sin incluir secretos."""
    logger.error('%s: %s', asunto, detalle)
    destinatarios = getattr(settings, 'BACKUP_ALERT_RECIPIENTS', [])
    if destinatarios:
        try:
            send_mail(asunto, detalle, settings.DEFAULT_FROM_EMAIL, destinatarios, fail_silently=False)
        except Exception:
            logger.exception('No fue posible enviar la alerta de respaldos.')


def _copiar_archivo_atomico(origen, destino):
    temporal = destino.with_name(f'.{destino.name}.{uuid.uuid4().hex}.tmp')
    try:
        with open(origen, 'rb') as fuente, open(temporal, 'wb') as copia:
            shutil.copyfileobj(fuente, copia, length=1024 * 1024)
        shutil.copystat(origen, temporal)
        os.replace(temporal, destino)
    except Exception:
        temporal.unlink(missing_ok=True)
        raise


def _replicar_conjunto(datos, actualizar_progreso=None):
    """Replica DB, media y manifiesto a un destino externo de forma atómica."""
    try:
        remoto = _directorio_remoto()
        if remoto is None:
            resultado = {'configurada': False, 'correcta': False, 'detalle': 'Sin repositorio externo configurado.'}
            if getattr(settings, 'BACKUP_REMOTE_REQUIRED', False):
                _alertar_respaldo('INVENTFARM: repositorio externo de respaldo no configurado', resultado['detalle'])
            return resultado
        _verificar_espacio(remoto)
        local = _directorio_backups()
        # El manifiesto se copia al final: así nunca se ofrece un conjunto
        # remoto incompleto como restaurable.
        for indice, nombre in enumerate((datos['database'], datos['media'], datos['manifest']), start=1):
            _copiar_archivo_atomico(local / nombre, remoto / nombre)
            if actualizar_progreso:
                actualizar_progreso(86 + indice * 3, 'Replicando la copia en el repositorio externo')
        limpiar_backups_antiguos(remoto, max_backups=getattr(settings, 'BACKUP_REMOTE_RETENTION', 30))
        return {'configurada': True, 'correcta': True, 'directorio': str(remoto)}
    except Exception as error:
        detalle = f'La copia local se creó, pero la réplica externa falló: {error}'
        _alertar_respaldo('INVENTFARM: fallo de réplica externa de respaldo', detalle)
        return {'configurada': True, 'correcta': False, 'detalle': detalle}


def _estado_repositorio_externo():
    try:
        remoto = _directorio_remoto()
        if remoto is None:
            return {'configurada': False, 'disponible': False, 'detalle': 'No configurado'}
        libre = _verificar_espacio(remoto)
        return {
            'configurada': True, 'disponible': True, 'detalle': str(remoto),
            'espacio_disponible_gb': round(libre / (1024 ** 3), 2),
        }
    except Exception as error:
        return {'configurada': True, 'disponible': False, 'detalle': str(error)}


def _serializar_valor_mysql(conexion, valor):
    """Usa el conversor de PyMySQL en vez de construir literales a mano."""
    if valor is None:
        return 'NULL'
    if isinstance(valor, bytes):
        return f"X'{valor.hex()}'"
    return conexion.escape(valor)


def _crear_archivo_base_datos(ruta_temporal, actualizar_progreso=None):
    """Genera una instantánea SQL comprimida del esquema MySQL completo."""
    import pymysql

    configuracion = settings.DATABASES['default']
    conexion = pymysql.connect(
        host=configuracion['HOST'], port=int(configuracion['PORT']),
        user=configuracion['USER'], password=configuracion['PASSWORD'],
        database=configuracion['NAME'], charset='utf8mb4', autocommit=False,
    )
    cursor = conexion.cursor()
    try:
        cursor.execute('SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        cursor.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT')
        with gzip.open(ruta_temporal, 'wt', encoding='utf-8') as archivo:
            archivo.write('-- INVENTFARM backup verificable v2\n')
            archivo.write('SET FOREIGN_KEY_CHECKS=0;\n\n')
            cursor.execute('SHOW TABLES')
            tablas = cursor.fetchall()
            total_tablas = max(len(tablas), 1)
            for numero_tabla, (tabla,) in enumerate(tablas, start=1):
                archivo.write(f'-- Table structure for `{tabla}`\n')
                archivo.write(f'DROP TABLE IF EXISTS `{tabla}`;\n')
                cursor.execute(f'SHOW CREATE TABLE `{tabla}`')
                archivo.write(f'{cursor.fetchone()[1]};\n\n')
                cursor.execute(f'SELECT * FROM `{tabla}`')
                filas = cursor.fetchall()
                if filas:
                    cursor.execute(f'SHOW COLUMNS FROM `{tabla}`')
                    columnas = [columna[0] for columna in cursor.fetchall()]
                    columnas_sql = '`, `'.join(columnas)
                    for inicio in range(0, len(filas), 100):
                        valores = []
                        for fila in filas[inicio:inicio + 100]:
                            valores.append('(' + ', '.join(
                                _serializar_valor_mysql(conexion, valor) for valor in fila
                            ) + ')')
                        archivo.write(f'INSERT INTO `{tabla}` (`{columnas_sql}`) VALUES\n')
                        archivo.write(',\n'.join(valores))
                        archivo.write(';\n\n')
                if actualizar_progreso:
                    actualizar_progreso(
                        15 + int(numero_tabla / total_tablas * 45),
                        f'Copiando base de datos ({numero_tabla}/{total_tablas} tablas)',
                    )
            archivo.write('SET FOREIGN_KEY_CHECKS=1;\n')
    finally:
        conexion.rollback()
        cursor.close()
        conexion.close()


def _crear_archivo_media(ruta_temporal):
    media_dir = Path(settings.MEDIA_ROOT)
    with tarfile.open(ruta_temporal, 'w:gz') as archivo:
        if media_dir.is_dir():
            archivo.add(media_dir, arcname='media')
        else:
            raiz = tarfile.TarInfo('media')
            raiz.type = tarfile.DIRTYPE
            archivo.addfile(raiz)


def _crear_respaldo(*, motivo='manual', actualizar_progreso=None):
    """Crea y publica un conjunto DB/media/manifiesto de una sola vez."""
    directorio = _directorio_backups()
    _verificar_espacio(directorio)
    marca = datetime.now().strftime('%Y%m%dT%H%M%S%f')
    nombre_bd = f'backup_{marca}.sql.gz'
    nombre_media = f'media_{marca}.tar.gz'
    nombre_manifiesto = _nombre_manifiesto(nombre_bd)
    ruta_bd = directorio / nombre_bd
    ruta_media = directorio / nombre_media
    ruta_manifiesto = directorio / nombre_manifiesto
    temporales = [
        directorio / f'.{nombre_bd}.tmp', directorio / f'.{nombre_media}.tmp',
        directorio / f'.{nombre_manifiesto}.tmp',
    ]
    publicados = []
    publicado_completo = False
    try:
        if actualizar_progreso:
            actualizar_progreso(10, 'Verificando espacio y preparando la copia')
        _crear_archivo_base_datos(temporales[0], actualizar_progreso=actualizar_progreso)
        if actualizar_progreso:
            actualizar_progreso(62, 'Empaquetando archivos media')
        _crear_archivo_media(temporales[1])
        if actualizar_progreso:
            actualizar_progreso(72, 'Calculando integridad de los archivos')
        manifiesto = {
            'formato': FORMATO_RESPALDO,
            'creado_en': datetime.now().isoformat(timespec='seconds'),
            'motivo': motivo,
            'base_datos': {
                'archivo': nombre_bd, 'bytes': temporales[0].stat().st_size,
                'sha256': _hash_archivo(temporales[0]),
            },
            'media': {
                'archivo': nombre_media, 'bytes': temporales[1].stat().st_size,
                'sha256': _hash_archivo(temporales[1]),
            },
        }
        manifiesto['firma'] = _firmador_manifiesto().sign_object(manifiesto)
        with open(temporales[2], 'w', encoding='utf-8', newline='\n') as archivo:
            json.dump(manifiesto, archivo, ensure_ascii=False, sort_keys=True)

        # El manifiesto se publica al final: sin él, el conjunto no se ofrece
        # para restaurar aunque el proceso se interrumpa a mitad.
        for temporal, destino in ((temporales[0], ruta_bd), (temporales[1], ruta_media), (temporales[2], ruta_manifiesto)):
            os.replace(temporal, destino)
            publicados.append(destino)
        publicado_completo = True
        if actualizar_progreso:
            actualizar_progreso(84, 'Publicando el conjunto verificable')
        limpiar_backups_antiguos(directorio, max_backups=getattr(settings, 'BACKUP_LOCAL_RETENTION', 10))
        datos = {
            'database': nombre_bd, 'media': nombre_media, 'manifest': nombre_manifiesto,
            'size_bytes': ruta_bd.stat().st_size,
        }
        datos['replica'] = _replicar_conjunto(datos, actualizar_progreso=actualizar_progreso)
        return datos
    except Exception:
        # Si la copia ya fue publicada, se conserva para recuperación aunque
        # falle la réplica o una comprobación posterior.
        if not publicado_completo:
            for ruta in temporales + publicados:
                try:
                    Path(ruta).unlink(missing_ok=True)
                except OSError:
                    pass
        raise


def _preparar_media_para_restauracion(ruta_media):
    """Valida y extrae media en un directorio privado, sin tocar el actual."""
    padre_media = Path(settings.MEDIA_ROOT).resolve().parent
    padre_media.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='inventfarm-media-', dir=padre_media))
    destino = staging.resolve()
    raiz_media = (destino / 'media').resolve()
    try:
        with tarfile.open(ruta_media, 'r:gz') as archivo:
            miembros = archivo.getmembers()
            if len(miembros) > MAX_ARCHIVOS_MEDIA_RESTAURACION:
                raise CopiaNoRestaurable('El respaldo media contiene demasiados archivos.')
            total = 0
            for miembro in miembros:
                if miembro.issym() or miembro.islnk() or miembro.isdev():
                    raise CopiaNoRestaurable('El respaldo media contiene enlaces no permitidos.')
                if miembro.name != 'media' and not miembro.name.startswith('media/'):
                    raise CopiaNoRestaurable('El respaldo media tiene una ruta no permitida.')
                candidato = (destino / miembro.name).resolve()
                if candidato != raiz_media and raiz_media not in candidato.parents:
                    raise CopiaNoRestaurable('El respaldo media intenta salir de su directorio.')
                total += miembro.size
                if total > MAX_BYTES_MEDIA_RESTAURACION:
                    raise CopiaNoRestaurable('El respaldo media supera el tamaño permitido para restaurar.')
            for miembro in miembros:
                archivo.extract(miembro, path=destino)
        media_extraida = destino / 'media'
        if not media_extraida.is_dir():
            raise CopiaNoRestaurable('El respaldo media no contiene su directorio raíz.')
        return staging, media_extraida
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _restaurar_base_datos(ruta_bd, actualizar_progreso=None, preservar_tablas=()):
    """Ejecuta una copia firmada sin omitir errores de SQL."""
    import pymysql

    configuracion = settings.DATABASES['default']
    with gzip.open(ruta_bd, 'rt', encoding='utf-8') as archivo:
        sentencias = [sentencia.strip() for sentencia in sqlparse.split(archivo.read()) if sentencia.strip()]
    tablas_preservadas = {tabla.casefold() for tabla in preservar_tablas}
    if tablas_preservadas:
        sentencias = [
            sentencia for sentencia in sentencias
            if not any(f'`{tabla}`' in sentencia.casefold() for tabla in tablas_preservadas)
        ]
    if not sentencias:
        raise CopiaNoRestaurable('El respaldo de base de datos no contiene sentencias SQL.')
    conexion = pymysql.connect(
        host=configuracion['HOST'], port=int(configuracion['PORT']),
        user=configuracion['USER'], password=configuracion['PASSWORD'],
        database=configuracion['NAME'], charset='utf8mb4', autocommit=False,
    )
    cursor = conexion.cursor()
    ejecutadas = 0
    try:
        cursor.execute('SET FOREIGN_KEY_CHECKS=0')
        total_sentencias = max(len(sentencias), 1)
        for numero, sentencia in enumerate(sentencias, start=1):
            try:
                cursor.execute(sentencia)
                ejecutadas += 1
            except Exception as error:
                raise CopiaNoRestaurable(f'La restauración falló en la sentencia {numero}.') from error
            if actualizar_progreso and (numero == total_sentencias or numero % 10 == 0):
                actualizar_progreso(
                    62 + int(numero / total_sentencias * 30),
                    f'Restaurando base de datos ({numero}/{total_sentencias} instrucciones)',
                )
        cursor.execute('SET FOREIGN_KEY_CHECKS=1')
        # Ninguna sesión histórica debe sobrevivir a una restauración.
        cursor.execute('DELETE FROM django_session')
        conexion.commit()
        return ejecutadas
    except Exception:
        conexion.rollback()
        raise
    finally:
        try:
            cursor.execute('SET FOREIGN_KEY_CHECKS=1')
        except Exception:
            pass
        cursor.close()
        conexion.close()


def _activar_media_restaurada(staging, media_preparada):
    """Cambia media solo después de que la base de datos fue restaurada."""
    media_actual = Path(settings.MEDIA_ROOT).resolve()
    respaldo_anterior = media_actual.parent / f'.media-previa-{datetime.now().strftime("%Y%m%dT%H%M%S%f")}'
    movido_anterior = False
    try:
        if media_actual.exists():
            os.replace(media_actual, respaldo_anterior)
            movido_anterior = True
        os.replace(media_preparada, media_actual)
    except Exception:
        if movido_anterior and not media_actual.exists():
            os.replace(respaldo_anterior, media_actual)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    if movido_anterior:
        shutil.rmtree(respaldo_anterior, ignore_errors=True)


@never_cache
@login_required
@require_http_methods(['GET'])
@superuser_required
def panel_backups(request):
    """Vista principal del panel de copias de seguridad."""
    directorio = _directorio_backups()
    db_backups, media_backups = [], []
    for ruta in glob.glob(str(directorio / '*.sql*')):
        archivo = Path(ruta)
        if not archivo.is_file():
            continue
        restaurable, razon, _ = _estado_restauracion(archivo.name)
        db_backups.append({
            'filename': archivo.name, 'size': archivo.stat().st_size,
            'size_mb': round(archivo.stat().st_size / (1024 * 1024), 2),
            'date': datetime.fromtimestamp(archivo.stat().st_mtime), 'tipo': 'database',
            'restorable': restaurable, 'restore_reason': razon,
        })
    for ruta in glob.glob(str(directorio / '*.tar*')):
        archivo = Path(ruta)
        if archivo.is_file():
            media_backups.append({
                'filename': archivo.name, 'size': archivo.stat().st_size,
                'size_mb': round(archivo.stat().st_size / (1024 * 1024), 2),
                'date': datetime.fromtimestamp(archivo.stat().st_mtime), 'tipo': 'media',
            })
    db_backups.sort(key=lambda copia: copia['date'], reverse=True)
    media_backups.sort(key=lambda copia: copia['date'], reverse=True)
    total_size = sum(copia['size'] for copia in db_backups + media_backups)
    espacio = shutil.disk_usage(directorio)
    return render(request, 'backups.html', {
        'db_backups': db_backups, 'media_backups': media_backups,
        'total_backups': len(db_backups) + len(media_backups),
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'espacio_disponible_gb': round(espacio.free / (1024 ** 3), 2),
        'ultimo_backup': db_backups[0] if db_backups else None,
        'repositorio_externo': _estado_repositorio_externo(),
        'minimo_espacio_gb': getattr(settings, 'BACKUP_MIN_FREE_GB', 5),
        'trabajo_activo': _trabajo_activo(),
        'trabajos_recientes': TrabajoRespaldo.objects.all()[:8],
    })


@never_cache
@login_required
@require_http_methods(['POST'])
@superuser_required
def crear_backup(request):
    try:
        trabajo, creado = _solicitar_trabajo(
            TrabajoRespaldo.Tipo.CREAR,
            solicitado_por=request.user.get_username(),
        )
        if not creado:
            return JsonResponse({
                'success': False,
                'error': 'Ya hay una operación de respaldos en curso o en espera.',
                'job': _serializar_trabajo(trabajo, incluir_token=True),
            }, status=409)
        registrar_evento('RESPALDO', 'Backup', objeto=str(trabajo.identificador), detalles={
            'operacion': 'encolar_creacion', 'solicitado_por': request.user.get_username(),
        })
        return JsonResponse({
            'success': True,
            'message': 'Copia en espera del proceso de respaldos.',
            'job': _serializar_trabajo(trabajo, incluir_token=True),
        }, status=202)
    except Exception as error:
        _alertar_respaldo('INVENTFARM: fallo al crear respaldo', str(error))
        return JsonResponse({'success': False, 'error': f'Error al crear la copia: {error}'}, status=500)


def limpiar_backups_antiguos(directorio=None, max_backups=None):
    """Elimina conjuntos completos, nunca la BD o media de forma separada."""
    directorio = Path(directorio or _directorio_backups())
    if max_backups is None:
        max_backups = getattr(settings, 'BACKUP_LOCAL_RETENTION', 10)
    conjuntos = []
    for ruta in directorio.glob(f'{PREFIJO_MANIFIESTO}*{SUFIJO_MANIFIESTO}'):
        try:
            nombre_bd = ruta.name[:-len(SUFIJO_MANIFIESTO)] + '.sql.gz'
            manifiesto, ruta_bd, ruta_media = _carga_manifiesto(
                nombre_bd, verificar_archivos=False, directorio=directorio,
            )
            conjuntos.append((ruta.stat().st_mtime, ruta, ruta_bd, ruta_media, manifiesto))
        except (CopiaNoRestaurable, OSError):
            # Una copia corrupta se conserva para diagnóstico y descarga; nunca
            # se borra automáticamente por una suposición.
            continue
    for _, ruta_manifiesto, ruta_bd, ruta_media, _ in sorted(conjuntos, reverse=True)[max_backups:]:
        for ruta in (ruta_manifiesto, ruta_bd, ruta_media):
            try:
                ruta.unlink(missing_ok=True)
            except OSError:
                pass


def registrar_respaldo_creado(datos, *, origen):
    """Registra la creación y deja evidencia explícita de la réplica externa."""
    replica = datos['replica']
    registrar_evento('RESPALDO', 'Backup', objeto=datos['database'], detalles={
        'operacion': 'crear', 'origen': origen,
        'archivo_base_datos': datos['database'], 'archivo_media': datos['media'],
        'archivo_manifiesto': datos['manifest'], 'tamano_bytes': datos['size_bytes'],
        'replica_externa': replica,
    })
    if not replica['correcta']:
        registrar_evento('RESPALDO', 'Backup', objeto=datos['database'], detalles={
            'operacion': 'fallo_replicacion', 'detalle': replica['detalle'],
        })


def _ejecutar_trabajo_respaldo(trabajo_id):
    """Ejecuta una solicitud ya tomada por un único proceso de servidor."""
    trabajo = TrabajoRespaldo.objects.get(pk=trabajo_id)

    def avance(progreso, etapa):
        _actualizar_trabajo(trabajo.pk, progreso, etapa)

    try:
        if trabajo.tipo == TrabajoRespaldo.Tipo.CREAR:
            avance(5, 'Iniciando creación de la copia')
            datos = _crear_respaldo(
                motivo=f'cola_{trabajo.creado_en:%Y%m%dT%H%M%S}',
                actualizar_progreso=avance,
            )
            registrar_respaldo_creado(datos, origen='cola_respaldo')
            if getattr(settings, 'BACKUP_REMOTE_REQUIRED', False) and not datos['replica']['correcta']:
                raise CopiaNoRestaurable(
                    'La copia local se creó, pero falló su réplica externa obligatoria.'
                )
            detalles = {
                'base_datos': datos['database'], 'media': datos['media'],
                'manifiesto': datos['manifest'], 'replica_externa_correcta': datos['replica']['correcta'],
            }
            objeto_auditoria = datos['database']
        elif trabajo.tipo == TrabajoRespaldo.Tipo.RESTAURAR:
            avance(5, 'Verificando la integridad de la copia solicitada')
            manifiesto, ruta_bd, ruta_media = _carga_manifiesto(
                trabajo.archivo_base_datos, verificar_archivos=True,
            )
            avance(15, 'Preparando archivos media en un área segura')
            staging, media_preparada = _preparar_media_para_restauracion(ruta_media)
            try:
                avance(25, 'Creando copia preventiva antes de restaurar')
                emergencia = _crear_respaldo(
                    motivo='antes_de_restaurar',
                    actualizar_progreso=lambda progreso, etapa: avance(25 + int(progreso * .35), etapa),
                )
                registrar_respaldo_creado(emergencia, origen='antes_de_restaurar')
                if getattr(settings, 'BACKUP_REMOTE_REQUIRED', False) and not emergencia['replica']['correcta']:
                    raise CopiaNoRestaurable(
                        'No se pudo proteger la copia preventiva en el repositorio externo.'
                    )
                avance(60, 'Restaurando la base de datos')
                sentencias = _restaurar_base_datos(
                    ruta_bd,
                    actualizar_progreso=avance,
                    # Este historial no forma parte del estado clínico. Se
                    # preserva para terminar el trabajo y poder informar el
                    # resultado tras invalidar todas las sesiones.
                    preservar_tablas=(TrabajoRespaldo._meta.db_table,),
                )
                avance(94, 'Activando los archivos media restaurados')
                _activar_media_restaurada(staging, media_preparada)
                staging = None
            finally:
                if staging:
                    shutil.rmtree(staging, ignore_errors=True)
            detalles = {
                'base_datos': trabajo.archivo_base_datos,
                'media': manifiesto['media']['archivo'],
                'sentencias_ejecutadas': sentencias,
                'respaldo_previo': emergencia['database'],
                'sesiones_invalidadas': True,
            }
            objeto_auditoria = trabajo.archivo_base_datos
            registrar_evento('RESPALDO', 'Backup', objeto=objeto_auditoria, detalles={
                'operacion': 'restaurar', **detalles,
            })
        else:
            raise CopiaNoRestaurable('El tipo de trabajo solicitado no es válido.')

        _actualizar_trabajo(
            trabajo.pk, 100, 'Operación completada', estado=TrabajoRespaldo.Estado.COMPLETADO,
            detalles=detalles, error='', finalizado_en=timezone.now(),
        )
        return TrabajoRespaldo.objects.get(pk=trabajo.pk)
    except Exception as error:
        logger.exception('Falló el trabajo de respaldo %s.', trabajo.identificador)
        _alertar_respaldo('INVENTFARM: fallo en trabajo de respaldo', str(error))
        _actualizar_trabajo(
            trabajo.pk, trabajo.progreso, 'Operación no completada',
            estado=TrabajoRespaldo.Estado.ERROR,
            error=str(error)[:4000], finalizado_en=timezone.now(),
        )
        return TrabajoRespaldo.objects.get(pk=trabajo.pk)
    finally:
        # La pausa de mantenimiento no debe permanecer en caché después de
        # que una restauración haya terminado o fallado.
        cache.delete('inventfarm:restauracion_activa')


def procesar_siguiente_trabajo_respaldo():
    """Toma como máximo un trabajo pendiente; lo usan tareas de Windows."""
    with transaction.atomic():
        ControlRespaldo.objects.select_for_update().get(clave=1)
        _limpiar_trabajos_atrasados()
        if TrabajoRespaldo.objects.filter(estado=TrabajoRespaldo.Estado.EJECUTANDO).exists():
            return None
        trabajo = TrabajoRespaldo.objects.select_for_update().filter(
            estado=TrabajoRespaldo.Estado.PENDIENTE,
        ).order_by('creado_en').first()
        if not trabajo:
            return None
        trabajo.estado = TrabajoRespaldo.Estado.EJECUTANDO
        trabajo.progreso = 1
        trabajo.etapa = 'Asignado al proceso de respaldos'
        trabajo.iniciado_en = timezone.now()
        trabajo.save(update_fields=('estado', 'progreso', 'etapa', 'iniciado_en'))
        trabajo_id = trabajo.pk
    return _ejecutar_trabajo_respaldo(trabajo_id)


@never_cache
@login_required
@require_http_methods(['GET'])
@superuser_required
def descargar_backup(request, filename):
    ruta = _ruta_backup_segura(filename)
    if ruta is None or not ruta.is_file():
        return HttpResponse('Archivo no encontrado', status=404)
    registrar_evento('RESPALDO', 'Backup', objeto=filename, detalles={'operacion': 'descargar'})
    return FileResponse(open(ruta, 'rb'), as_attachment=True, filename=filename)


@never_cache
@login_required
@require_http_methods(['POST'])
@superuser_required
def eliminar_backup(request, filename):
    ruta = _ruta_backup_segura(filename)
    if ruta is None or not ruta.is_file():
        return JsonResponse({'success': False, 'error': 'Archivo no encontrado'}, status=404)
    if _trabajo_activo():
        return JsonResponse({
            'success': False,
            'error': 'No se pueden eliminar copias mientras hay una operación de respaldos en curso.',
        }, status=409)
    try:
        conjunto = _rutas_del_conjunto(filename)
        rutas = conjunto or (ruta,)
        for archivo in rutas:
            archivo.unlink(missing_ok=True)
        registrar_evento('RESPALDO', 'Backup', objeto=filename, detalles={
            'operacion': 'eliminar', 'conjunto_completo': bool(conjunto),
            'archivos_eliminados': [archivo.name for archivo in rutas],
        })
        mensaje = 'Conjunto de respaldo eliminado correctamente.' if conjunto else f'Archivo "{filename}" eliminado correctamente.'
        return JsonResponse({'success': True, 'message': mensaje})
    except OSError as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=500)


@never_cache
@login_required
@require_http_methods(['POST'])
@superuser_required
def restaurar_backup(request):
    nombre_bd = request.POST.get('filename', '')
    try:
        # Rechazar desde el inicio nombres no verificables. El hash completo
        # se vuelve a comprobar dentro del proceso antes de tocar la base.
        _carga_manifiesto(nombre_bd, verificar_archivos=False)
        trabajo, creado = _solicitar_trabajo(
            TrabajoRespaldo.Tipo.RESTAURAR,
            solicitado_por=request.user.get_username(),
            archivo_base_datos=nombre_bd,
        )
        if not creado:
            return JsonResponse({
                'success': False,
                'error': 'Ya hay una operación de respaldos en curso o en espera.',
                'job': _serializar_trabajo(trabajo, incluir_token=True),
            }, status=409)
        registrar_evento('RESPALDO', 'Backup', objeto=nombre_bd, detalles={
            'operacion': 'encolar_restauracion', 'solicitado_por': request.user.get_username(),
        })
        return JsonResponse({
            'success': True,
            'message': 'Restauración en espera del proceso de respaldos.',
            'job': _serializar_trabajo(trabajo, incluir_token=True),
        }, status=202)
    except CopiaNoRestaurable as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)
    except Exception:
        return JsonResponse({
            'success': False,
            'error': 'La restauración no se completó. Se conservó una copia previa cuando fue posible; revise la bitácora y contacte a TI.',
        }, status=500)


@never_cache
@require_http_methods(['GET'])
def estado_trabajo_respaldo(request, identificador):
    """Consulta de avance; tras restaurar acepta un recibo firmado temporal."""
    token = request.GET.get('token', '')
    autorizado_por_token = False
    if token:
        try:
            datos_token = _firmador_estado_trabajo().unsign_object(
                token,
                max_age=getattr(settings, 'BACKUP_JOB_STATUS_TOKEN_AGE', 3600),
            )
            autorizado_por_token = datos_token.get('id') == str(identificador)
        except (signing.BadSignature, ValueError, TypeError):
            autorizado_por_token = False
    if not autorizado_por_token and not (
        request.user.is_authenticated and request.user.is_superuser
    ):
        return JsonResponse({'success': False, 'error': 'No autorizado.'}, status=403)
    try:
        trabajo = TrabajoRespaldo.objects.get(identificador=identificador)
    except (TrabajoRespaldo.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': 'Trabajo no encontrado.'}, status=404)
    return JsonResponse({'success': True, 'job': _serializar_trabajo(trabajo)})


@never_cache
@login_required
@require_http_methods(['POST'])
@superuser_required
def subir_backup(request):
    """La importación de copias externas queda deshabilitada por seguridad."""
    return JsonResponse({
        'success': False,
        'error': 'La importación de copias externas está deshabilitada. Solo se restauran copias verificables generadas por INVENTFARM.',
    }, status=410)
