"""
farmacia/views/inventario_views.py
Vistas de gestión de inventario: farmacia_g, alertas, lotes, CPM,
inventario general, registro de medicamentos.
"""
import json
import logging
import uuid
from datetime import date, timedelta
from math import ceil

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum, Q, F, Value, IntegerField, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from ..decorators import group_required
from ..forms import MedicamentoForm
from ..models import (
    Lote, Medicamento, Presentacion, CPMMedicamento, CatalogoAntibioticosWHO
)

logger = logging.getLogger(__name__)


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
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia')
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
@group_required('Administrador', 'Farmacéutico', 'Jefe de Farmacia', 'Enfermero', 'Jefe de Enfermería', 'Médico')
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
    ).filter(existencia_total__gt=0).order_by('medicamento__descripcion')

    if busqueda:
        inventario = inventario.filter(
            Q(medicamento__descripcion__icontains=busqueda) |
            Q(medicamento__clave__icontains=busqueda)
        )

    sobreabasto = stock_adecuado = stock_bajo = desabasto = 0
    inventario_con_porcentaje = []
    for item in inventario:
        existencia = item['existencia_total']
        cpm = item['cpm_medicamento']
        porcentaje = round((existencia / cpm) * 100, 1) if cpm > 0 else 0
        if cpm > 0:
            if porcentaje > 100:
                estado = 'sobreabasto'; sobreabasto += 1
            elif porcentaje >= 50:
                estado = 'adecuado'; stock_adecuado += 1
            elif porcentaje > 0:
                estado = 'bajo'; stock_bajo += 1
            else:
                estado = 'desabasto'; desabasto += 1
        else:
            estado = 'sin-cpm'
        item['porcentaje'] = porcentaje
        item['estado'] = estado
        inventario_con_porcentaje.append(item)

    context = {
        'inventario': inventario_con_porcentaje,
        'busqueda_actual': busqueda,
        'total_medicamentos': len(inventario_con_porcentaje),
        'sobreabasto': sobreabasto,
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
def actualizar_cpm(request):
    """Alias de editar_cpm_medicamento para compatibilidad con URLs existentes"""
    return editar_cpm_medicamento(request)


@login_required
@require_http_methods(['POST'])
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
        'valor_atc': float(item.valor_atc) if item.valor_atc is not None else None,
        'fuente_ddd': item.fuente_ddd,
    })
