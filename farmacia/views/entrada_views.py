"""
farmacia/views/entrada_views.py
Vistas de entrada de medicamentos: formulario de entrada, guardar entradas,
búsqueda de medicamentos/lotes para autocomplete, y carga masiva Excel.
"""
import json
import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from farmacia.forms import CargaMasivaForm
from farmacia.models import (
    Medicamento, Presentacion, Almacen, Institucion, FuenteFinanciamiento,
    Entrada, DetalleEntrada, Lote
)

logger = logging.getLogger(__name__)


@never_cache
@login_required(login_url='login')
@permission_required('farmacia.add_entrada', raise_exception=True)
def entrada_medicamentos(request):
    context = {
        'presentaciones': Presentacion.objects.all(),
        'almacenes': Almacen.objects.all(),
        'instituciones': Institucion.objects.all(),
        'fuentes_financiamiento': FuenteFinanciamiento.objects.all(),
        'hoy': date.today().isoformat(),
        'user': request.user
    }

    if 'folio_entrada' in request.GET:
        context['folio_entrada'] = request.GET.get('folio_entrada')
    else:
        date_str = date.today().strftime('%Y%m%d')
        last_entry = Entrada.objects.filter(folio__startswith=f'ENT-{date_str}').order_by('-folio').first()
        new_num = int(last_entry.folio.split('-')[-1]) + 1 if last_entry else 1
        context['folio_entrada'] = f"ENT-{date_str}-{new_num:04d}"

    if request.method == 'POST':
        try:
            with transaction.atomic():
                folio = request.POST.get('folio_entrada') or context['folio_entrada']
                if not folio:
                    raise ValueError("El folio es requerido")
                entrada = Entrada(
                    folio=folio,
                    medicamento_id=request.POST.get('medicamento_id'),
                    lote=request.POST.get('lote'),
                    caducidad=request.POST.get('caducidad'),
                    cantidad=request.POST.get('cantidad'),
                )
                entrada.save()
                messages.success(request, f'Entrada {folio} guardada correctamente')
                return redirect('farmacia_g')
        except Exception as e:
            messages.error(request, f'Error al guardar: {str(e)}')
            context['folio_entrada'] = request.POST.get('folio_entrada', context['folio_entrada'])

    return render(request, 'entrada_medicamentos.html', context)


@login_required
def buscar_medicamentos_autocomplete(request):
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse([], safe=False)
    medicamentos = Medicamento.objects.filter(
        Q(descripcion__icontains=query) | Q(clave__icontains=query),
        activo=True
    ).select_related('presentacion')[:10]
    resultados = [{
        'id': m.id, 'clave': m.clave, 'descripcion': m.descripcion,
        'presentacion': m.presentacion.nombre if m.presentacion else 'UNIDAD'
    } for m in medicamentos]
    return JsonResponse(resultados, safe=False)


@login_required
def buscar_medicamentos(request):
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse([], safe=False)
    medicamentos = Medicamento.objects.filter(
        Q(clave__icontains=query) | Q(descripcion__icontains=query),
        activo=True
    ).select_related('presentacion')[:10]
    resultados = [{
        'id': m.id, 'clave': m.clave, 'descripcion': m.descripcion,
        'presentacion': m.presentacion.nombre if m.presentacion else 'UNIDAD'
    } for m in medicamentos]
    return JsonResponse(resultados, safe=False)


@login_required
def guardar_entradas(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body)
        required_fields = ['folio', 'fecha', 'tipo_entrada', 'recibido_por',
                           'detalles', 'fuente_financiamiento', 'proceso']
        for field in required_fields:
            if field not in data or data[field] in (None, '', []):
                return JsonResponse({'error': f'Campo {field} es requerido'}, status=400)

        if not isinstance(data['detalles'], list) or len(data['detalles']) == 0:
            return JsonResponse({'error': 'Debe incluir al menos un medicamento'}, status=400)

        tipo = data['tipo_entrada']
        almacen_id = data.get('almacen')
        institucion_id = data.get('institucion')

        if tipo == 'ALMACEN':
            if not almacen_id:
                return JsonResponse({'error': 'Seleccione un almacén'}, status=400)
            institucion_id = None
        elif tipo == 'TRANSFERENCIA':
            if not institucion_id:
                return JsonResponse({'error': 'Seleccione una institución'}, status=400)
            almacen_id = None
        else:
            return JsonResponse({'error': 'Tipo de entrada inválido'}, status=400)

        with transaction.atomic():
            entrada = Entrada.objects.create(
                folio=data['folio'], fecha=data['fecha'], tipo_entrada=tipo,
                almacen_id=almacen_id, institucion_id=institucion_id,
                fuente_financiamiento_id=data['fuente_financiamiento'],
                contrato=data.get('contrato', ''), proceso=data['proceso'],
                recibido_por_id=data['recibido_por'],
                observaciones=data.get('observaciones', '')
            )
            detalle_fields = {f.name for f in DetalleEntrada._meta.fields}
            for det in data['detalles']:
                detalle_required = ['medicamento_id', 'lote', 'caducidad', 'cantidad', 'precio_unitario', 'presentacion_id']
                for f in detalle_required:
                    if f not in det or det[f] in (None, ''):
                        return JsonResponse({'error': f'Campo {f} es requerido en los detalles'}, status=400)
                kwargs_det = dict(
                    entrada=entrada, medicamento_id=det['medicamento_id'],
                    lote=det['lote'], caducidad=det['caducidad'],
                    cantidad=det['cantidad'], presentacion_id=det['presentacion_id'],
                )
                if 'precio_unitario' in detalle_fields:
                    kwargs_det['precio_unitario'] = det['precio_unitario']
                elif 'preciounitario' in detalle_fields:
                    kwargs_det['preciounitario'] = det['precio_unitario']
                else:
                    return JsonResponse({'error': 'El modelo DetalleEntrada no tiene campo de precio unitario'}, status=500)
                DetalleEntrada.objects.create(**kwargs_det)

            return JsonResponse({'success': True, 'folio': entrada.folio, 'redirect_url': reverse('farmacia_g')})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def buscar_lote_json(request, query):
    """Busca un lote por ID (pk) O por Código de Lote."""
    if request.method == "GET":
        try:
            lote = Lote.objects.get(Q(id=query) | Q(lote_codigo=query.upper()))
            return JsonResponse({
                'id': lote.id,
                'medicamento_nombre': lote.medicamento.descripcion,
                'clave': lote.medicamento.clave,
                'lote_numero': lote.lote_codigo,
                'caducidad': lote.fecha_caducidad.strftime('%d/%m/%Y'),
                'cantidad_actual': lote.existencia,
            })
        except Lote.DoesNotExist:
            return JsonResponse({'error': f'Lote "{query}" no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
@permission_required('farmacia.view_carga_masiva', raise_exception=True)
def carga_masiva(request):
    """Vista para mostrar el formulario de carga masiva"""
    form = CargaMasivaForm()
    return render(request, 'carga_masiva.html', {'form': form, 'user': request.user})


@login_required
def procesar_carga_masiva(request):
    """Procesa el archivo Excel de carga masiva"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    form = CargaMasivaForm(request.POST, request.FILES)
    if not form.is_valid():
        errores = [str(e) for field, errors in form.errors.items() for e in errors]
        return JsonResponse({'error': ', '.join(errores)}, status=400)

    from farmacia.utils import ProcesadorCargaMasiva
    archivo = form.cleaned_data['archivo']
    procesador = ProcesadorCargaMasiva(archivo)
    resultado = procesador.procesar()

    if 'error' in resultado:
        return JsonResponse(resultado, status=400)

    response_data = {
        'success': True,
        'mensaje': 'Carga masiva completada',
        'resultados': {
            'total': resultado['resultados']['total'],
            'exitosos': resultado['resultados']['exitosos'],
            'actualizados': resultado['resultados']['actualizados'],
            'errores': resultado['resultados']['errores'],
            'advertencias': resultado['resultados'].get('advertencias', [])
        }
    }
    status_code = 200 if len(resultado['resultados']['errores']) == 0 else 207
    return JsonResponse(response_data, status=status_code)
