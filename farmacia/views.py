import os
import json
import openpyxl
import traceback
import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods
from .models import Lote, Medicamento, Presentacion, Proveedor, Entrada, Almacen, DetalleEntrada, Institucion, FuenteFinanciamiento, CPMMedicamento, Receta, RecetaMedicamento, Paciente
from datetime import timedelta, date, datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q, F, Value, IntegerField
from django.db.models.functions import Coalesce
from .forms import LoteForm, MedicamentoForm, SalidaForm
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, LoginSerializer
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepInFrame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.templatetags.static import static
from .pdf_utils import generar_pdf_salida
from django.conf import settings
from .forms import CargaMasivaForm
import uuid
import logging
logger = logging.getLogger(__name__)



# Create your views here.

def inicio(request):
    return render(request, 'inicio.html')

def vista_farmacia(request):
    return render(request, 'farmacia.html')

def vista_farmacia_g(request):
    """Vista para el inventario por lotes"""
    return render(request, 'farmacia_g.html', {
        'user': request.user
    })

def login_view(request):
    if request.user.is_authenticated:
        return redirect('principal')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Validación básica
        if not username or not password:
            messages.error(request, 'Usuario y contraseña son requeridos')
            return render(request, 'inicio.html', {'username': username or ''})
        
        user = authenticate(request, username=username, password=password)
        print(f"Authenticate result: {user}")  # <<<<<
        
        if user is not None:
            if user.is_active:
                login(request, user)
                next_url = request.POST.get('next', 'principal')
                return redirect(next_url)
            else:
                messages.error(request, 'Cuenta desactivada')
        else:
            messages.error(request, 'Credenciales inválidas')
        
        return render(request, 'inicio.html', {'username': username})
    
    return render(request, 'inicio.html')

@login_required
def bienvenida(request):
    def tiene_acceso(user, grupos_requeridos):
        # Acceso para superusuarios O usuarios con rol ADMIN
        if user.is_superuser or user.rol == 'ADMIN':
            return True
        # Verificación por grupos para otros usuarios
        return user.groups.filter(name__in=grupos_requeridos).exists()
    
    modulos = [
        {
            'nombre': 'Farmacia',
            'imagen': 'farmacia/img/farmacia.png',
            'descripcion': 'Gestión de medicamentos y lotes',
            'url': 'farmacia_g',
            'acceso': tiene_acceso(request.user, ['Capturista_Farmacia', 'Supervisor_Farmacia'])
        },
        {
            'nombre': 'Enfermería',
            'imagen': 'farmacia/img/enfermeria.png',
            'descripcion': 'Gestión de pacientes y tratamientos',
            'url': None,
            'acceso': tiene_acceso(request.user, ['Enfermeria'])
        },
        # ... otros módulos con la misma estructura
    ]
    
    return render(request, 'principal.html', {
        'modulos': modulos,
        'last_login': request.user.last_login
    })

def logout_view(request):
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente')
    return redirect('login')

@login_required
def alertas(request):
    usuario = request.user
    es_admin = usuario.is_superuser or usuario.groups.filter(name='Administrador').exists()
    es_capturista = usuario.groups.filter(name='Capturista').exists()

    # Filtros
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
            lotes = lotes.filter(fecha_caducidad__gt=hoy + timedelta(days=180), fecha_caducidad__lte=hoy + timedelta(days=365))
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
    lote = get_object_or_404(Lote, id=lote_id)
    
    if request.method == 'POST':
        try:
            # Campos que todos pueden editar
            cpm = request.POST.get('cpm')
            presentacion_id = request.POST.get('presentacion')
            
            if cpm:
                lote.cpm = float(cpm)
            
            if presentacion_id:
                presentacion = get_object_or_404(Presentacion, id=presentacion_id)
                lote.presentacion = presentacion
            
            # Campos solo para admin
            if request.user.is_superuser:
                lote_codigo = request.POST.get('lote_codigo')
                existencia = request.POST.get('existencia')
                fecha_caducidad = request.POST.get('fecha_caducidad')
                
                if lote_codigo:
                    lote.lote_codigo = lote_codigo
                
                if existencia:
                    lote.existencia = int(existencia)
                
                if fecha_caducidad:
                    lote.fecha_caducidad = fecha_caducidad
            
            lote.save()
            
            return JsonResponse({
                'success': True,
                'mensaje': 'Lote actualizado correctamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    # GET: devolver datos del lote en JSON
    return JsonResponse({
        'id': lote.id,
        'medicamento': f"{lote.medicamento.clave} - {lote.medicamento.descripcion}",
        'cpm': str(lote.cpm),
        'presentacion_id': lote.presentacion.id if lote.presentacion else '',
        'lote_codigo': lote.lote_codigo,
        'existencia': lote.existencia,
        'fecha_caducidad': lote.fecha_caducidad.strftime('%Y-%m-%d')
    })


def tiene_acceso_farmacia(user):
    return user.groups.filter(name__in=[
        'Administrador',
        'Capturista_Farmacia',
        'Supervisor_Farmacia'
    ]).exists()


@login_required(login_url='login')
@user_passes_test(tiene_acceso_farmacia)
def farmacia_g(request):
    if request.method == 'POST':
        medicamento_id = request.POST.get('medicamento')
        lote_codigo = request.POST.get('lote_codigo')
        existencia = request.POST.get('existencia')
        presentacion_id = request.POST.get('presentacion')
        nueva_descripcion = request.POST.get('descripcion')

        if medicamento_id and nueva_descripcion:
            medicamento = Medicamento.objects.get(id=medicamento_id)
            medicamento.descripcion = nueva_descripcion
            medicamento.save()
            return JsonResponse({'status': 'success'})

        if medicamento_id and lote_codigo and existencia and presentacion_id:
            medicamento = Medicamento.objects.get(id=medicamento_id)
            presentacion = Presentacion.objects.get(id=presentacion_id)
            
            import uuid
            lote_id = str(uuid.uuid4())[:15]
            
            Lote.objects.create(
                id=lote_id,
                medicamento=medicamento,
                lote_codigo=lote_codigo,
                existencia=int(existencia),
                presentacion=presentacion,
                fecha_caducidad=date.today() + timedelta(days=365),
                cpm=0
            )
            
            return redirect('farmacia_g')

    # ✅ AGREGAMOS EL CÁLCULO DE DÍAS
    lotes = Lote.objects.select_related('medicamento', 'presentacion').all()
    
    # Calcular días para caducidad para cada lote
    hoy = date.today()
    lotes_con_dias = []
    for lote in lotes:
        lote.dias_para_caducidad = (lote.fecha_caducidad - hoy).days
        lotes_con_dias.append(lote)
    
    medicamentos = Medicamento.objects.filter(activo=True)
    presentaciones = Presentacion.objects.all()

    context = {
        'lotes': lotes_con_dias,  # ✅ Enviamos los lotes con días calculados
        'medicamentos': medicamentos,
        'presentaciones': presentaciones,
    }

    return render(request, 'farmacia_g.html', context)


@csrf_exempt
@login_required
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


def inventario_general(request):
    # Obtener parámetro de búsqueda si existe
    busqueda = request.GET.get('busqueda', '').strip()
    
    # Consulta base - Incluir CPM del medicamento
    inventario = Lote.objects.values(
        'medicamento__id',
        'medicamento__clave',
        'medicamento__descripcion',
    ).annotate(
        existencia_total=Sum('existencia'),
        # Usar Coalesce para mostrar 0 si no hay CPM definido
        cpm_medicamento=Coalesce(
            F('medicamento__cpm_medicamento__valor'),
            Value(0),
            output_field=IntegerField()
        )
    ).order_by('medicamento__descripcion')
    
    # Aplicar filtro si hay búsqueda
    if busqueda:
        inventario = inventario.filter(
            Q(medicamento__descripcion__icontains=busqueda) |
            Q(medicamento__clave__icontains=busqueda)
        )
    
    context = {
        'inventario': inventario,
        'busqueda_actual': busqueda
    }
    return render(request, 'inv_gene_f.html', context)

@require_http_methods(["POST"]) 
@csrf_exempt
@login_required
def editar_cpm_medicamento(request):
    if request.method == 'POST':
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
            
            # Obtener o crear el registro CPM
            medicamento = Medicamento.objects.get(id=medicamento_id)
            cpm_obj, created = CPMMedicamento.objects.get_or_create(
                medicamento=medicamento,
                defaults={'valor': nuevo_cpm, 'actualizado_por': request.user}
            )
            
            if not created:
                cpm_obj.valor = nuevo_cpm
                cpm_obj.actualizado_por = request.user
                cpm_obj.save()
            
            return JsonResponse({
                'success': True, 
                'message': 'CPM actualizado correctamente',
                'nuevo_cpm': nuevo_cpm
            })
            
        except Medicamento.DoesNotExist:
            return JsonResponse({'error': 'Medicamento no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
@require_http_methods(["DELETE", "POST"])
def eliminar_lote(request, lote_id):
    """
    Elimina un lote del inventario
    Solo permite eliminar si existencia = 0
    """
    try:
        lote = get_object_or_404(Lote, id=lote_id)
        
        # Información del lote
        medicamento_clave = lote.medicamento.clave
        medicamento_descripcion = lote.medicamento.descripcion
        lote_codigo = lote.lote_codigo
        existencia = lote.existencia
        
        # VALIDACIÓN: Verificar que existencia sea 0
        if existencia > 0:
            return JsonResponse({
                'success': False,
                'tipo': 'error_existencia',
                'error': f'No se puede eliminar el lote {lote_codigo}',
                'detalle': f'El lote tiene {existencia} unidades en existencia.',
                'solucion': 'Para eliminar este lote, primero debes registrar salidas hasta que la existencia sea 0.',
                'existencia': existencia
            }, status=400)
        
        # Si llegamos aquí, existencia = 0, proceder a eliminar
        lote.delete()
        
        return JsonResponse({
            'success': True,
            'mensaje': f'Lote {lote_codigo} eliminado correctamente',
            'clave': medicamento_clave,
            'descripcion': medicamento_descripcion
        })
        
    except Lote.DoesNotExist:
        return JsonResponse({
            'success': False,
            'tipo': 'error_no_existe',
            'error': 'El lote no existe',
            'detalle': 'Es posible que ya haya sido eliminado por otro usuario.'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'tipo': 'error_sistema',
            'error': 'Error del sistema',
            'detalle': str(e)
        }, status=500)


def registro_medicamento(request):
    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            # Generar ID automático si no se provee
            medicamento = form.save(commit=False)
            if not medicamento.id:
                medicamento.id = f"MED-{Medicamento.objects.count() + 1:04d}"
            medicamento.save()
            
            messages.success(request, 'Medicamento registrado correctamente')
            return redirect('farmacia_g')
        else:
            messages.error(request, 'Error en el formulario. Verifica los datos.')
    else:
        form = MedicamentoForm()
    
    return render(request, 'registro_medicamento.html', {
        'form': form,
        'proveedores': Proveedor.objects.filter(activo=True)
    })


@login_required
def entrada_medicamentos(request):
    
    
    context = {
        'presentaciones': Presentacion.objects.all(),
        'almacenes': Almacen.objects.all(),
        'instituciones': Institucion.objects.all(),
        'fuentes_financiamiento': FuenteFinanciamiento.objects.all(),
        'hoy': date.today().isoformat(),
        'user': request.user
    }

    # Lógica para folio (GET o POST fallido)
    if 'folio_entrada' in request.GET:  # Para previsualización
        context['folio_entrada'] = request.GET.get('folio_entrada')
    else:
        # Generar folio automático
        date_str = date.today().strftime('%Y%m%d')
        last_entry = Entrada.objects.filter(folio__startswith=f'ENT-{date_str}').order_by('-folio').first()
        new_num = int(last_entry.folio.split('-')[-1]) + 1 if last_entry else 1
        context['folio_entrada'] = f"ENT-{date_str}-{new_num:04d}"

    # Manejo de POST (guardar entrada)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener folio (manual o automático)
                folio = request.POST.get('folio_entrada')
                if not folio:  # Si no se proporcionó folio manual
                    folio = context['folio_entrada']  # Usar el generado automáticamente

                # Validación básica
                if not folio:
                    raise ValueError("El folio es requerido")

                # Crear la entrada (ajusta según tu modelo)
                entrada = Entrada(
                    folio=folio,
                    medicamento_id=request.POST.get('medicamento_id'),
                    lote=request.POST.get('lote'),
                    caducidad=request.POST.get('caducidad'),
                    cantidad=request.POST.get('cantidad'),
                    # ... otros campos ...
                )
                entrada.save()

                messages.success(request, f'Entrada {folio} guardada correctamente')
                return redirect('nombre_de_tu_url_de_exito')  # Ajusta la URL

        except Exception as e:
            messages.error(request, f'Error al guardar: {str(e)}')
            # Mantenemos los valores en el contexto para repoblar el formulario
            context.update({
                'folio_entrada': request.POST.get('folio_entrada', context['folio_entrada']),
                # ... otros campos del formulario ...
            })

    return render(request, 'entrada_medicamentos.html', context)


# En views.py - agregar esta vista
@csrf_exempt
def buscar_medicamentos_autocomplete(request):
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse([], safe=False)
    
    medicamentos = Medicamento.objects.filter(
        Q(descripcion__icontains=query) | Q(clave__icontains=query),
        activo=True
    ).select_related('presentacion')[:10]
    
    resultados = []
    for med in medicamentos:
        resultados.append({
            'id': med.id,
            'clave': med.clave,
            'descripcion': med.descripcion,
            'presentacion': med.presentacion.nombre if med.presentacion else 'UNIDAD'
        })
    
    return JsonResponse(resultados, safe=False)


def buscar_medicamentos(request):
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse([], safe=False)
    
    medicamentos = Medicamento.objects.filter(
        Q(clave__icontains=query) | Q(descripcion__icontains=query),
        activo=True
    ).select_related('presentacion')[:10]
    
    resultados = []
    for med in medicamentos:
        resultados.append({
            'id': med.id,
            'clave': med.clave,
            'descripcion': med.descripcion,
            'presentacion': med.presentacion.nombre if med.presentacion else 'UNIDAD'
        })
    
    return JsonResponse(resultados, safe=False)

@csrf_exempt
@login_required
def guardar_entradas(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validación de campos requeridos
        required_fields = ['folio', 'fecha', 'tipo_entrada', 'recibido_por', 'detalles', 'fuente_financiamiento', 'proceso']
        for field in required_fields:
            if field not in data or not data[field]:
                return JsonResponse({'error': f'Campo {field} es requerido'}, status=400)
        
        if not isinstance(data['detalles'], list) or len(data['detalles']) == 0:
            return JsonResponse({'error': 'Debe incluir al menos un medicamento'}, status=400)

        with transaction.atomic():
            # Crear entrada principal
            entrada = Entrada.objects.create(
                folio=data['folio'],
                fecha=data['fecha'],
                tipo_entrada=data['tipo_entrada'],
                almacen_id=data.get('almacen'),
                institucion_id=data.get('institucion'),
                fuente_financiamiento_id=data['fuente_financiamiento'],
                contrato=data.get('contrato', ''),
                proceso=data['proceso'],
                recibido_por_id=data['recibido_por']
            )
            
            # Procesar cada detalle
            for detalle in data['detalles']:
                # Validar campos del detalle
                detalle_required = ['medicamento_id', 'lote', 'caducidad', 'cantidad', 'precio_unitario', 'presentacion_id']
                for field in detalle_required:
                    if field not in detalle:
                        raise ValueError(f'Campo {field} es requerido en los detalles')
                
                # Crear detalle
                DetalleEntrada.objects.create(
                    entrada=entrada,
                    medicamento_id=detalle['medicamento_id'],
                    lote=detalle['lote'],
                    caducidad=detalle['caducidad'],
                    cantidad=detalle['cantidad'],
                    precio_unitario=detalle['precio_unitario'],
                    presentacion_id=detalle['presentacion_id']
                )
                
                # Actualizar inventario
                Lote.actualizar_inventario(
                    medicamento_id=detalle['medicamento_id'],
                    lote_codigo=detalle['lote'],
                    cantidad=detalle['cantidad'],
                    fecha_caducidad=detalle['caducidad'],
                    presentacion_id=detalle['presentacion_id']
                )
            
            return JsonResponse({
                'success': True,
                'folio': entrada.folio,
                'redirect_url': reverse('farmacia_g')
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@login_required
def generar_reporte_pdf(request):    
    try:
        data = json.loads(request.body)
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              rightMargin=20*mm, leftMargin=20*mm,
                              topMargin=15*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        elements = []
        
        # 1. Definir estilo para medicamentos primero
        medicamento_style = ParagraphStyle(
            name='MedicamentoStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=9,
            alignment=0,
            wordWrap='LTR',
            splitLongWords=True
        )
        
        # 2. Agregar logo
        logo_path = os.path.join(settings.BASE_DIR, 'farmacia/static/farmacia/img/logo.jpg')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=180*mm, height=(175*180/1236)*mm)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 15*mm))
        
        # 3. Título
        titulo = Paragraph('<para align=center><font size=14><b>REPORTE DE ENTRADA DE MEDICAMENTOS</b></font></para>', styles['Normal'])
        elements.append(titulo)
        elements.append(Spacer(1, 8*mm))
        
        # 4. Información de cabecera
        info_data = [
            ['Folio: ', data.get('folio', 'N/A'), 'Fecha: ', data.get('fecha', 'N/A')],
            ['Tipo Entrada: ', data.get('tipo_entrada', 'N/A'), 'Almacén: ', data.get('almacen_nombre', 'N/A')],
            ['Fuente Financ.: ', data.get('fuente_financiamiento_nombre', 'N/A'), 'Proceso: ', data.get('proceso', 'N/A')]
        ]
        
        info_table = Table(info_data, colWidths=[35*mm, 60*mm, 40*mm, 60*mm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 8*mm))
        
        # 5. Tabla de items
        encabezados = [
            Paragraph('<b>Medicamento</b>', styles['Normal']),
            Paragraph('<b>Lote</b>', styles['Normal']),
            Paragraph('<b>Presentación</b>', styles['Normal']),
            Paragraph('<b>Cantidad</b>', styles['Normal']),
            Paragraph('<b>P. Unitario</b>', styles['Normal']),
            Paragraph('<b>Total</b>', styles['Normal'])
        ]
        datos_tabla = [encabezados]

        # Procesar items una sola vez
        for item in data.get('items', []):
            fila = [
                Paragraph(item.get('nombre', '')),  # Usa el estilo por defecto
                item.get('lote', ''),
                item.get('presentacion', ''),
                str(item.get('cantidad', 0)),
                f"${float(item.get('precio_unitario', 0)):,.2f}",
                f"${float(item.get('total', 0)):,.2f}"
                ]
            datos_tabla.append(fila)

        # Total general (fuera del bucle)
        datos_tabla.append([
            '', '', '', '',
            Paragraph('<b>TOTAL GENERAL:</b>', styles['Normal']),
            f"${float(data.get('total', 0)):,.2f}"
        ])
        
        # Crear tabla con ajustes
        tabla = Table(datos_tabla, colWidths=[80*mm, 25*mm, 35*mm, 20*mm, 25*mm, 25*mm])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (0,1), (0,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('BACKGROUND', (4,-1), (-1,-1), colors.HexColor('#70AD47')),
            ('TEXTCOLOR', (4,-1), (-1,-1), colors.whitesmoke),
            ('FONTNAME', (4,-1), (-1,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('FONTSIZE', (0,1), (-1,-2), 8),
            ('LEADING', (0,1), (0,-2), 9),
        ]))
        
        elements.append(tabla)
        elements.append(Spacer(1, 15*mm))
        
        # 6. Firmas
        firmas_data = [
            ['', '', ''],
            ['________________________', '________________________', '________________________'],
            ['Recibido por', 'Autorizado por', 'Entregado por'],
            ['Nombre y Firma', 'Nombre y Firma', 'Nombre y Firma']
        ]
        
        firmas_table = Table(firmas_data, colWidths=[60*mm, 60*mm, 60*mm])
        firmas_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('SPAN', (0,0), (2,0)),
            ('LEADING', (1,1), (2,1), 14),
        ]))
        elements.append(firmas_table)
        
        # 7. Pie de página
        elements.append(Spacer(1, 10*mm))
        footer = Paragraph(
            f"<font size=7>Generado el {timezone.now().strftime('%d/%m/%Y %H:%M')} por {request.user.get_full_name()} | Sistema de Gestión Farmacéutica</font>", 
            styles['Normal'])
        elements.append(footer)
        
        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ENTRADA_{data.get("folio", "REPORTE")}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Error al generar PDF: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
                

@csrf_exempt
def generar_reporte_excel(request):
    try:
        data = json.loads(request.body)
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte de Entradas"

        # ===== 1. CONFIGURACIÓN INICIAL =====
        # Estilo de borde
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # ===== 2. LOGO (1236x175 px) =====
        logo_path = os.path.join(settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg')
        if os.path.exists(logo_path):
            img = ExcelImage(logo_path)
            # Ajuste preciso de dimensiones (1236x175 px → Excel usa puntos, 1px ≈ 0.75pt)
            img.width = 1236 * 0.75  # Ancho en puntos
            img.height = 175 * 0.75  # Alto en puntos
            ws.add_image(img, 'A1')  # Logo en celda A1
            ws.row_dimensions[1].height = 135  # 175px ≈ 135 puntos (ajuste empírico)

        # ===== 3. CABECERA =====
        # Título principal
        ws.merge_cells('A3:F3')
        title_cell = ws['A3']
        title_cell.value = "REPORTE DE ENTRADA DE MEDICAMENTOS"
        title_cell.font = Font(bold=True, size=14)
        title_cell.alignment = Alignment(horizontal='center')

        # Datos de cabecera
        header_data = [
            ("Folio:", data.get('folio', '')),
            ("Fecha:", data.get('fecha', '')),
            ("Tipo de entrada:", data.get('tipo_entrada', '')),
            ("Almacén:", data.get('almacen_nombre', '')),
            ("Fuente de financiamiento:", data.get('fuente_financiamiento_nombre', ''))
        ]

        for i, (label, value) in enumerate(header_data, start=4):
            ws[f'A{i}'] = label
            ws[f'B{i}'] = value
            ws.merge_cells(f'B{i}:F{i}')

        # ===== 4. TABLA DE ITEMS =====
        # Encabezados de tabla
        headers = ["Medicamento", "Lote", "Presentación", "Cantidad", "Precio Unitario", "Total"]
        ws.append([''] * 6)  # Espacio antes de la tabla
        start_row = ws.max_row + 1
        ws.append(headers)

        # Estilo para encabezados
        for col in range(1, 7):
            cell = ws.cell(row=start_row, column=col)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="70AD47", fill_type="solid")
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = thin_border

        # ===== 5. LLENAR DATOS =====
        for item in data.get('items', []):
            row = [
                item.get('nombre', ''),
                item.get('lote', ''),
                item.get('presentacion', ''),
                item.get('cantidad', 0),
                item.get('precio_unitario', 0),
                item.get('total', 0)
            ]
            ws.append(row)

        # ===== 6. FORMATO Y AJUSTES =====
        # Ajuste de columnas (ancho automático + mínimo)
        column_widths = {
            'A': 40,  # Medicamento
            'B': 20,  # Lote
            'C': 25,  # Presentación
            'D': 15,  # Cantidad
            'E': 20,  # Precio
            'F': 20   # Total
        }

        for col_letter, width in column_widths.items():
            ws.column_dimensions[col_letter].width = width

        # Formato numérico y alineación
        for row in ws.iter_rows(min_row=start_row + 1, max_col=6, max_row=ws.max_row):
            for cell in row:
                cell.border = thin_border
                cell.alignment = Alignment(vertical='center', wrap_text=True)
            
            # Formato moneda para precios
            row[4].number_format = '"$"#,##0.00'
            row[5].number_format = '"$"#,##0.00'
            row[3].alignment = Alignment(horizontal='center')  # Cantidad centrada

        # ===== 7. TOTAL GENERAL =====
        total_row = ws.max_row + 1
        ws.merge_cells(f'A{total_row}:E{total_row}')
        ws[f'A{total_row}'] = "TOTAL GENERAL:"
        ws[f'A{total_row}'].font = Font(bold=True)
        ws[f'F{total_row}'] = float(data.get('total', 0))
        ws[f'F{total_row}'].font = Font(bold=True)
        ws[f'F{total_row}'].number_format = '"$"#,##0.00'

        # ===== 8. FIRMAS =====
        firma_row = total_row + 3
        firmas = [
            ('B', "RECIBIDO POR:"),
            ('D', "AUTORIZADO POR:"),
            ('F', "ENTREGADO POR:")
        ]

        for col, texto in firmas:
            ws[f'{col}{firma_row}'] = texto
            ws[f'{col}{firma_row + 1}'] = '________________________'
            ws[f'{col}{firma_row + 2}'] = 'Nombre y Firma'
            
            for offset in [0, 1, 2]:
                ws[f'{col}{firma_row + offset}'].alignment = Alignment(horizontal='center')

        # ===== 9. PIE DE PÁGINA =====
        ws[f'A{firma_row + 4}'] = f"Generado el {timezone.now().strftime('%d/%m/%Y %H:%M')} por {request.user.get_full_name()}"

        # ===== 10. GUARDAR =====
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="ENTRADA_{data.get("folio", "REPORTE")}.xlsx"'
        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


class RegisterAPIView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': serializer.data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    

@login_required
def registrar_salida(request):
    if request.method == 'POST':
        
        # 1. Extraer datos (sin cambios)
        curp = request.POST.get('paciente_curp', '').strip().upper()
        nombre = request.POST.get('paciente_nombre')
        nacimiento_str = request.POST.get('paciente_nacimiento')
        origen = request.POST.get('receta_origen')
        folio = request.POST.get('receta_folio')
        surtido_por = f"{request.user.first_name} {request.user.last_name}"

        # 2. Extraer items (sin cambios)
        items_para_guardar = []
        index = 0
        while True:
            lote_id = request.POST.get(f'item_lote_{index}')
            cantidad_str = request.POST.get(f'item_cantidad_{index}')
            if not lote_id or not cantidad_str: break
            try:
                lote = Lote.objects.get(id=lote_id)
                cantidad = int(cantidad_str)
                if cantidad <= 0: raise Exception(f"Cantidad inválida para {lote.lote_codigo}")
                if cantidad > lote.existencia: raise Exception(f"Stock insuficiente para {lote.lote_codigo}")
                items_para_guardar.append({'lote': lote, 'cantidad': cantidad})
                index += 1
            except (Lote.DoesNotExist, ValueError, Exception) as e:
                return JsonResponse({"success": False, "error": str(e)}, status=400)

        if not items_para_guardar:
            return JsonResponse({"success": False, "error": "No hay medicamentos en la lista."}, status=400)

        # 3. Guardar todo
        try:
            with transaction.atomic():
                
                # --- ¡AQUÍ ESTÁ LA NUEVA LÓGICA DE GUARDADO! ---
                try:
                    nacimiento_obj = datetime.strptime(nacimiento_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    messages.error(request, "La fecha de nacimiento es inválida.")
                    return JsonResponse({"success": False, "error": "Fecha de nacimiento inválida."}, status=400)

                # 3.1. Buscar o Crear Paciente
                if curp:
                    # Si SÍ hay CURP, lo usamos como llave (como antes)
                    paciente, _ = Paciente.objects.update_or_create(
                        curp=curp,
                        defaults={
                            'nombre_completo': nombre, 
                            'fecha_nacimiento': nacimiento_obj
                        }
                    )
                else:
                    # Si NO hay CURP, usamos Nombre + Fecha Nacimiento como llave
                    # (get_or_create es más seguro para no sobreescribir datos)
                    paciente, _ = Paciente.objects.get_or_create(
                        nombre_completo=nombre,
                        fecha_nacimiento=nacimiento_obj,
                        defaults={'curp': None} # Le ponemos None al CURP
                    )
                # --- FIN DE LA NUEVA LÓGICA DE GUARDADO ---

                # 3.2. Crear UNA Receta (sin cambios)
                if not folio:
                    folio = f"SAL-MULTI-{paciente.id}-{int(timezone.now().timestamp())}"
                
                receta_salida = Receta.objects.create(
                    id_folio=folio,
                    paciente=paciente, 
                    fecha_emision=timezone.now().date(),
                    fecha_surtido=timezone.now().date(), 
                    estado='completa',
                    origen=origen,
                    surtido_por=request.user 
                )

                # 3.3. Guardar CADA item y restar stock (sin cambios)
                for item in items_para_guardar:
                    lote = item['lote']
                    cantidad = item['cantidad']
                    RecetaMedicamento.objects.create(
                        receta=receta_salida,
                        medicamento=lote.medicamento, 
                        lote=lote, 
                        cantidad_solicitada=cantidad,
                        cantidad_surtida=cantidad
                    )
                    lote.existencia -= cantidad
                    lote.save(update_fields=['existencia'])
            
            # 4. Éxito: Devolver JSON (sin cambios)
            pdf_url = reverse('descargar_comprobante', args=[receta_salida.pk])
            return JsonResponse({
                "success": True, 
                "message": "Salida registrada exitosamente.",
                "pdf_url": pdf_url 
            })
        
        except Exception as e:
            traceback.print_exc() 
            return JsonResponse({"success": False, "error": str(e)}, status=500)
            
    # --- LÓGICA GET (sin cambios) ---
    form = SalidaForm() 
    context = {
        'form': form,
        'titulo_pagina': 'Registro de Salidas'
    }
    return render(request, 'salida_medicamentos.html', context)


# ==================================================
# VISTA 2: DESCARGAR EL PDF (NUEVA)
# ==================================================
@login_required
def descargar_comprobante(request, receta_id):
    try:
        # Buscamos la receta por su folio
        receta = get_object_or_404(Receta.objects.select_related('paciente', 'surtido_por'), pk=receta_id)
        
        # 4. Generar el PDF
        pdf_buffer = generar_pdf_salida(receta) # ¡Función actualizada!
        
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="salida_{receta.id_folio}.pdf"'
        return response
        
    except Exception as e:
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect('registrar_salida')

@login_required 
@require_http_methods(["POST"]) # Asumo que recibirás fechas por POST (igual que en entradas)
def generar_excel_salidas(request):
    """
    Genera un reporte en Excel de todas las salidas (RecetaMedicamento)
    en un rango de fechas.
    """
    try:
        # Asumo que envías un JSON con 'fecha_inicio' y 'fecha_fin'
        # Si no, necesitarás un formulario
        
        # Si no usas JSON, y usas un form normal, sería request.POST.get('fecha_inicio')
        data = json.loads(request.body) 
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')

        # Si las fechas no vienen, puedes usar un rango por defecto (ej. el día de hoy)
        if not fecha_inicio:
            fecha_inicio = timezone.now().replace(hour=0, minute=0, second=0)
        if not fecha_fin:
            fecha_fin = timezone.now().replace(hour=23, minute=59, second=59)

        # 1. La consulta a la base de datos (la parte clave)
        salidas = RecetaMedicamento.objects.filter(
            receta__fecha_surtido__range=(fecha_inicio, fecha_fin)
        ).order_by('receta__fecha_surtido', 'lote__medicamento__descripcion')

        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte de Salidas"

        # 2. Títulos
        titulos = ['Fecha Surtido', 'Área', 'Médico/Quien Solicita', 'Clave', 'Medicamento', 'Lote', 'Cantidad Surtida']
        ws.append(titulos)
        
        # (Opcional: Ponerlos en negrita)
        for cell in ws[1]:
            cell.font = Font(bold=True)

        # 3. Datos
        for item in salidas:
            ws.append([
                item.receta.fecha_surtido.strftime('%d/%m/%Y %H:%M'),
                item.receta.area.nombre if item.receta.area else 'N/A',
                item.receta.medico,
                item.lote.medicamento.clave,
                item.lote.medicamento.descripcion,
                item.lote.lote_codigo,
                item.cantidad_surtida
            ])

        # (Aquí puedes ajustar anchos de columna, etc.)

        # 4. Guardar en buffer y devolver
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="REPORTE_SALIDAS_{fecha_inicio}_{fecha_fin}.xlsx"'
        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def get_paciente_info_json(request, curp):
    """
    Vista que devuelve la información de un Paciente como JSON
    para ser usada por JavaScript al teclear el CURP.
    """
    if request.method == "GET":
        try:
            # --- ¡CAMBIO IMPORTANTE! ---
            # Usamos .get() en lugar de get_object_or_404
            # para poder atrapar el error 'DoesNotExist' nosotros mismos.
            paciente = Paciente.objects.get(curp=curp.upper())
            
            # Si lo encuentra, preparamos los datos
            data = {
                'id': paciente.id,
                'nombre_completo': paciente.nombre_completo,
                'curp': paciente.curp,
                # El input HTML de tipo 'date' necesita el formato AAAA-MM-DD
                'fecha_nacimiento': paciente.fecha_nacimiento.strftime('%Y-%m-%d'), 
            }
            return JsonResponse(data) # Devuelve 200 OK
        
        except Paciente.DoesNotExist: 
            # ¡Esto es lo que queremos! Significa que es un paciente nuevo.
            # El JS está esperando este error 404 para dejarte escribir.
            return JsonResponse({'error': 'Paciente no encontrado'}, status=404)
        except Exception as e:
            # Atrapa cualquier otro error 
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def buscar_lote_json(request, query):
    """
    Vista UNIFICADA que busca un lote.
    Intenta buscar por ID (pk) O por Código de Lote.
    """
    if request.method == "GET":
        try:
            # ¡Aquí está la magia!
            # Buscamos un Lote donde el ID (pk) sea la query
            # O (el | significa 'OR') el lote_codigo sea la query
            lote = Lote.objects.get(
                Q(id=query) | Q(lote_codigo=query.upper())
            )
            
            # Si lo encontramos (por cualquiera de los dos), devolvemos los datos
            data = {
                'id': lote.id, # El ID (pk) que usará el formulario ('auto-B1011')
                'medicamento_nombre': lote.medicamento.descripcion,
                'clave': lote.medicamento.clave,
                'lote_numero': lote.lote_codigo,
                'caducidad': lote.fecha_caducidad.strftime('%d/%m/%Y'),
                'cantidad_actual': lote.existencia,
            }
            return JsonResponse(data)
        
        except Lote.DoesNotExist: 
            return JsonResponse({'error': f'Lote "{query}" no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def get_paciente_by_name(request, nombre):
    """
    Busca al primer paciente que coincida (ignorando mayúsculas) con el nombre.
    """
    if request.method == "GET":
        try:
            # Usamos filter() + first() porque los nombres se pueden repetir
            paciente = Paciente.objects.filter(nombre_completo__iexact=nombre).first()
            
            if paciente: # Si encontró uno
                data = {
                    'id': paciente.id,
                    'nombre_completo': paciente.nombre_completo,
                    'curp': paciente.curp or '', # Devolvemos '' si es None
                    'fecha_nacimiento': paciente.fecha_nacimiento.strftime('%Y-%m-%d'), 
                }
                return JsonResponse(data)
            else:
                # No es un error, solo que no existe
                return JsonResponse({'error': 'Paciente no encontrado'}, status=404)
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def carga_masiva(request):
    """Vista para mostrar el formulario de carga masiva"""
    form = CargaMasivaForm()
    return render(request, 'carga_masiva.html', {
        'form': form,
        'user': request.user
    })

@csrf_exempt
@login_required
def procesar_carga_masiva(request):
    """Procesa el archivo Excel de carga masiva"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    form = CargaMasivaForm(request.POST, request.FILES)
    if not form.is_valid():
        errores = []
        for field, errors in form.errors.items():
            for error in errors:
                errores.append(str(error))
        return JsonResponse({'error': ', '.join(errores)}, status=400)
    
    from .utils import ProcesadorCargaMasiva
    archivo = form.cleaned_data['archivo']
    procesador = ProcesadorCargaMasiva(archivo)
    resultado = procesador.procesar()
    
    # Si hay error crítico en el procesamiento
    if 'error' in resultado:
        return JsonResponse(resultado, status=400)
    
    # Preparar respuesta con advertencias
    response_data = {
        'success': True,
        'mensaje': 'Carga masiva completada',
        'resultados': {
            'total': resultado['resultados']['total'],
            'exitosos': resultado['resultados']['exitosos'],
            'actualizados': resultado['resultados']['actualizados'],
            'errores': resultado['resultados']['errores'],
            'advertencias': resultado['resultados'].get('advertencias', [])  # ← NUEVO
        }
    }
    
    # Código de estado basado en si hubo errores
    status_code = 200 if len(resultado['resultados']['errores']) == 0 else 207  # 207 = Multi-Status
    
    return JsonResponse(response_data, status=status_code)

@login_required
def exportar_inventario_excel(request):
    """Exportar inventario a Excel con logo"""
    try:
        import xlsxwriter
        
        lotes = Lote.objects.select_related('medicamento', 'presentacion').all()
        
        # Crear archivo en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Inventario')
        
        # Definir formatos
        header_format = workbook.add_format({
            'bg_color': '#8B0000',
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 11
        })
        
        title_format = workbook.add_format({
            'bg_color': '#8B0000',
            'font_color': 'white',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14
        })
        
        date_format = workbook.add_format({
            'italic': True,
            'align': 'left',
            'font_size': 10
        })
        
        data_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 10
        })
        
        red_format = workbook.add_format({
            'bg_color': '#FF0000',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bold': True
        })
        
        orange_format = workbook.add_format({
            'bg_color': '#FF4444',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        yellow_format = workbook.add_format({
            'bg_color': '#FFFF00',
            'font_color': 'black',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        green_format = workbook.add_format({
            'bg_color': '#00B050',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Establecer ancho de columnas
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 12)
        worksheet.set_column('G:G', 15)
        
        # Agregar logo
        logo_path = os.path.join(settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg')
        if os.path.exists(logo_path):
            try:
                # Insertar logo en A1, redimensionado
                worksheet.insert_image('A1', logo_path, {
                    'x_scale': 0.8,
                    'y_scale': 0.8,
                    'x_offset': 0,
                    'y_offset': 0
                })
            except Exception as e:
                print(f"Error insertando logo: {e}")
        
        # Título (desplazado después del logo)
        worksheet.merge_range('A3:G3', 'REPORTE DE INVENTARIO DE MEDICAMENTOS POR LOTE', title_format)
        worksheet.set_row(2, 25)
        
        # Fecha
        worksheet.merge_range('A4:G4', f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", date_format)
        worksheet.set_row(3, 18)
        
        # Encabezados
        headers = ['Clave', 'Descripción', 'Lote', 'Presentación', 'Existencia', 'CPM', 'Caducidad']
        for col, header in enumerate(headers):
            worksheet.write(5, col, header, header_format)
        worksheet.set_row(5, 20)
        
        # Datos
        row = 6
        for lote in lotes:
            worksheet.write(row, 0, lote.medicamento.clave, data_format)
            worksheet.write(row, 1, lote.medicamento.descripcion, data_format)
            worksheet.write(row, 2, lote.lote_codigo, data_format)
            worksheet.write(row, 3, lote.presentacion.nombre if lote.presentacion else 'N/A', data_format)
            worksheet.write(row, 4, lote.existencia, data_format)
            worksheet.write(row, 5, lote.cpm, data_format)
            
            # Determinar color según caducidad
            dias_restantes = (lote.fecha_caducidad - datetime.now().date()).days
            fecha_str = lote.fecha_caducidad.strftime('%d/%m/%Y')
            
            if dias_restantes <= 0:
                worksheet.write(row, 6, fecha_str, red_format)
            elif dias_restantes <= 30:
                worksheet.write(row, 6, fecha_str, orange_format)
            elif dias_restantes <= 90:
                worksheet.write(row, 6, fecha_str, yellow_format)
            else:
                worksheet.write(row, 6, fecha_str, green_format)
            
            worksheet.set_row(row, 18)
            row += 1
        
        # Pie de página
        worksheet.merge_range(row + 1, 0, row + 1, 6, 'Documento generado automáticamente por INVENTFARM', date_format)
        
        # Finalizar
        workbook.close()
        
        # Preparar respuesta
        output.seek(0)
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="Inventario_{datetime.now().strftime("%d%m%Y")}.xlsx"'
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'Error: {str(e)}', status=400)



@login_required
def exportar_inventario_pdf(request):
    """Exportar inventario a PDF con logo"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        
        lotes = Lote.objects.select_related('medicamento', 'presentacion').all()
        
        # Crear PDF en memoria
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter  # 8.5" x 11"
        
        # ✅ RUTA CORRECTA (igual a pdf_utils.py)
        logo_path = os.path.join(settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg')
        
        # Configurar logo (dimensiones 1236x175 -> ratio ~7:1)
        logo_width = 7.0 * inch
        logo_height = 1.0 * inch
        
        # Centrar logo
        x_logo = (width - logo_width) / 2
        y_logo = height - (0.75 * inch) - logo_height
        
        # Dibujar logo
        if os.path.exists(logo_path):
            try:
                p.drawImage(logo_path, x_logo, y_logo,
                           width=logo_width, height=logo_height,
                           preserveAspectRatio=True)
            except Exception as e:
                print(f"Error cargando logo: {e}")
        else:
            print(f"Logo no encontrado en: {logo_path}")
        
        # Posición para el contenido después del logo
        y_actual = y_logo - (0.25 * inch)
        
        # Título
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width / 2.0, y_actual, "REPORTE DE INVENTARIO DE MEDICAMENTOS")
        y_actual -= 20
        
        # Fecha
        p.setFont("Helvetica", 10)
        p.drawCentredString(width / 2.0, y_actual, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y_actual -= 20
        
        # Línea divisoria
        p.line(inch, y_actual, width - inch, y_actual)
        y_actual -= 20
        
        # Tabla de datos
        data_tabla = [['Clave', 'Descripción', 'Lote', 'Pres.', 'Exist.', 'CPM', 'Caducidad']]
        
        for lote in lotes:
            data_tabla.append([
                lote.medicamento.clave,
                lote.medicamento.descripcion[:25] + '...' if len(lote.medicamento.descripcion) > 25 else lote.medicamento.descripcion,
                lote.lote_codigo,
                lote.presentacion.nombre[:8] if lote.presentacion else 'N/A',
                str(lote.existencia),
                str(lote.cpm),
                lote.fecha_caducidad.strftime('%d/%m/%Y')
            ])
        
        tabla = Table(data_tabla, colWidths=[0.9*inch, 2.2*inch, 0.8*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.9*inch])
        
        # Estilo de tabla
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8B0000")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        # Obtener altura de la tabla
        wrap_height = tabla.wrapOn(p, width - 2*inch, height)[1]
        y_tabla = y_actual - wrap_height - 20
        
        # Si no cabe en la página, crear nueva página
        if y_tabla < (inch * 2.5):
            p.showPage()
            y_tabla = height - inch - wrap_height
        
        # Dibujar tabla
        tabla.drawOn(p, inch, y_tabla)
        
        # Pie de página
        p.setFont("Helvetica", 9)
        p.drawCentredString(width / 2.0, inch * 0.5, "Documento generado por INVENTFARM")
        
        # Finalizar PDF
        p.showPage()
        p.save()
        
        # Retornar como descarga
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Inventario_{datetime.now().strftime("%d%m%Y")}.pdf"'
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f'Error: {str(e)}', status=400)


