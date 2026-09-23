"""
farmacia/views/inventario_views.py
Vistas de gestión de inventario: farmacia_g, alertas, lotes, CPM,
inventario general, registro de medicamentos.
"""
import json
import logging
import uuid
from datetime import date, timedelta, datetime
from decimal import Decimal
from math import ceil
from xml.sax.saxutils import escape as escape_xml

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum, Q, F, Value, IntegerField, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from ..decorators import group_required
from ..cpm import calcular_estado_inventario
from ..forms import MedicamentoForm
from ..models import (
    Lote, Medicamento, Presentacion, CPMMedicamento, CatalogoAntibioticosWHO,
    RecetaMedicamento,
)

logger = logging.getLogger(__name__)


def _consumo_antibioticos_por_medicamento(fecha_inicio, fecha_fin_exclusiva):
    """Devuelve las piezas surtidas por receta o colectivo en el periodo."""
    consumos = (
        RecetaMedicamento.objects
        .filter(
            medicamento__es_antibiotico=True,
            medicamento__activo=True,
            receta__fecha_surtido__gte=fecha_inicio,
            receta__fecha_surtido__lt=fecha_fin_exclusiva,
        )
        .values('medicamento_id')
        .annotate(consumo_total=Sum('cantidad_surtida'))
    )
    return {
        item['medicamento_id']: item['consumo_total'] or 0
        for item in consumos
    }


def _resumen_ddd_aware(totales_ddd):
    """Construye las sumatorias y porcentajes AWaRe sin redondear el total."""
    total = sum(totales_ddd.values(), Decimal('0'))
    etiquetas = {
        'Access': '∑DDD Access',
        'Watch': '∑DDD Watch',
        'Reserve': '∑DDD Reserve',
    }
    filas = []

    for categoria in ('Access', 'Watch', 'Reserve'):
        sumatoria = totales_ddd[categoria]
        porcentaje = (
            (sumatoria / total) * Decimal('100')
            if total > 0 else Decimal('0')
        )
        filas.append({
            'categoria': categoria,
            'etiqueta': etiquetas[categoria],
            'sumatoria': round(sumatoria, 4),
            'porcentaje': round(porcentaje, 2),
        })

    return filas, round(total, 4)


def _calcular_ddd_antibiotico(medicamento, cantidad_surtida):
    gramos_por_pieza = medicamento.gramos_por_pieza or Decimal('0')
    valor_atc = medicamento.valor_atc or Decimal('0')
    gramos_consumidos = Decimal(cantidad_surtida or 0) * gramos_por_pieza
    if valor_atc <= 0:
        return Decimal('0')
    return gramos_consumidos / valor_atc


def tiene_acceso_farmacia(user):
    return (
        user.is_authenticated and (
            user.is_superuser
            or user.rol in ['ADMIN', 'FARMACIA']
            or user.groups.filter(name__in=[
                'Administradores', 'Administrador',
                'Capturista_Farmacia', 'Supervisor_Farmacia'
            ]).exists()
        )
    )


@login_required
@require_http_methods(['GET'])
@permission_required('farmacia.view_lote', raise_exception=True)
def alertas(request):
    usuario = request.user
    es_admin = usuario.is_superuser or usuario.groups.filter(name='Administrador').exists()
    es_capturista = usuario.groups.filter(name='Capturista').exists()

    medicamento_id = request.GET.get('medicamento')
    color_filtro = request.GET.get('color')

    lotes = Lote.objects.all().select_related('medicamento')

    if medicamento_id:
        lotes = lotes.filter(medicamento_id=medicamento_id)

    if color_filtro:
        hoy = timezone.now().date()
        if color_filtro == 'verde':
            lotes = lotes.filter(fecha_caducidad__gt=hoy + timedelta(days=365))
        elif color_filtro == 'amarillo':
            lotes = lotes.filter(fecha_caducidad__gt=hoy + timedelta(days=180),
                                  fecha_caducidad__lte=hoy + timedelta(days=365))
        elif color_filtro == 'rojo':
            lotes = lotes.filter(fecha_caducidad__lte=hoy + timedelta(days=180))

    medicamentos = Medicamento.objects.all()
    context = {
        'lotes': lotes,
        'medicamentos': medicamentos,
        'es_admin': es_admin,
        'es_capturista': es_capturista,
    }
    return render(request, 'alertas.html', context)


@login_required
@require_http_methods(["POST", "GET"])
@permission_required('farmacia.change_lote', raise_exception=True)
def editar_lote(request, lote_id):
    es_admin = (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Administrador', 'Administradores']).exists()
    )
    if not es_admin:
        return JsonResponse({'success': False, 'error': 'No autorizado'}, status=403)

    lote = get_object_or_404(Lote, id=lote_id)

    if request.method == 'POST':
        try:
            cpm = request.POST.get('cpm')
            presentacion_id = request.POST.get('presentacion')
            if cpm:
                lote.cpm = float(cpm)
            if presentacion_id:
                presentacion = get_object_or_404(Presentacion, id=presentacion_id)
                lote.presentacion = presentacion

            lote_codigo = request.POST.get('lote_codigo')
            existencia = request.POST.get('existencia')
            fecha_caducidad = request.POST.get('fecha_caducidad')
            if lote_codigo:
                lote.lote_codigo = lote_codigo
            if existencia is not None and existencia != '':
                lote.existencia = int(existencia)
            if fecha_caducidad:
                lote.fecha_caducidad = fecha_caducidad

            lote.save()
            return JsonResponse({'success': True, 'mensaje': 'Lote actualizado correctamente'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({
        'id': lote.id,
        'medicamento': f"{lote.medicamento.clave} - {lote.medicamento.descripcion}",
        'cpm': str(lote.cpm),
        'presentacion_id': lote.presentacion.id if lote.presentacion else '',
        'lote_codigo': lote.lote_codigo,
        'existencia': lote.existencia,
        'fecha_caducidad': lote.fecha_caducidad.strftime('%Y-%m-%d')
    })


@never_cache
@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
@permission_required('farmacia.change_lote', raise_exception=True)
def farmacia_g(request):
    if request.method == 'POST':
        medicamento_id = request.POST.get('medicamento')
        nueva_descripcion = request.POST.get('descripcion')
        lote_codigo = request.POST.get('lote_codigo')
        existencia = request.POST.get('existencia')
        presentacion_id = request.POST.get('presentacion')

        if medicamento_id and nueva_descripcion:
            medicamento = Medicamento.objects.get(id=medicamento_id)
            medicamento.descripcion = nueva_descripcion
            medicamento.save()
            return JsonResponse({'status': 'success'})

        if medicamento_id and lote_codigo and existencia and presentacion_id:
            medicamento = Medicamento.objects.get(id=medicamento_id)
            presentacion = Presentacion.objects.get(id=presentacion_id)
            lote_id = str(uuid.uuid4())[:15]
            Lote.objects.create(
                id=lote_id, medicamento=medicamento, lote_codigo=lote_codigo,
                existencia=int(existencia), presentacion=presentacion,
                fecha_caducidad=date.today() + timedelta(days=365), cpm=0
            )
            return redirect('farmacia_g')

    lotes = (
        Lote.objects
        .select_related('medicamento', 'presentacion')
        .annotate(
            costo_total=ExpressionWrapper(
                F('existencia') * F('costo_unitario'),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            )
        )
        .order_by('fecha_caducidad')
    )

    presentaciones = Presentacion.objects.all()
    hoy = date.today()
    lotes_con_dias = []
    vigentes = por_vencer = criticos = 0

    for lote in lotes:
        dias = (lote.fecha_caducidad - hoy).days
        lote.dias_para_caducidad = dias
        lotes_con_dias.append(lote)
        if dias > 365:
            vigentes += 1
        elif dias >= 180:
            por_vencer += 1
        else:
            criticos += 1

    medicamentos = Medicamento.objects.filter(activo=True)
    es_admin = (
        request.user.is_superuser or
        request.user.groups.filter(name__in=['Administrador', 'Administradores']).exists()
    )

    context = {
        'lotes': lotes_con_dias,
        'medicamentos': medicamentos,
        'presentaciones': presentaciones,
        'vigentes': vigentes,
        'por_vencer': por_vencer,
        'criticos': criticos,
        'es_admin': es_admin,
    }
    return render(request, 'farmacia_g.html', context)


@login_required
@require_http_methods(['POST'])
@permission_required('farmacia.change_medicamento', raise_exception=True)
def guardar_descripcion(request):
    if request.method == 'POST':
        medicamento_id = request.POST.get('medicamento_id')
        descripcion = request.POST.get('descripcion')
        if medicamento_id and descripcion:
            try:
                medicamento = Medicamento.objects.get(id=medicamento_id)
                medicamento.descripcion = descripcion
                medicamento.save()
                return JsonResponse({'status': 'success'})
            except Medicamento.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Medicamento no encontrado'})
    return JsonResponse({'status': 'error', 'message': 'Datos inválidos'})


@login_required(login_url='login')
@require_http_methods(['GET'])
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia', 'Enfermero', 'Jefe de Enfermería', 'Médico')
@permission_required('farmacia.view_lote', raise_exception=True)
def inventario_general(request):
    """Vista de inventario general - suma de existencias por medicamento"""
    busqueda = request.GET.get('busqueda', '').strip()
    inventario = Lote.objects.values(
        'medicamento__id', 'medicamento__clave', 'medicamento__descripcion',
    ).annotate(
        existencia_total=Sum('existencia'),
        cpm_medicamento=Coalesce(
            F('medicamento__cpm_medicamento__valor'),
            Value(0), output_field=IntegerField()
        )
    ).order_by('medicamento__descripcion')

    if busqueda:
        inventario = inventario.filter(
            Q(medicamento__descripcion__icontains=busqueda) |
            Q(medicamento__clave__icontains=busqueda)
        )

    excedentes = stock_adecuado = stock_bajo = desabasto = 0
    inventario_con_porcentaje = []
    for item in inventario:
        existencia = item['existencia_total']
        cpm = item['cpm_medicamento']
        indicadores = calcular_estado_inventario(existencia, cpm)
        item.update(indicadores)
        if indicadores['estado'] == 'excedente':
            excedentes += 1
        elif indicadores['estado'] == 'adecuado':
            stock_adecuado += 1
        elif indicadores['estado'] == 'bajo':
            stock_bajo += 1
        else:
            desabasto += 1
        inventario_con_porcentaje.append(item)

    context = {
        'inventario': inventario_con_porcentaje,
        'busqueda_actual': busqueda,
        'total_medicamentos': len(inventario_con_porcentaje),
        'excedentes': excedentes,
        'stock_adecuado': stock_adecuado,
        'stock_bajo': stock_bajo,
        'desabasto': desabasto,
    }
    return render(request, 'inv_gene_f.html', context)


@require_http_methods(['POST'])
@login_required
@permission_required('farmacia.change_cpmmedicamento', raise_exception=True)
def editar_cpm_medicamento(request):
    try:
        data = json.loads(request.body)
        medicamento_id = data.get('medicamento_id')
        nuevo_cpm = data.get('cpm')
        if not medicamento_id or nuevo_cpm is None:
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        try:
            nuevo_cpm = int(nuevo_cpm)
            if nuevo_cpm < 0:
                return JsonResponse({'error': 'El CPM no puede ser negativo'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'El CPM debe ser un número válido'}, status=400)

        medicamento = Medicamento.objects.get(id=medicamento_id)
        cpm_obj, created = CPMMedicamento.objects.get_or_create(
            medicamento=medicamento,
            defaults={'valor': nuevo_cpm, 'actualizado_por': request.user}
        )
        if not created:
            cpm_obj.valor = nuevo_cpm
            cpm_obj.actualizado_por = request.user
            cpm_obj.save()

        return JsonResponse({'success': True, 'message': 'CPM actualizado correctamente', 'nuevo_cpm': nuevo_cpm})
    except Medicamento.DoesNotExist:
        return JsonResponse({'error': 'Medicamento no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['DELETE', 'POST'])
@permission_required('farmacia.delete_lote', raise_exception=True)
def eliminar_lote(request, lote_id):
    try:
        lote = get_object_or_404(Lote, id=lote_id)
        if lote.existencia > 0:
            return JsonResponse({
                'success': False, 'tipo': 'error_existencia',
                'error': f'No se puede eliminar el lote {lote.lote_codigo}',
                'detalle': f'El lote tiene {lote.existencia} unidades en existencia.',
                'solucion': 'Para eliminar este lote, primero debes registrar salidas hasta que la existencia sea 0.',
                'existencia': lote.existencia
            }, status=400)
        lote.delete()
        return JsonResponse({'success': True, 'mensaje': f'Lote {lote.lote_codigo} eliminado correctamente'})
    except Exception as e:
        return JsonResponse({'success': False, 'tipo': 'error_sistema', 'error': 'Error del sistema', 'detalle': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
@permission_required('farmacia.change_cpmmedicamento', raise_exception=True)
def actualizar_cpm(request):
    """Alias de editar_cpm_medicamento para compatibilidad con URLs existentes"""
    return editar_cpm_medicamento(request)


@login_required
@require_http_methods(['POST'])
@permission_required('farmacia.delete_medicamento', raise_exception=True)
def eliminar_medicamento(request):
    try:
        data = json.loads(request.body)
        medicamento_id = data.get('medicamento_id')
        medicamento = get_object_or_404(Medicamento, id=medicamento_id)
        if Lote.objects.filter(medicamento=medicamento, existencia__gt=0).exists():
            return JsonResponse({'success': False, 'error': 'No se puede eliminar: el medicamento tiene existencias en lotes activos'}, status=400)
        medicamento.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@never_cache
@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
@permission_required('farmacia.add_medicamento', raise_exception=True)
def registro_medicamento(request):
    """Vista para registrar un nuevo medicamento"""
    from django.contrib import messages

    if request.method == 'POST':
        form = MedicamentoForm(request.POST)

        if form.is_valid():
            try:
                medicamento = form.save(commit=False)

                medicamento.clave = medicamento.clave.strip().upper()
                medicamento.descripcion = medicamento.descripcion.strip()
                medicamento.activo = True

                if medicamento.costo is None:
                    medicamento.costo = 0.00

                if not medicamento.codigo_barras:
                    medicamento.codigo_barras = None

                if not medicamento.proveedor_id:
                    medicamento.proveedor = None

                if not medicamento.presentacion_id:
                    medicamento.presentacion = None

                medicamento.save()

                messages.success(
                    request,
                    f'✓ Medicamento "{medicamento.clave}" '
                    'registrado correctamente.'
                )

                return redirect('farmacia_g')

            except Exception as e:
                messages.error(
                    request,
                    f'Error al registrar medicamento: {str(e)}'
                )
        else:
            messages.error(
                request,
                'Error en el formulario. Verifica los datos.'
            )
    else:
        form = MedicamentoForm()

    return render(
        request,
        'registro_medicamento.html',
        {'form': form}
    )


@login_required
@require_http_methods(['GET'])
@permission_required('farmacia.add_medicamento', raise_exception=True)
def buscar_catalogo_antibiotico(request):
    codigo_atc = request.GET.get('codigo_atc', '').strip().upper()

    if not codigo_atc:
        return JsonResponse({'encontrado': False, 'error': 'Código ATC requerido'}, status=400)

    item = CatalogoAntibioticosWHO.objects.filter(codigo_atc=codigo_atc).first()

    if not item:
        return JsonResponse({'encontrado': False})

    return JsonResponse({
        'encontrado': True,
        'codigo_atc': item.codigo_atc,
        'categoria_aware': item.categoria_aware,
        'valor_atc': item.valor_atc,
        'fuente_valor_atc': item.fuente_valor_atc,
    })


@login_required
@require_http_methods(['GET'])
@permission_required('farmacia.view_reportes', raise_exception=True)
def inventario_antibioticos(request):
    hoy = timezone.now().date()

    mes_param = request.GET.get('mes')
    if mes_param:
        try:
            fecha_inicio = datetime.strptime(mes_param, '%Y-%m').date().replace(day=1)
        except ValueError:
            fecha_inicio = hoy.replace(day=1)
    else:
        fecha_inicio = hoy.replace(day=1)

    if fecha_inicio.month == 12:
        siguiente_mes = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1, day=1)
    else:
        siguiente_mes = fecha_inicio.replace(month=fecha_inicio.month + 1, day=1)

    antibioticos_qs = (
        Medicamento.objects
        .filter(es_antibiotico=True, activo=True)
        .order_by('descripcion')
    )

    consumos_map = _consumo_antibioticos_por_medicamento(
        fecha_inicio, siguiente_mes
    )

    antibioticos = []
    total_access = 0
    total_watch = 0
    total_reserve = 0
    totales_ddd = {
        'Access': Decimal('0'),
        'Watch': Decimal('0'),
        'Reserve': Decimal('0'),
    }

    for med in antibioticos_qs:
        gramos_por_pieza = med.gramos_por_pieza or Decimal('0')
        valor_atc = med.valor_atc or Decimal('0')
        consumo_total = consumos_map.get(med.id, 0)

        consumo_gramos = Decimal(consumo_total) * gramos_por_pieza
        ddd_consumidas = (
            consumo_gramos / valor_atc
            if valor_atc > 0 else Decimal('0')
        )

        aware = (med.categoria_aware or '').strip()

        if aware == 'Access':
            total_access += 1
        elif aware == 'Watch':
            total_watch += 1
        elif aware == 'Reserve':
            total_reserve += 1

        if aware in totales_ddd:
            totales_ddd[aware] += ddd_consumidas

        antibioticos.append({
            'id': med.id,
            'clave': med.clave,
            'descripcion': med.descripcion,
            'via_administracion': med.via_administracion or '',
            'codigo_atc': med.codigo_atc or '',
            'aware': aware or 'N/A',
            'gramos_por_pieza': gramos_por_pieza,
            'valor_atc': valor_atc,
            'consumo_total': consumo_total,
            'ddd_consumidas': round(ddd_consumidas, 2),
        })

    resumen_aware, total_ddd_antibioticos = _resumen_ddd_aware(totales_ddd)
    datos_grafica_aware = {
        'etiquetas': [fila['categoria'] for fila in resumen_aware],
        'sumatorias': [float(fila['sumatoria']) for fila in resumen_aware],
        'porcentajes': [float(fila['porcentaje']) for fila in resumen_aware],
    }

    context = {
        'user': request.user,
        'antibioticos': antibioticos,
        'total_antibioticos': len(antibioticos),
        'total_access': total_access,
        'total_watch': total_watch,
        'total_reserve': total_reserve,
        'resumen_aware': resumen_aware,
        'total_ddd_antibioticos': total_ddd_antibioticos,
        'datos_grafica_aware': datos_grafica_aware,
        'mes_actual': fecha_inicio.strftime('%Y-%m'),
        'fecha_inicio': fecha_inicio,
        'fecha_fin': siguiente_mes,
    }

    return render(request, 'inventario_antibioticos.html', context)

    
@login_required
@require_http_methods(['GET'])
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
@permission_required('farmacia.view_reportes', raise_exception=True)
def api_reportes_antibioticos_ddd(request):
    """
    Calcula consumo real, gramos consumidos y DDD por medicamento antibiótico,
    filtrado por periodo (fecha_inicio / fecha_fin).
    """
    try:
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin.replace(day=1)

        if request.GET.get('fecha_inicio'):
            fecha_inicio = datetime.strptime(request.GET.get('fecha_inicio'), '%Y-%m-%d').date()
        if request.GET.get('fecha_fin'):
            fecha_fin = datetime.strptime(request.GET.get('fecha_fin'), '%Y-%m-%d').date()

        antibioticos = Medicamento.objects.filter(es_antibiotico=True, activo=True)

        consumo_por_medicamento = (
            RecetaMedicamento.objects
            .filter(
                medicamento__es_antibiotico=True,
                receta__fecha_surtido__range=[fecha_inicio, fecha_fin]
            )
            .values('medicamento_id')
            .annotate(total_consumo=Sum('cantidad_surtida'))
        )

        consumo_map = {
            item['medicamento_id']: item['total_consumo'] or 0
            for item in consumo_por_medicamento
        }

        datos = []
        for med in antibioticos:
            consumo_real = consumo_map.get(med.id, 0)

            gramos_por_pieza = float(med.gramos_por_pieza) if med.gramos_por_pieza is not None else None
            valor_atc = float(med.valor_atc) if med.valor_atc is not None else None

            gramos_consumidos = (
                consumo_real * gramos_por_pieza
                if gramos_por_pieza is not None
                else None
            )

            ddd = None
            if gramos_consumidos is not None and valor_atc:
                ddd = gramos_consumidos / valor_atc

            datos.append({
                'clave': med.clave,
                'descripcion': med.descripcion,
                'via_administracion': med.via_administracion,
                'categoria_aware': med.categoria_aware,
                'codigo_atc': med.codigo_atc,
                'consumo_real': consumo_real,
                'gramos_por_pieza': gramos_por_pieza,
                'gramos_consumidos': round(gramos_consumidos, 4) if gramos_consumidos is not None else None,
                'valor_atc': valor_atc,
                'ddd': round(ddd, 4) if ddd is not None else None,
            })

        return JsonResponse({
            'success': True,
            'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
            'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
            'data': datos
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['GET'])
@permission_required('farmacia.export_reportes', raise_exception=True)
def exportar_inventario_antibioticos_excel(request):
    """Exportar inventario de antibióticos a Excel con consumo mensual y DDD/ATC"""
    try:
        import os
        from io import BytesIO
        from datetime import datetime
        import xlsxwriter
        from django.db.models import Sum
        from django.conf import settings
        from django.http import HttpResponse
        from django.utils import timezone

        hoy = timezone.now().date()

        mes_param = request.GET.get('mes')
        if mes_param:
            try:
                fecha_inicio = datetime.strptime(mes_param, '%Y-%m').date().replace(day=1)
            except ValueError:
                fecha_inicio = hoy.replace(day=1)
        else:
            fecha_inicio = hoy.replace(day=1)

        if fecha_inicio.month == 12:
            siguiente_mes = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1, day=1)
        else:
            siguiente_mes = fecha_inicio.replace(month=fecha_inicio.month + 1, day=1)

        antibioticos_qs = (
            Medicamento.objects
            .filter(es_antibiotico=True, activo=True)
            .order_by('descripcion')
        )

        consumos_map = _consumo_antibioticos_por_medicamento(
            fecha_inicio, siguiente_mes
        )

        existencias_qs = (
            Lote.objects
            .filter(medicamento__es_antibiotico=True, medicamento__activo=True)
            .values('medicamento_id')
            .annotate(existencia_total=Sum('existencia'))
        )
        existencias_map = {
            item['medicamento_id']: item['existencia_total'] or 0
            for item in existencias_qs
        }

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Antibioticos')

        header_format = workbook.add_format({
            'bg_color': '#8B0000', 'font_color': 'white', 'bold': True,
            'align': 'center', 'valign': 'vcenter', 'border': 1,
            'font_size': 11, 'text_wrap': True
        })

        title_format = workbook.add_format({
            'bg_color': '#8B0000', 'font_color': 'white', 'bold': True,
            'align': 'center', 'valign': 'vcenter', 'font_size': 14
        })

        date_format = workbook.add_format({
            'italic': True, 'align': 'left', 'font_size': 10
        })

        text_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10
        })

        text_format_izq = workbook.add_format({
            'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_size': 10
        })

        number_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1,
            'font_size': 10, 'num_format': '#,##0'
        })

        decimal_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1,
            'font_size': 10, 'num_format': '#,##0.0000'
        })

        aware_access_format = workbook.add_format({
            'bg_color': '#00B050', 'font_color': 'white', 'bold': True,
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10
        })

        aware_watch_format = workbook.add_format({
            'bg_color': '#FFC000', 'font_color': 'black', 'bold': True,
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10
        })

        aware_reserve_format = workbook.add_format({
            'bg_color': '#FF0000', 'font_color': 'white', 'bold': True,
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10
        })

        summary_header_format = workbook.add_format({
            'bg_color': '#8F7A63', 'font_color': 'white', 'bold': True,
            'align': 'center', 'valign': 'vcenter', 'border': 1,
            'font_size': 10, 'text_wrap': True,
        })

        summary_label_format = workbook.add_format({
            'bold': True, 'align': 'left', 'valign': 'vcenter',
            'border': 1, 'font_size': 10,
        })

        summary_total_format = workbook.add_format({
            'bg_color': '#F2F3F5', 'bold': True, 'align': 'center',
            'valign': 'vcenter', 'border': 1, 'font_size': 10,
            'num_format': '#,##0.0000',
        })

        percentage_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1,
            'font_size': 10, 'num_format': '0.00%',
        })

        worksheet.set_column('A:A', 16)   # Clave
        worksheet.set_column('B:B', 55)   # Descripción
        worksheet.set_column('C:C', 18)   # Vía
        worksheet.set_column('D:D', 14)   # Código ATC
        worksheet.set_column('E:E', 16)   # Categoría AWaRe
        worksheet.set_column('F:F', 14)   # Gramos/pieza
        worksheet.set_column('G:G', 16)   # Piezas consumidas
        worksheet.set_column('H:H', 14)   # DDD/ATC
        worksheet.set_column('I:I', 16)   # Existencia actual

        logo_path = os.path.join(
            settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
        )
        if os.path.exists(logo_path):
            try:
                worksheet.insert_image('A1', logo_path, {'x_scale': 0.8, 'y_scale': 0.8})
            except Exception:
                pass

        worksheet.merge_range('A3:I3', 'REPORTE DE INVENTARIO DE ANTIBIÓTICOS', title_format)
        worksheet.merge_range(
            'A4:I4',
            f"Periodo: {fecha_inicio.strftime('%d/%m/%Y')} - "
            f"{(siguiente_mes - timezone.timedelta(days=1)).strftime('%d/%m/%Y')}  |  "
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            date_format
        )

        headers = [
            'Clave', 'Descripción', 'Vía', 'Código ATC', 'Categoría AWaRe',
            'Gramos/pieza', 'Piezas consumidas', 'DDD/ATC', 'Existencia actual',
        ]
        for col, header in enumerate(headers):
            worksheet.write(5, col, header, header_format)
        worksheet.set_row(5, 28)

        row = 6
        totales_ddd = {
            'Access': Decimal('0'),
            'Watch': Decimal('0'),
            'Reserve': Decimal('0'),
        }
        for med in antibioticos_qs:
            gramos_por_pieza = float(med.gramos_por_pieza or 0)
            valor_atc = float(med.valor_atc or 0)
            consumo_total = consumos_map.get(med.id, 0)
            existencia_actual = existencias_map.get(med.id, 0)

            ddd_consumidas_decimal = _calcular_ddd_antibiotico(
                med, consumo_total
            )
            ddd_consumidas = float(ddd_consumidas_decimal)

            aware = (med.categoria_aware or '').strip() or 'N/A'
            if aware in totales_ddd:
                totales_ddd[aware] += ddd_consumidas_decimal
            if aware == 'Access':
                aware_format = aware_access_format
            elif aware == 'Watch':
                aware_format = aware_watch_format
            elif aware == 'Reserve':
                aware_format = aware_reserve_format
            else:
                aware_format = text_format

            worksheet.write(row, 0, med.clave, text_format)
            worksheet.write(row, 1, med.descripcion, text_format_izq)
            worksheet.write(row, 2, med.via_administracion or 'N/A', text_format)
            worksheet.write(row, 3, med.codigo_atc or 'N/A', text_format)
            worksheet.write(row, 4, aware, aware_format)
            worksheet.write_number(row, 5, gramos_por_pieza, decimal_format)
            worksheet.write_number(row, 6, consumo_total, number_format)
            worksheet.write_number(row, 7, round(ddd_consumidas, 2), decimal_format)
            worksheet.write_number(row, 8, existencia_actual, number_format)

            worksheet.set_row(row, 20)
            row += 1

        resumen_aware, total_ddd = _resumen_ddd_aware(totales_ddd)
        summary_row = row + 2
        worksheet.merge_range(
            summary_row, 0, summary_row, 2,
            'BALANCE DE CONSUMO POR CLASIFICACIÓN AWaRe', title_format,
        )
        summary_row += 1
        summary_headers = [
            'Clasificación de Antibióticos esencial',
            'Sumatoria por grupo',
            'Porcentaje por grupo',
        ]
        for col, header in enumerate(summary_headers):
            worksheet.write(summary_row, col, header, summary_header_format)

        first_group_row = summary_row + 1
        for offset, fila in enumerate(resumen_aware, start=1):
            target_row = summary_row + offset
            worksheet.write(target_row, 0, fila['etiqueta'], summary_label_format)
            worksheet.write_number(
                target_row, 1, float(fila['sumatoria']), decimal_format
            )
            porcentaje_excel = float(fila['porcentaje']) / 100
            worksheet.write_number(
                target_row, 2, porcentaje_excel, percentage_format
            )

        total_row = summary_row + 4
        worksheet.write(total_row, 0, '∑ Total DDD antibióticos', summary_total_format)
        worksheet.write_number(total_row, 1, float(total_ddd), summary_total_format)
        worksheet.write_number(
            total_row, 2, 1 if total_ddd else 0, percentage_format
        )
        worksheet.set_column('A:A', 38)

        chart = workbook.add_chart({'type': 'pie'})
        chart.add_series({
            'name': 'Consumo DDD/ATC por grupo AWaRe',
            'categories': ['Antibioticos', first_group_row, 0, first_group_row + 2, 0],
            'values': ['Antibioticos', first_group_row, 1, first_group_row + 2, 1],
            'points': [
                {'fill': {'color': '#315B20'}},
                {'fill': {'color': '#FFB700'}},
                {'fill': {'color': '#9B0000'}},
            ],
            'data_labels': {
                'percentage': True,
                'category': True,
                'leader_lines': True,
            },
        })
        chart.set_title({'name': 'Reporte mensual de Consumo de Antibióticos'})
        chart.set_legend({'position': 'right'})
        chart.set_style(10)
        worksheet.insert_chart(summary_row, 4, chart, {
            'x_scale': 1.35, 'y_scale': 1.2,
        })

        worksheet.merge_range(
            total_row + 2, 0, total_row + 2, 8,
            'Documento generado automáticamente por INVENTFARM',
            date_format
        )

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="Antibioticos_{fecha_inicio.strftime("%Y%m")}.xlsx"'
        )
        return response

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)


def truncar_texto(valor, limite=80):
    texto = str(valor or "").strip()
    if len(texto) <= limite:
        return texto
    return texto[:limite - 3] + "..."


def _exportar_inventario_antibioticos_pdf(
    request, categoria_aware=None, incluir_resumen=True
):
    """Exportar inventario de antibióticos a PDF con consumo mensual y DDD/ATC"""
    try:
        import os
        from io import BytesIO
        from datetime import datetime

        from django.conf import settings
        from django.http import HttpResponse
        from django.db.models import Sum
        from django.utils import timezone

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
            PageBreak,
        )
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.charts.legends import Legend

        hoy = timezone.now().date()

        mes_param = request.GET.get('mes')
        if mes_param:
            try:
                fecha_inicio = datetime.strptime(mes_param, '%Y-%m').date().replace(day=1)
            except ValueError:
                fecha_inicio = hoy.replace(day=1)
        else:
            fecha_inicio = hoy.replace(day=1)

        if fecha_inicio.month == 12:
            siguiente_mes = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1, day=1)
        else:
            siguiente_mes = fecha_inicio.replace(month=fecha_inicio.month + 1, day=1)

        antibioticos_qs = (
            Medicamento.objects
            .filter(es_antibiotico=True, activo=True)
            .order_by('descripcion')
        )
        if categoria_aware:
            antibioticos_qs = antibioticos_qs.filter(
                categoria_aware=categoria_aware
            )

        consumos_map = _consumo_antibioticos_por_medicamento(
            fecha_inicio, siguiente_mes
        )

        existencias_qs = (
            Lote.objects
            .filter(medicamento__es_antibiotico=True, medicamento__activo=True)
            .values('medicamento_id')
            .annotate(existencia_total=Sum('existencia'))
        )
        existencias_map = {
            item['medicamento_id']: item['existencia_total'] or 0
            for item in existencias_qs
        }

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=8 * mm,
            rightMargin=8 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )

        styles = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            name="TituloReporte", parent=styles["Title"],
            fontName="Helvetica-Bold", fontSize=14, leading=16,
            alignment=1, spaceAfter=4,
        )

        estilo_meta = ParagraphStyle(
            name="MetaReporte", parent=styles["Normal"],
            fontName="Helvetica", fontSize=9, leading=11,
            alignment=1, spaceAfter=2,
        )

        estilo_header = ParagraphStyle(
            name="HeaderTabla", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=7.0, leading=7.5,
            alignment=1, textColor=colors.whitesmoke,
        )

        estilo_celda = ParagraphStyle(
            name="CeldaTabla", parent=styles["Normal"],
            fontName="Helvetica", fontSize=6.5, leading=7.0,
            alignment=0, wordWrap='LTR',
        )

        estilo_celda_centrada = ParagraphStyle(
            name="CeldaTablaCentrada", parent=estilo_celda, alignment=1,
        )

        elementos = []

        logo_path = os.path.join(
            settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg'
        )
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=170 * mm, height=24 * mm)
            logo.hAlign = 'CENTER'
            elementos.append(logo)
            elementos.append(Spacer(1, 3 * mm))

        titulo_reporte = "REPORTE DE INVENTARIO DE ANTIBIÓTICOS"
        if categoria_aware:
            titulo_reporte += f" - {categoria_aware.upper()}"
        elementos.append(Paragraph(titulo_reporte, estilo_titulo))

        fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
        nombre_usuario = (request.user.get_full_name() or request.user.username).strip()
        fecha_fin_mostrar = (siguiente_mes - timezone.timedelta(days=1)).strftime('%d/%m/%Y')

        elementos.append(Paragraph(
            f"Periodo: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin_mostrar}",
            estilo_meta
        ))
        elementos.append(Paragraph(
            f"Fecha de Generación: {fecha_generacion}  |  Generado por: {nombre_usuario}",
            estilo_meta
        ))
        elementos.append(Spacer(1, 4 * mm))

        data_tabla = [[
            Paragraph("Clave", estilo_header),
            Paragraph("Descripción", estilo_header),
            Paragraph("Vía", estilo_header),
            Paragraph("Cód. ATC", estilo_header),
            Paragraph("AWaRe", estilo_header),
            Paragraph("Gr./pieza", estilo_header),
            Paragraph("Piezas cons.", estilo_header),
            Paragraph("DDD/ATC", estilo_header),
            Paragraph("Exist. actual", estilo_header),
        ]]

        totales_ddd = {
            'Access': Decimal('0'),
            'Watch': Decimal('0'),
            'Reserve': Decimal('0'),
        }
        for med in antibioticos_qs:
            gramos_por_pieza = float(med.gramos_por_pieza or 0)
            consumo_total = consumos_map.get(med.id, 0)
            existencia_actual = existencias_map.get(med.id, 0)

            ddd_consumidas_decimal = _calcular_ddd_antibiotico(
                med, consumo_total
            )
            ddd_consumidas = float(ddd_consumidas_decimal)
            aware = (med.categoria_aware or '').strip()
            if aware in totales_ddd:
                totales_ddd[aware] += ddd_consumidas_decimal

            data_tabla.append([
                Paragraph(escape_xml(str(med.clave or "N/A")), estilo_celda_centrada),
                Paragraph(escape_xml(truncar_texto(med.descripcion or "N/A", 220)), estilo_celda),
                Paragraph(escape_xml(str(med.via_administracion or "N/A")), estilo_celda_centrada),
                Paragraph(escape_xml(str(med.codigo_atc or "N/A")), estilo_celda_centrada),
                Paragraph(escape_xml(str(med.categoria_aware or "N/A")), estilo_celda_centrada),
                Paragraph(f"{gramos_por_pieza:,.4f}", estilo_celda_centrada),
                Paragraph(str(consumo_total), estilo_celda_centrada),
                Paragraph(f"{ddd_consumidas:,.2f}", estilo_celda_centrada),
                Paragraph(str(existencia_actual), estilo_celda_centrada),
            ])

        col_widths = [
            18 * mm,   # Clave
            80 * mm,   # Descripción
            20 * mm,   # Vía
            18 * mm,   # Cód. ATC
            16 * mm,   # AWaRe
            16 * mm,   # Gr./pieza
              20 * mm,   # Piezas cons.
            16 * mm,   # DDD/ATC
            18 * mm,   # Exist. actual
        ]

        tabla = Table(
            data_tabla,
            colWidths=col_widths,
            repeatRows=1,
            splitByRow=1,
            hAlign='LEFT',
        )

        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8B0000")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7.2),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),

            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F4F4")]),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.grey),

            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),

            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (8, -1), 'CENTER'),
        ]))

        elementos.append(tabla)

        if incluir_resumen:
            resumen_aware, total_ddd = _resumen_ddd_aware(totales_ddd)
            elementos.append(PageBreak())
            elementos.append(Paragraph(
                "BALANCE DE CONSUMO POR CLASIFICACIÓN AWaRe",
                estilo_titulo,
            ))
            elementos.append(Spacer(1, 3 * mm))

            data_resumen = [[
                Paragraph("Clasificación de Antibióticos esencial", estilo_header),
                Paragraph("Sumatoria por grupo", estilo_header),
                Paragraph("Porcentaje por grupo", estilo_header),
            ]]
            for fila in resumen_aware:
                data_resumen.append([
                    Paragraph(
                        f"Sumatoria DDD {fila['categoria']}", estilo_celda
                    ),
                    Paragraph(
                        f"{fila['sumatoria']:,.4f}", estilo_celda_centrada
                    ),
                    Paragraph(
                        f"{fila['porcentaje']:,.2f}%", estilo_celda_centrada
                    ),
                ])
            data_resumen.append([
                Paragraph("Total DDD antibióticos", estilo_celda),
                Paragraph(f"{total_ddd:,.4f}", estilo_celda_centrada),
                Paragraph(
                    "100.00%" if total_ddd else "0.00%",
                    estilo_celda_centrada,
                ),
            ])

            tabla_resumen = Table(
                data_resumen,
                colWidths=[90 * mm, 45 * mm, 45 * mm],
                repeatRows=1,
                hAlign='CENTER',
            )
            tabla_resumen.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8F7A63')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F2F3F5')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#555555')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ]))
            elementos.append(tabla_resumen)
            elementos.append(Spacer(1, 5 * mm))

            if total_ddd:
                drawing = Drawing(650, 250)
                pie = Pie()
                pie.x = 95
                pie.y = 28
                pie.width = 210
                pie.height = 210
                pie.data = [
                    float(fila['sumatoria']) for fila in resumen_aware
                ]
                pie.labels = [
                    f"{fila['porcentaje']:.2f}%" for fila in resumen_aware
                ]
                pie.slices.strokeWidth = 0.5
                pie.slices.strokeColor = colors.white
                colores_aware = [
                    colors.HexColor('#315B20'),
                    colors.HexColor('#FFB700'),
                    colors.HexColor('#9B0000'),
                ]
                for indice, color in enumerate(colores_aware):
                    pie.slices[indice].fillColor = color
                drawing.add(pie)

                legend = Legend()
                legend.x = 390
                legend.y = 168
                legend.dx = 12
                legend.dy = 12
                legend.deltay = 22
                legend.fontName = 'Helvetica'
                legend.fontSize = 9
                legend.colorNamePairs = [
                    (
                        colores_aware[indice],
                        f"DDD {fila['categoria']}: "
                        f"{fila['sumatoria']:,.4f} ({fila['porcentaje']:.2f}%)",
                    )
                    for indice, fila in enumerate(resumen_aware)
                ]
                drawing.add(legend)
                elementos.append(Paragraph(
                    "Reporte mensual de Consumo de Antibióticos",
                    estilo_titulo,
                ))
                elementos.append(drawing)
            else:
                elementos.append(Paragraph(
                    "No hay consumo DDD/ATC calculable para este periodo.",
                    estilo_meta,
                ))

        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(
            f"Documento generado por INVENTFARM - {nombre_usuario}",
            estilo_meta
        ))

        doc.build(elementos)

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        sufijo_categoria = f'_{categoria_aware}' if categoria_aware else ''
        response['Content-Disposition'] = (
            'attachment; filename="Antibioticos'
            f'{sufijo_categoria}_{fecha_inicio.strftime("%Y%m")}.pdf"'
        )
        return response

    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)


@login_required
@require_http_methods(['GET'])
@permission_required('farmacia.export_reportes', raise_exception=True)
def exportar_inventario_antibioticos_pdf(request):
    return _exportar_inventario_antibioticos_pdf(request)


@login_required
@require_http_methods(['GET'])
@permission_required('farmacia.export_reportes', raise_exception=True)
def exportar_inventario_antibioticos_access_pdf(request):
    return _exportar_inventario_antibioticos_pdf(
        request, categoria_aware='Access', incluir_resumen=False
    )


@login_required
@require_http_methods(['GET'])
@permission_required('farmacia.export_reportes', raise_exception=True)
def exportar_inventario_antibioticos_watch_pdf(request):
    return _exportar_inventario_antibioticos_pdf(
        request, categoria_aware='Watch', incluir_resumen=False
    )


@login_required
@require_http_methods(['GET'])
@permission_required('farmacia.export_reportes', raise_exception=True)
def exportar_inventario_antibioticos_reserve_pdf(request):
    return _exportar_inventario_antibioticos_pdf(
        request, categoria_aware='Reserve', incluir_resumen=False
    )
