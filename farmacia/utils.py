import pandas as pd
from datetime import datetime, date
from django.db import transaction
from .models import Medicamento, Lote, Presentacion
import uuid
from collections import defaultdict

class ProcesadorCargaMasiva:
    """Clase para procesar archivos de carga masiva de medicamentos"""
    
    COLUMNAS_REQUERIDAS = [
        'clave', 'descripcion', 'lote', 'cantidad', 'precio',
        'caducidad', 'origen', 'contrato', 'fuente_financiamiento'
    ]
    
    def __init__(self, archivo):
        self.archivo = archivo
        self.resultados = {
            'exitosos': 0,
            'actualizados': 0,
            'errores': [],
            'total': 0,
            'advertencias': []  # Para claves similares
        }
        self.medicamentos_cache = {}
        
    def procesar(self):
        """Procesa el archivo Excel y retorna resultados"""
        try:
            # Leer Excel con tipo explícito para clave (evita conversión numérica)
            df = pd.read_excel(
                self.archivo, 
                engine='openpyxl', 
                dtype={'clave': str, 'lote': str}
            )
            
            # Validar columnas
            error_columnas = self._validar_columnas(df)
            if error_columnas:
                return {'error': error_columnas}
            
            # Limpiar nombres de columnas
            df.columns = df.columns.str.strip().str.lower()
            self.resultados['total'] = len(df)
            
            # Detectar claves similares (advertencia preventiva)
            self._detectar_claves_similares(df)
            
            # FASE 1: Validar y preparar datos
            datos_validados = []
            for index, row in df.iterrows():
                datos_fila = self._validar_fila(index, row)
                if datos_fila:
                    datos_validados.append(datos_fila)
            
            # FASE 2: Procesar en bulk con transaction
            with transaction.atomic():
                self._procesar_medicamentos_bulk(datos_validados)
                self._procesar_lotes_bulk(datos_validados)
            
            return {
                'success': True, 
                'mensaje': 'Carga masiva completada',
                'resultados': self.resultados
            }
            
        except Exception as e:
            return {'error': f'Error al procesar el archivo: {str(e)}'}
    
    def _detectar_claves_similares(self, df):
        """
        Detecta claves muy similares que podrían ser errores de captura.
        Ejemplo: 010.000.0142.00 vs 010.000.0142.01 (presentaciones diferentes)
        """
        claves_unicas = df['clave'].unique()
        claves_procesadas = set()
        
        for i, clave1 in enumerate(claves_unicas):
            clave1_str = str(clave1).strip().upper()
            
            for clave2 in claves_unicas[i+1:]:
                clave2_str = str(clave2).strip().upper()
                
                # Solo comparar si tienen longitudes similares
                if abs(len(clave1_str) - len(clave2_str)) <= 2:
                    similitud = self._calcular_similitud_clave(clave1_str, clave2_str)
                    
                    # Si son >85% similares, generar advertencia
                    if similitud > 0.85 and clave1_str != clave2_str:
                        self.resultados['advertencias'].append({
                            'tipo': 'claves_similares',
                            'clave1': clave1_str,
                            'clave2': clave2_str,
                            'similitud': f"{similitud*100:.1f}%",
                            'mensaje': 'Estas claves son muy similares. Verifica que sean correctas.'
                        })
    
    def _calcular_similitud_clave(self, clave1, clave2):
        """
        Calcula similitud entre dos claves usando ratio de caracteres comunes.
        Retorna valor entre 0 y 1.
        """
        # Remover puntos y espacios para comparación
        c1 = clave1.replace('.', '').replace(' ', '')
        c2 = clave2.replace('.', '').replace(' ', '')
        
        # Contar caracteres en común en posición
        coincidencias = sum(1 for a, b in zip(c1, c2) if a == b)
        longitud_max = max(len(c1), len(c2))
        
        if longitud_max == 0:
            return 0
        
        return coincidencias / longitud_max
    
    def _validar_fila(self, index, row):
        """Valida una fila y retorna datos preparados o None si hay error"""
        try:
            # ===== VALIDACIÓN ESTRICTA DE CLAVE =====
            if pd.isna(row['clave']):
                self.resultados['errores'].append({
                    'fila': index + 2,
                    'clave': 'N/A',
                    'error': 'La clave no puede estar vacía'
                })
                return None
            
            # Limpiar clave preservando formato EXACTO
            clave = str(row['clave']).strip().upper()
            
            # Validar formato de clave (ejemplo: ###.###.####.##)
            # Ajusta esta validación según tu estándar
            if len(clave) < 5:
                self.resultados['errores'].append({
                    'fila': index + 2,
                    'clave': clave,
                    'error': 'Formato de clave inválido (muy corta)'
                })
                return None
            
            # ===== VALIDACIÓN DE LOTE =====
            if pd.isna(row['lote']):
                self.resultados['errores'].append({
                    'fila': index + 2,
                    'clave': clave,
                    'error': 'El lote no puede estar vacío'
                })
                return None
            
            lote_codigo = str(row['lote']).strip().upper()
            
            # ===== VALIDACIÓN DE DESCRIPCIÓN (con caracteres especiales) =====
            descripcion = str(row['descripcion']).strip()
            if pd.isna(row['descripcion']) or descripcion == 'nan' or not descripcion:
                self.resultados['errores'].append({
                    'fila': index + 2,
                    'clave': clave,
                    'error': 'La descripción no puede estar vacía'
                })
                return None
            
            # Validar que descripción tenga contenido real (no solo espacios)
            if len(descripcion) < 5:
                self.resultados['errores'].append({
                    'fila': index + 2,
                    'clave': clave,
                    'error': 'La descripción es demasiado corta'
                })
                return None
            
            # ===== VALIDACIÓN DE CANTIDAD =====
            if not self._validar_cantidad(row['cantidad']):
                self.resultados['errores'].append({
                    'fila': index + 2,
                    'clave': clave,
                    'error': 'Cantidad inválida (debe ser entero positivo)'
                })
                return None
            
            cantidad = int(row['cantidad'])
            
            # ===== VALIDACIÓN DE PRECIO =====
            if not self._validar_precio(row['precio']):
                self.resultados['errores'].append({
                    'fila': index + 2,
                    'clave': clave,
                    'error': 'Precio inválido (debe ser número positivo)'
                })
                return None
            
            precio = float(row['precio'])
            
            # ===== VALIDACIÓN DE FECHA =====
            fecha_caducidad = self._parsear_fecha(row['caducidad'])
            if not fecha_caducidad:
                self.resultados['errores'].append({
                    'fila': index + 2,
                    'clave': clave,
                    'error': 'Fecha inválida. Formatos: DD/MM/YYYY o YYYY-MM-DD'
                })
                return None
            
            # Validar fecha futura (con margen de 30 días por si es reposición urgente)
            if fecha_caducidad <= date.today():
                self.resultados['errores'].append({
                    'fila': index + 2,
                    'clave': clave,
                    'error': f'Fecha de caducidad ya pasó: {fecha_caducidad}'
                })
                return None
            
            # Advertencia si caduca en menos de 6 meses
            dias_hasta_caducidad = (fecha_caducidad - date.today()).days
            if dias_hasta_caducidad < 180:
                self.resultados['advertencias'].append({
                    'tipo': 'caducidad_proxima',
                    'fila': index + 2,
                    'clave': clave,
                    'lote': lote_codigo,
                    'dias': dias_hasta_caducidad,
                    'mensaje': f'Este lote caduca en {dias_hasta_caducidad} días'
                })
            
            # Retornar datos validados
            return {
                'fila': index + 2,  # Para referencia
                'clave': clave,
                'descripcion': descripcion,
                'lote_codigo': lote_codigo,
                'cantidad': cantidad,
                'precio': precio,
                'fecha_caducidad': fecha_caducidad,
                'origen': str(row.get('origen', '')).strip(),
                'contrato': str(row.get('contrato', '')).strip(),
                'fuente': str(row.get('fuente_financiamiento', '')).strip()
            }
            
        except Exception as e:
            self.resultados['errores'].append({
                'fila': index + 2,
                'clave': str(row.get('clave', 'N/A')),
                'error': f'Error inesperado: {str(e)}'
            })
            return None
    
    def _procesar_medicamentos_bulk(self, datos_validados):
        """
        Procesa medicamentos respetando que cada clave es ÚNICA.
        Agrupa por clave exacta para evitar procesamiento redundante.
        """
        # Agrupar por clave EXACTA
        medicamentos_unicos = {}
        
        for dato in datos_validados:
            clave = dato['clave']  # Ya viene limpia y en mayúsculas
            
            # Usar la PRIMERA ocurrencia de cada clave
            if clave not in medicamentos_unicos:
                medicamentos_unicos[clave] = {
                    'descripcion': dato['descripcion'],
                    'precio': dato['precio']
                }
        
        # Obtener medicamentos existentes en BD
        claves_existentes_objs = Medicamento.objects.filter(
            clave__in=medicamentos_unicos.keys()
        )
        
        # Crear diccionario de medicamentos existentes
        medicamentos_existentes = {med.clave: med for med in claves_existentes_objs}
        
        # Separar medicamentos a crear vs actualizar
        medicamentos_a_crear = []
        medicamentos_a_actualizar = []
        
        for clave, datos in medicamentos_unicos.items():
            if clave in medicamentos_existentes:
                # ACTUALIZAR medicamento existente (solo si hay cambios)
                med = medicamentos_existentes[clave]
                actualizado = False
                
                if med.descripcion != datos['descripcion']:
                    med.descripcion = datos['descripcion']
                    actualizado = True
                
                if float(med.costo) != datos['precio']:
                    med.costo = datos['precio']
                    actualizado = True
                
                if actualizado:
                    medicamentos_a_actualizar.append(med)
                
                # Guardar en cache para uso posterior
                self.medicamentos_cache[clave] = med
            else:
                # CREAR nuevo medicamento
                contador = Medicamento.objects.count() + len(medicamentos_a_crear) + 1
                nuevo_med = Medicamento(
                    id=f"MED-{contador:04d}",
                    clave=clave,
                    descripcion=datos['descripcion'],
                    costo=datos['precio'],
                    activo=True
                )
                medicamentos_a_crear.append(nuevo_med)
        
        # Ejecutar bulk operations
        if medicamentos_a_crear:
            Medicamento.objects.bulk_create(medicamentos_a_crear, batch_size=100)
            # Actualizar cache con nuevos medicamentos
            for med in medicamentos_a_crear:
                self.medicamentos_cache[med.clave] = med
        
        if medicamentos_a_actualizar:
            Medicamento.objects.bulk_update(
                medicamentos_a_actualizar, 
                ['descripcion', 'costo'], 
                batch_size=100
            )
    
    def _procesar_lotes_bulk(self, datos_validados):
        """
        Procesa lotes agrupando por (clave_medicamento, lote_codigo).
        Suma cantidades si el par ya existe.
        """
        presentacion = self._obtener_presentacion_default()
        
        # Agrupar por (clave, lote_codigo) - CLAVE DEL ALGORITMO
        lotes_agrupados = defaultdict(lambda: {
            'cantidad_total': 0,
            'datos': None,
            'filas': []
        })
        
        for dato in datos_validados:
            key = (dato['clave'], dato['lote_codigo'])
            lotes_agrupados[key]['cantidad_total'] += dato['cantidad']
            lotes_agrupados[key]['filas'].append(dato['fila'])
            
            # Guardar datos de la primera ocurrencia
            if lotes_agrupados[key]['datos'] is None:
                lotes_agrupados[key]['datos'] = dato
        
        # Obtener lotes existentes en BD
        lotes_existentes = {}
        for (clave, lote_codigo), info in lotes_agrupados.items():
            medicamento = self.medicamentos_cache[clave]
            
            try:
                lote = Lote.objects.get(
                    medicamento=medicamento,
                    lote_codigo=lote_codigo
                )
                lotes_existentes[(clave, lote_codigo)] = lote
            except Lote.DoesNotExist:
                pass
        
        # Separar lotes a crear vs actualizar
        lotes_a_crear = []
        lotes_a_actualizar = []
        
        for (clave, lote_codigo), info in lotes_agrupados.items():
            medicamento = self.medicamentos_cache[clave]
            dato = info['datos']
            cantidad_total = info['cantidad_total']
            
            # Generar advertencia si hay múltiples filas del mismo lote
            if len(info['filas']) > 1:
                self.resultados['advertencias'].append({
                    'tipo': 'lote_duplicado',
                    'clave': clave,
                    'lote': lote_codigo,
                    'filas': info['filas'],
                    'mensaje': f'Lote repetido en {len(info["filas"])} filas. Cantidades sumadas.'
                })
            
            if (clave, lote_codigo) in lotes_existentes:
                # ACTUALIZAR lote existente (SUMAR cantidad)
                lote = lotes_existentes[(clave, lote_codigo)]
                lote.existencia += cantidad_total
                lotes_a_actualizar.append(lote)
                self.resultados['actualizados'] += 1
            else:
                # CREAR nuevo lote
                nuevo_lote = Lote(
                    id=f"LOT-{uuid.uuid4().hex[:10].upper()}",
                    medicamento=medicamento,
                    lote_codigo=lote_codigo,
                    fecha_caducidad=dato['fecha_caducidad'],
                    existencia=cantidad_total,
                    presentacion=presentacion,
                    cpm=0
                )
                lotes_a_crear.append(nuevo_lote)
                self.resultados['exitosos'] += 1
        
        # Ejecutar bulk operations
        if lotes_a_crear:
            Lote.objects.bulk_create(lotes_a_crear, batch_size=100)
        
        if lotes_a_actualizar:
            Lote.objects.bulk_update(
                lotes_a_actualizar, 
                ['existencia'], 
                batch_size=100
            )
    
    def _parsear_fecha(self, fecha):
        """Parsea la fecha de diferentes formatos incluyendo Excel"""
        # Si ya es un objeto date
        if isinstance(fecha, date) and not isinstance(fecha, datetime):
            return fecha
        
        # Si es pandas Timestamp (lo más común al leer Excel)
        if hasattr(fecha, 'date') and callable(fecha.date):
            try:
                return fecha.date()  # Convierte Timestamp a date
            except:
                pass
        
        # Si es datetime de Python
        if isinstance(fecha, datetime):
            return fecha.date()
        
        # Si es string, intentar múltiples formatos
        if isinstance(fecha, str):
            fecha = fecha.strip()
            formatos = [
                '%d/%m/%Y',   # 30/08/2026
                '%Y-%m-%d',   # 2026-08-30
                '%d-%m-%Y',   # 30-08-2026
                '%Y/%m/%d',   # 2026/08/30
                '%d/%m/%y',   # 30/08/26
                '%d%m%Y',     # 30082026 (sin separadores)
            ]
            
            for formato in formatos:
                try:
                    return datetime.strptime(fecha, formato).date()
                except ValueError:
                    continue
        
        # Si pandas lee el Excel como Timestamp (método alternativo)
        try:
            if pd.notna(fecha):
                # Convertir a Timestamp y luego a date
                return pd.to_datetime(fecha).date()
        except:
            pass
        
        return None
        
    def _validar_cantidad(self, cantidad):
        """Valida cantidad como entero positivo"""
        if pd.isna(cantidad):
            return False
        try:
            cantidad_float = float(cantidad)
            return cantidad_float > 0 and cantidad_float == int(cantidad_float)
        except (ValueError, TypeError):
            return False
    
    def _validar_precio(self, precio):
        """Valida precio como número positivo"""
        if pd.isna(precio):
            return False
        try:
            return float(precio) >= 0
        except (ValueError, TypeError):
            return False
    
    def _validar_columnas(self, df):
        """Valida columnas requeridas"""
        columnas_df = [col.strip().lower() for col in df.columns]
        faltantes = [col for col in self.COLUMNAS_REQUERIDAS if col not in columnas_df]
        if faltantes:
            return f"Faltan columnas: {', '.join(faltantes)}"
        return None
    
    def _obtener_presentacion_default(self):
        """Obtiene presentación UNIDAD por defecto"""
        presentacion, _ = Presentacion.objects.get_or_create(
            nombre='UNIDAD',
            defaults={'unidades_por_caja': 1}
        )
        return presentacion
