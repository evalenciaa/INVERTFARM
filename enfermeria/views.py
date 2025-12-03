import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import permission_required
from django.views.decorators.cache import never_cache
from datetime import datetime, timedelta
from .models import Colectivo, ColectivoMedicamento
from farmacia.models import Medicamento, Paciente, Lote

# ===== DECORADOR DE PERMISOS =====
def enfermeria_requerida(user):
    """Verifica que el usuario sea de enfermería"""
    return user.is_authenticated and (user.rol == 'ENFERMERIA' or user.is_superuser)

def farmacia_requerida(user):
    """Verifica que el usuario sea de farmacia"""
    return user.is_authenticated and (user.rol == 'FARMACIA' or user.is_superuser)


# ===== VISTA PRINCIPAL DE ENFERMERÍA =====
@never_cache
@login_required(login_url='login')
@user_passes_test(enfermeria_requerida, login_url='principal')
def enfermeria_principal(request):
    """
    Vista principal del módulo de enfermería
    Muestra tarjeta de acceso a colectivos
    """
    return render(request, 'enfermeria.html', {
        'user': request.user
    })


# ===== LISTA DE COLECTIVOS (ENFERMERÍA) =====
@never_cache
@login_required(login_url='login')
@user_passes_test(enfermeria_requerida, login_url='principal')
def lista_colectivos_enfermeria(request):
    """
    Vista de lista de colectivos para enfermería
    Muestra todos los colectivos creados por el enfermero
    """
    # Filtros
    estado_filtro = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')
    
    # Query base - solo colectivos del enfermero actual
    colectivos = Colectivo.objects.filter(
        enfermero_solicitante=request.user
    ).select_related(
        'paciente', 
        'enfermero_solicitante', 
        'farmaceutico_asignado'
    ).prefetch_related('medicamentos')
    
    # Aplicar filtros
    if estado_filtro:
        colectivos = colectivos.filter(estado=estado_filtro)
    
    if busqueda:
        colectivos = colectivos.filter(
            Q(folio__icontains=busqueda) |
            Q(paciente__nombre_completo__icontains=busqueda) |
            Q(numero_cama__icontains=busqueda)
        )
    
    # Estadísticas
    stats = {
        'total': colectivos.count(),
        'pendientes': colectivos.filter(estado='PENDIENTE').count(),
        'respondidos': colectivos.filter(estado='RESPONDIDO').count(),
        'completados': colectivos.filter(estado='COMPLETADO').count(),
        'cancelados': colectivos.filter(estado='CANCELADO').count(),
    }
    
    return render(request, 'lista_colectivos.html', {
        'colectivos': colectivos,
        'stats': stats,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'user': request.user
    })


# ===== CREAR NUEVO COLECTIVO =====
@never_cache
@login_required(login_url='login')
@user_passes_test(enfermeria_requerida, login_url='principal')
@require_http_methods(["GET", "POST"])
def crear_colectivo(request):
    """
    Formulario para crear un nuevo colectivo
    """
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            paciente_id = request.POST.get('paciente_id')
            numero_cama = request.POST.get('numero_cama')
            servicio = request.POST.get('servicio')
            observaciones = request.POST.get('observaciones', '')
            
            # Validaciones
            if not all([paciente_id, numero_cama, servicio]):
                messages.error(request, 'Todos los campos obligatorios deben ser completados')
                return redirect('crear_colectivo')
            
            # Obtener paciente
            paciente = get_object_or_404(Paciente, id=paciente_id)
            
            # Crear colectivo
            colectivo = Colectivo.objects.create(
                paciente=paciente,
                enfermero_solicitante=request.user,
                numero_cama=numero_cama,
                servicio=servicio,
                observaciones_enfermeria=observaciones,
                estado='PENDIENTE'
            )
            
            # Procesar medicamentos
            medicamentos_ids = request.POST.getlist('medicamento_id[]')
            cantidades = request.POST.getlist('cantidad[]')
            
            if not medicamentos_ids:
                colectivo.delete()
                messages.error(request, 'Debe agregar al menos un medicamento')
                return redirect('crear_colectivo')
            
            # Crear relaciones de medicamentos
            for med_id, cantidad in zip(medicamentos_ids, cantidades):
                if med_id and cantidad:
                    medicamento = get_object_or_404(Medicamento, id=med_id)
                    ColectivoMedicamento.objects.create(
                        colectivo=colectivo,
                        medicamento=medicamento,
                        cantidad_solicitada=int(cantidad)
                    )
            
            messages.success(request, f'Colectivo {colectivo.folio} creado exitosamente')
            return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo.id)
            
        except Exception as e:
            messages.error(request, f'Error al crear colectivo: {str(e)}')
            return redirect('crear_colectivo')
    
    # GET - Mostrar formulario
    pacientes = Paciente.objects.all().order_by('nombre_completo')
    medicamentos = Medicamento.objects.filter(activo=True).order_by('descripcion')
    
    return render(request, 'crear_colectivo.html', {
        'pacientes': pacientes,
        'medicamentos': medicamentos,
        'user': request.user
    })


# ===== VER DETALLE DE COLECTIVO (ENFERMERÍA) =====
@never_cache
@login_required(login_url='login')
@user_passes_test(enfermeria_requerida, login_url='principal')
def detalle_colectivo_enfermeria(request, colectivo_id):
    """
    Vista de detalle de un colectivo para enfermería
    Permite editar si está en estado RESPONDIDO
    """
    colectivo = get_object_or_404(
        Colectivo.objects.select_related('paciente', 'farmaceutico_asignado'),
        id=colectivo_id,
        enfermero_solicitante=request.user  # Solo puede ver sus propios colectivos
    )
    
    medicamentos = colectivo.medicamentos.select_related('medicamento').all()
    
    return render(request, 'detalle_colectivo.html', {
        'colectivo': colectivo,
        'medicamentos': medicamentos,
        'user': request.user
    })


# ===== CANCELAR COLECTIVO =====
@never_cache
@login_required(login_url='login')
@user_passes_test(enfermeria_requerida, login_url='principal')
@require_http_methods(["POST"])
def cancelar_colectivo(request, colectivo_id):
    """
    Cancelar un colectivo (solo si está PENDIENTE o RESPONDIDO)
    """
    colectivo = get_object_or_404(
        Colectivo,
        id=colectivo_id,
        enfermero_solicitante=request.user
    )
    
    if colectivo.estado in ['PENDIENTE', 'RESPONDIDO']:
        colectivo.estado = 'CANCELADO'
        colectivo.save()
        messages.success(request, f'Colectivo {colectivo.folio} cancelado')
    else:
        messages.error(request, 'No se puede cancelar un colectivo completado')
    
    return redirect('lista_colectivos_enfermeria')


# ===== EDITAR Y REENVIAR COLECTIVO =====
@never_cache
@login_required(login_url='login')
@user_passes_test(enfermeria_requerida, login_url='principal')
@require_http_methods(["POST"])
def editar_colectivo(request, colectivo_id):
    """
    Editar un colectivo respondido y reenviarlo a farmacia
    """
    # Importar el modelo de farmacia
    from farmacia.models import Medicamento
    
    colectivo = get_object_or_404(
        Colectivo,
        id=colectivo_id,
        enfermero_solicitante=request.user
    )
    
    if colectivo.estado != 'RESPONDIDO':
        messages.error(request, 'Solo se pueden editar colectivos respondidos por farmacia')
        return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo.id)
    
    try:
        with transaction.atomic():
            # ✅ Actualizar observaciones
            observaciones = request.POST.get('observaciones', '').strip()
            if observaciones:
                colectivo.observaciones_enfermeria = observaciones
            
            # ✅ Obtener TODOS los medicamento_id[] y cantidad[]
            medicamentos_ids = request.POST.getlist('medicamento_id[]')
            cantidades = request.POST.getlist('cantidad[]')
            
            print(f"📥 Datos recibidos del formulario:")
            print(f"   medicamentos_ids: {medicamentos_ids}")
            print(f"   cantidades: {cantidades}")
            
            # ✅ Filtrar y validar datos
            medicamentos_validos = []
            
            for med_id, cantidad in zip(medicamentos_ids, cantidades):
                # Verificar que ambos valores existan y no estén vacíos
                if med_id and cantidad and str(med_id).strip() and str(cantidad).strip():
                    try:
                        # ✅ med_id es un string como "MED-0007", NO convertir a int
                        med_id_str = str(med_id).strip()
                        cantidad_int = int(cantidad)
                        
                        # Verificar que la cantidad sea positiva
                        if cantidad_int > 0:
                            medicamentos_validos.append({
                                'id': med_id_str,  # ✅ Guardar como string
                                'cantidad': cantidad_int
                            })
                            print(f"   ✅ Medicamento válido: ID={med_id_str}, Cantidad={cantidad_int}")
                        else:
                            print(f"   ⚠️ Cantidad inválida: {cantidad_int}")
                    except (ValueError, TypeError) as e:
                        print(f"   ❌ Error al procesar: med_id={med_id}, cantidad={cantidad}, error={e}")
                        continue
                else:
                    print(f"   ⏭️ Par ignorado (vacío o deshabilitado): med_id={med_id}, cantidad={cantidad}")
            
            print(f"📊 Total medicamentos válidos: {len(medicamentos_validos)}")
            
            # ✅ Validar que haya al menos un medicamento
            if not medicamentos_validos:
                messages.error(request, 'Debe haber al menos un medicamento en el colectivo')
                return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo.id)
            
            # ✅ Eliminar todos los medicamentos actuales
            colectivo.medicamentos.all().delete()
            print(f"🗑️ Medicamentos anteriores eliminados")
            
            # ✅ Agregar medicamentos válidos
            for item in medicamentos_validos:
                try:
                    # ✅ Buscar medicamento por ID string
                    medicamento = Medicamento.objects.get(id=item['id'])
                    ColectivoMedicamento.objects.create(
                        colectivo=colectivo,
                        medicamento=medicamento,
                        cantidad_solicitada=item['cantidad']
                    )
                    print(f"   ➕ Agregado: {medicamento.clave} - Cantidad: {item['cantidad']}")
                except Medicamento.DoesNotExist:
                    print(f"   ❌ Medicamento no encontrado: ID={item['id']}")
                    messages.error(request, f'Medicamento con ID {item["id"]} no encontrado')
                    return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo.id)
            
            # ✅ Cambiar estado a PENDIENTE nuevamente
            colectivo.estado = 'PENDIENTE'
            colectivo.fecha_respuesta_farmacia = None
            colectivo.respuesta_farmacia = ''
            colectivo.save()
            
            print(f"✅ Colectivo {colectivo.folio} actualizado correctamente")
            messages.success(request, f'Colectivo {colectivo.folio} actualizado y reenviado a farmacia')
            return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo.id)
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error al editar colectivo: {str(e)}')
        return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo.id)




@login_required
def api_buscar_medicamentos(request):
    """API para autocompletado de medicamentos"""
    from farmacia.models import Medicamento
    
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    medicamentos = Medicamento.objects.filter(
        Q(clave__icontains=query) | Q(descripcion__icontains=query),
        activo=True
    ).order_by('descripcion')[:50]
    
    results = [{
        'id': med.id,  # ✅ Esto devolverá "MED-0007" (string)
        'clave': med.clave,
        'descripcion': med.descripcion,
        'text': f"{med.clave} - {med.descripcion}"
    } for med in medicamentos]
    
    print(f"🔍 Búsqueda: '{query}' → {len(results)} resultados")
    if results:
        print(f"   Ejemplo: ID={results[0]['id']} (tipo: {type(results[0]['id'])})")
    
    return JsonResponse({'results': results})




# ===== API: BUSCAR PACIENTES =====
@login_required
def api_buscar_pacientes(request):
    """
    API para autocompletado de pacientes
    """
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    pacientes = Paciente.objects.filter(
        Q(nombre_completo__icontains=query) | Q(curp__icontains=query)
    )[:10]
    
    results = [{
        'id': pac.id,
        'nombre': pac.nombre_completo,
        'curp': pac.curp or 'Sin CURP',
        'text': f"{pac.nombre_completo} - {pac.curp or 'Sin CURP'}"
    } for pac in pacientes]
    
    return JsonResponse({'results': results})


# ===== LISTA DE COLECTIVOS (FARMACIA) =====
@never_cache
@login_required(login_url='login')
@user_passes_test(farmacia_requerida, login_url='principal')
def lista_colectivos_farmacia(request):
    """
    Vista de lista de colectivos para farmacia
    Muestra todos los colectivos pendientes y en revisión
    """
    # Filtros
    estado_filtro = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')
    
    # Query base - todos los colectivos
    colectivos = Colectivo.objects.select_related(
        'paciente', 
        'enfermero_solicitante', 
        'farmaceutico_asignado'
    ).prefetch_related('medicamentos')
    
    # Aplicar filtros
    if estado_filtro:
        colectivos = colectivos.filter(estado=estado_filtro)
    else:
        # Por defecto, mostrar solo pendientes y en revisión
        colectivos = colectivos.exclude(estado__in=['COMPLETADO', 'CANCELADO'])
    
    if busqueda:
        colectivos = colectivos.filter(
            Q(folio__icontains=busqueda) |
            Q(paciente__nombre_completo__icontains=busqueda) |
            Q(numero_cama__icontains=busqueda) |
            Q(enfermero_solicitante__username__icontains=busqueda)
        )
    
    # Estadísticas
    stats = {
        'total': Colectivo.objects.count(),
        'pendientes': Colectivo.objects.filter(estado='PENDIENTE').count(),
        'en_revision': Colectivo.objects.filter(estado='EN_REVISION').count(),
        'completados_hoy': Colectivo.objects.filter(
            estado='COMPLETADO',
            fecha_completado__date=timezone.now().date()
        ).count(),
    }
    
    return render(request, 'farmacia/lista_colectivos_farmacia.html', {
        'colectivos': colectivos,
        'stats': stats,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'user': request.user
    })


# ===== VER DETALLE Y RESPONDER COLECTIVO (FARMACIA) =====
@never_cache
@login_required(login_url='login')
@user_passes_test(farmacia_requerida, login_url='principal')
def detalle_colectivo_farmacia(request, colectivo_id):
    """
    Vista de detalle de un colectivo para farmacia
    Permite marcar disponibilidad y agregar comentarios
    """
    colectivo = get_object_or_404(
        Colectivo.objects.select_related('paciente', 'enfermero_solicitante'),
        id=colectivo_id
    )
    
    # Cambiar estado a EN_REVISION si está PENDIENTE
    if colectivo.estado == 'PENDIENTE':
        colectivo.estado = 'EN_REVISION'
        colectivo.farmaceutico_asignado = request.user
        colectivo.save()
    
    medicamentos = colectivo.medicamentos.select_related('medicamento').all()
    
    # Obtener existencias disponibles por medicamento
    medicamentos_con_stock = []
    for item in medicamentos:
        # Calcular stock total disponible del medicamento
        stock_total = Lote.objects.filter(
            medicamento=item.medicamento,
            existencia__gt=0
        ).aggregate(total=Sum('existencia'))['total'] or 0
        
        medicamentos_con_stock.append({
            'item': item,
            'stock_disponible': stock_total,
            'suficiente': stock_total >= item.cantidad_solicitada
        })
    
    return render(request, 'farmacia/detalle_colectivo_farmacia.html', {
        'colectivo': colectivo,
        'medicamentos_con_stock': medicamentos_con_stock,
        'user': request.user
    })


# ===== RESPONDER COLECTIVO (FARMACIA) =====
@never_cache
@login_required(login_url='login')
@user_passes_test(farmacia_requerida, login_url='principal')
@require_http_methods(["POST"])
def responder_colectivo(request, colectivo_id):
    """
    Farmacia responde al colectivo indicando disponibilidad
    """
    colectivo = get_object_or_404(Colectivo, id=colectivo_id)
    
    if colectivo.estado not in ['PENDIENTE', 'EN_REVISION']:
        messages.error(request, 'Este colectivo ya fue respondido o completado')
        return redirect('detalle_colectivo_farmacia', colectivo_id=colectivo.id)
    
    try:
        # Actualizar respuesta general
        colectivo.respuesta_farmacia = request.POST.get('respuesta_farmacia', '')
        
        # Actualizar disponibilidad de cada medicamento
        for medicamento in colectivo.medicamentos.all():
            disponible = request.POST.get(f'disponible_{medicamento.id}') == 'on'
            comentario = request.POST.get(f'comentario_{medicamento.id}', '')
            
            medicamento.disponible = disponible
            medicamento.comentario_farmacia = comentario
            medicamento.save()
        
        # Cambiar estado a RESPONDIDO
        colectivo.estado = 'RESPONDIDO'
        colectivo.fecha_respuesta_farmacia = timezone.now()
        colectivo.farmaceutico_asignado = request.user
        colectivo.save()
        
        messages.success(request, f'Respuesta enviada a enfermería para colectivo {colectivo.folio}')
        return redirect('lista_colectivos_farmacia')
        
    except Exception as e:
        messages.error(request, f'Error al responder colectivo: {str(e)}')
        return redirect('detalle_colectivo_farmacia', colectivo_id=colectivo.id)


# ===== COMPLETAR SURTIDO DE COLECTIVO =====
@never_cache
@login_required(login_url='login')
@user_passes_test(farmacia_requerida, login_url='principal')
@require_http_methods(["POST"])
def completar_colectivo(request, colectivo_id):
    """
    Marca el colectivo como completado y descuenta del inventario
    """
    colectivo = get_object_or_404(Colectivo, id=colectivo_id)
    
    if colectivo.estado != 'EN_REVISION':
        messages.error(request, 'Solo se pueden completar colectivos en revisión')
        return redirect('detalle_colectivo_farmacia', colectivo_id=colectivo.id)
    
    try:
        # Verificar que todos los medicamentos tengan stock suficiente
        for medicamento in colectivo.medicamentos.all():
            cantidad_surtida = int(request.POST.get(f'cantidad_surtida_{medicamento.id}', 0))
            
            # Verificar stock disponible
            stock_total = Lote.objects.filter(
                medicamento=medicamento.medicamento,
                existencia__gt=0
            ).aggregate(total=Sum('existencia'))['total'] or 0
            
            if cantidad_surtida > stock_total:
                messages.error(
                    request, 
                    f'Stock insuficiente para {medicamento.medicamento.descripcion}. '
                    f'Disponible: {stock_total}, Solicitado: {cantidad_surtida}'
                )
                return redirect('detalle_colectivo_farmacia', colectivo_id=colectivo.id)
            
            # Actualizar cantidad surtida
            medicamento.cantidad_surtida = cantidad_surtida
            medicamento.save()
        
        # Descontar del inventario (FEFO - First Expired, First Out)
        for medicamento in colectivo.medicamentos.all():
            cantidad_restante = medicamento.cantidad_surtida
            
            # Obtener lotes ordenados por fecha de caducidad (más próximo primero)
            lotes = Lote.objects.filter(
                medicamento=medicamento.medicamento,
                existencia__gt=0
            ).order_by('fecha_caducidad')
            
            for lote in lotes:
                if cantidad_restante <= 0:
                    break
                
                if lote.existencia >= cantidad_restante:
                    # Este lote tiene suficiente
                    lote.existencia -= cantidad_restante
                    lote.save()
                    cantidad_restante = 0
                else:
                    # Agotar este lote y continuar con el siguiente
                    cantidad_restante -= lote.existencia
                    lote.existencia = 0
                    lote.save()
        
        # Marcar como completado
        colectivo.estado = 'COMPLETADO'
        colectivo.fecha_completado = timezone.now()
        colectivo.farmaceutico_asignado = request.user
        colectivo.save()
        
        messages.success(request, f'Colectivo {colectivo.folio} completado exitosamente')
        return redirect('generar_pdf_colectivo', colectivo_id=colectivo.id)
        
    except Exception as e:
        messages.error(request, f'Error al completar colectivo: {str(e)}')
        return redirect('detalle_colectivo_farmacia', colectivo_id=colectivo.id)


# ===== GENERAR PDF DEL COLECTIVO =====
@never_cache
@login_required(login_url='login')
def generar_pdf_colectivo(request, colectivo_id):
    """
    Genera PDF con la información del colectivo completado
    """
    colectivo = get_object_or_404(
        Colectivo.objects.select_related('paciente', 'enfermero_solicitante', 'farmaceutico_asignado'),
        id=colectivo_id
    )
    
    if colectivo.estado != 'COMPLETADO':
        messages.error(request, 'Solo se puede generar PDF de colectivos completados')
        return redirect('detalle_colectivo_farmacia', colectivo_id=colectivo.id)
    
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from io import BytesIO
        
        # Crear buffer para el PDF
        buffer = BytesIO()
        
        # Crear documento
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # Logo del hospital
        logo_path = os.path.join(settings.BASE_DIR, 'farmacia', 'static', 'farmacia', 'img', 'logo.jpg')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=3.5*inch, height=0.5*inch)
            elements.append(logo)
            elements.append(Spacer(1, 0.3*inch))
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#750000'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        title = Paragraph(f"COLECTIVO DE MEDICAMENTOS<br/>{colectivo.folio}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Información del paciente
        info_data = [
            ['INFORMACIÓN DEL PACIENTE', ''],
            ['Nombre:', colectivo.paciente.nombre_completo],
            ['CURP:', colectivo.paciente.curp or 'N/A'],
            ['Fecha de Nacimiento:', colectivo.paciente.fecha_nacimiento.strftime('%d/%m/%Y')],
            ['Número de Cama:', colectivo.numero_cama],
            ['Servicio:', colectivo.servicio],
            ['', ''],
            ['INFORMACIÓN DEL COLECTIVO', ''],
            ['Fecha de Solicitud:', colectivo.fecha_solicitud.strftime('%d/%m/%Y %H:%M')],
            ['Fecha de Surtido:', colectivo.fecha_completado.strftime('%d/%m/%Y %H:%M')],
            ['Enfermero(a):', colectivo.enfermero_solicitante.get_full_name() or colectivo.enfermero_solicitante.username],
            ['Farmacéutico(a):', colectivo.farmaceutico_asignado.get_full_name() or colectivo.farmaceutico_asignado.username if colectivo.farmaceutico_asignado else 'N/A'],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4.5*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#750000')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 7), (-1, 7), colors.HexColor('#750000')),
            ('TEXTCOLOR', (0, 7), (-1, 7), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 7), (-1, 7), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Tabla de medicamentos
        medicamentos_data = [['#', 'CLAVE', 'DESCRIPCIÓN', 'SOLICITADO', 'SURTIDO']]
        
        for idx, item in enumerate(colectivo.medicamentos.all(), 1):
            medicamentos_data.append([
                str(idx),
                item.medicamento.clave,
                item.medicamento.descripcion[:50],
                str(item.cantidad_solicitada),
                str(item.cantidad_surtida)
            ])
        
        medicamentos_table = Table(medicamentos_data, colWidths=[0.5*inch, 1*inch, 3*inch, 1*inch, 1*inch])
        medicamentos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#750000')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        elements.append(medicamentos_table)
        
        # Observaciones
        if colectivo.observaciones_enfermeria:
            elements.append(Spacer(1, 0.2*inch))
            obs_style = ParagraphStyle('Observaciones', parent=styles['Normal'], fontSize=9)
            elements.append(Paragraph(f"<b>Observaciones de Enfermería:</b> {colectivo.observaciones_enfermeria}", obs_style))
        
        # Construir PDF
        doc.build(elements)
        
        # Obtener PDF
        pdf = buffer.getvalue()
        buffer.close()
        
        # Respuesta HTTP
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Colectivo_{colectivo.folio}.pdf"'
        response.write(pdf)
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error al generar PDF: {str(e)}')
        return redirect('detalle_colectivo_farmacia', colectivo_id=colectivo.id)
    
@login_required
@permission_required('enfermeria.change_colectivo', raise_exception=True)
def editar_reenviar_colectivo(request, colectivo_id):
    """Vista para editar y reenviar un colectivo que fue respondido por farmacia"""
    colectivo = get_object_or_404(Colectivo, id=colectivo_id)
    
    # Verificar que el usuario sea el solicitante
    if colectivo.enfermero_solicitante != request.user:
        messages.error(request, "No tienes permiso para editar este colectivo.")
        return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo_id)
    
    # Verificar que el colectivo esté en estado RESPONDIDO
    if colectivo.estado != 'RESPONDIDO':
        messages.error(request, "Solo puedes editar colectivos en estado RESPONDIDO.")
        return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo_id)
    
    if request.method == 'POST':
        comentario_reenvio = request.POST.get('comentario_reenvio', '').strip()
        
        if not comentario_reenvio:
            messages.error(request, "Debes agregar un comentario explicando los cambios.")
            return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo_id)
        
        try:
            with transaction.atomic():
                # Actualizar cantidades de los medicamentos (CAMBIO AQUÍ)
                items_actualizados = []
                for item in colectivo.medicamentos.all():  # ← Cambio de .items a .medicamentos
                    nueva_cantidad = request.POST.get(f'cantidad_{item.id}')
                    if nueva_cantidad:
                        nueva_cantidad = int(nueva_cantidad)
                        if nueva_cantidad != item.cantidad_solicitada:
                            items_actualizados.append({
                                'medicamento': item.medicamento.descripcion,
                                'cantidad_anterior': item.cantidad_solicitada,
                                'cantidad_nueva': nueva_cantidad
                            })
                        item.cantidad_solicitada = nueva_cantidad
                        item.save()
                
                # Actualizar observaciones agregando el comentario de reenvío
                observaciones_actualizadas = f"{colectivo.observaciones_enfermeria}\n\n--- REENVÍO ---\n{comentario_reenvio}"
                colectivo.observaciones_enfermeria = observaciones_actualizadas
                
                # Cambiar estado a PENDIENTE
                colectivo.estado = 'PENDIENTE'
                colectivo.fecha_respuesta_farmacia = None
                colectivo.respuesta_farmacia = ""
                colectivo.save()
                
                messages.success(request, f'Colectivo {colectivo.folio} reenviado exitosamente a farmacia.')
                
            return redirect('lista_colectivos_enfermeria')
            
        except Exception as e:
            messages.error(request, f'Error al reenviar el colectivo: {str(e)}')
            return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo_id)
    
    return redirect('detalle_colectivo_enfermeria', colectivo_id=colectivo_id)