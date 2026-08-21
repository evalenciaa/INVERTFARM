"""
farmacia/views/admin_views.py
Vistas para gestión de usuarios y grupos para usuarios con rol Administrador.
"""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from farmacia.decorators import group_required

User = get_user_model()


@login_required
@group_required('Administrador')
def admin_usuarios(request):
    usuarios = User.objects.all().prefetch_related('groups').order_by('-date_joined')
    grupos = Group.objects.all().order_by('name')
    
    usuarios_activos = usuarios.filter(is_active=True, is_superuser=False).count()
    total_grupos = grupos.count()
    total_admins = usuarios.filter(Q(is_superuser=True) | Q(groups__name='Administrador')).distinct().count()
    
    context = {
        'usuarios': usuarios, 'grupos': grupos, 'usuarios_activos': usuarios_activos,
        'total_grupos': total_grupos, 'total_admins': total_admins,
    }
    return render(request, 'admin_usuarios.html', context)


@login_required
@group_required('Administrador')
def admin_usuario_detalle(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    grupos = Group.objects.all().order_by('name')
    
    if request.method == 'POST':
        try:
            usuario.username = request.POST.get('username', usuario.username)
            usuario.email = request.POST.get('email', usuario.email)
            usuario.first_name = request.POST.get('first_name', usuario.first_name)
            usuario.last_name = request.POST.get('last_name', usuario.last_name)
            usuario.is_active = request.POST.get('is_active') == 'on'
            
            new_password = request.POST.get('new_password')
            if new_password and new_password.strip():
                usuario.set_password(new_password)
            
            usuario.save()
            
            grupos_seleccionados = request.POST.getlist('groups')
            usuario.groups.clear()
            if grupos_seleccionados:
                for grupo_id in grupos_seleccionados:
                    try:
                        usuario.groups.add(Group.objects.get(pk=grupo_id))
                    except Group.DoesNotExist:
                        continue
            
            messages.success(request, f'Usuario {usuario.username} actualizado exitosamente')
            return redirect('admin_usuarios')
        except Exception as e:
            messages.error(request, f'Error al actualizar usuario: {str(e)}')
    
    permisos_usuario = usuario.get_all_permissions()
    context = {
        'usuario': usuario, 'grupos': grupos, 'permisos_usuario': sorted(permisos_usuario),
    }
    return render(request, 'admin_usuario_detalle.html', context)


@login_required
@group_required('Administrador')
def admin_crear_usuario(request):
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email', '')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            password = request.POST.get('password')
            password2 = request.POST.get('password2')
            
            if not username or not password:
                messages.error(request, 'Nombre de usuario y contraseña son obligatorios')
                return redirect('admin_usuarios')
            if password != password2:
                messages.error(request, 'Las contraseñas no coinciden')
                return redirect('admin_usuarios')
            if User.objects.filter(username=username).exists():
                messages.error(request, f'El usuario {username} ya existe')
                return redirect('admin_usuarios')
            
            usuario = User.objects.create_user(
                username=username, email=email, password=password,
                first_name=first_name, last_name=last_name
            )
            
            grupos_seleccionados = request.POST.getlist('groups')
            for grupo_id in grupos_seleccionados:
                usuario.groups.add(Group.objects.get(pk=grupo_id))
            
            messages.success(request, f'Usuario {username} creado exitosamente')
            return redirect('admin_usuarios')
        except Exception as e:
            messages.error(request, f'Error al crear usuario: {str(e)}')
            return redirect('admin_usuarios')
    return redirect('admin_usuarios')


@login_required
@group_required('Administrador')
@require_http_methods(['POST'])
def admin_eliminar_usuario(request, user_id):
    try:
        usuario = get_object_or_404(User, pk=user_id)
        if usuario.is_superuser:
            return JsonResponse({'success': False, 'error': 'No se puede eliminar un superusuario'}, status=403)
        if usuario.id == request.user.id:
            return JsonResponse({'success': False, 'error': 'No puedes eliminar tu propio usuario'}, status=403)
        
        username = usuario.username
        usuario.delete()
        return JsonResponse({'success': True, 'message': f'Usuario {username} eliminado exitosamente'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@group_required('Administrador')
def admin_grupos(request):
    grupos = Group.objects.annotate(num_usuarios=Count('user')).prefetch_related('permissions').order_by('name')
    return render(request, 'admin_grupos.html', {'grupos': grupos})


@login_required
@group_required('Administrador')
def admin_grupo_detalle(request, grupo_id):
    grupo = get_object_or_404(Group, pk=grupo_id)
    todos_permisos = Permission.objects.filter(
        content_type__app_label__in=['farmacia', 'enfermeria', 'auth']
    ).select_related('content_type').order_by('content_type__app_label', 'codename')
    
    if request.method == 'POST':
        try:
            nuevo_nombre = request.POST.get('name', grupo.name)
            if nuevo_nombre != grupo.name:
                grupo.name = nuevo_nombre
                grupo.save()
            
            permisos_seleccionados = request.POST.getlist('permissions')
            grupo.permissions.clear()
            if permisos_seleccionados:
                for permiso_id in permisos_seleccionados:
                    try:
                        grupo.permissions.add(Permission.objects.get(pk=permiso_id))
                    except Permission.DoesNotExist:
                        continue
            
            messages.success(request, f'Grupo {grupo.name} actualizado exitosamente')
            return redirect('admin_grupos')
        except Exception as e:
            messages.error(request, f'Error al actualizar grupo: {str(e)}')
    
    usuarios_grupo = User.objects.filter(groups=grupo).order_by('username')
    permisos_grupo = grupo.permissions.values_list('id', flat=True)
    
    context = {
        'grupo': grupo, 'todos_permisos': todos_permisos,
        'permisos_grupo': list(permisos_grupo), 'usuarios_grupo': usuarios_grupo,
    }
    return render(request, 'admin_grupo_detalle.html', context)


@login_required
@group_required('Administrador')
def admin_crear_grupo(request):
    if request.method == 'POST':
        try:
            nombre = request.POST.get('name')
            if not nombre:
                messages.error(request, 'El nombre del grupo es obligatorio')
                return redirect('admin_grupos')
            if Group.objects.filter(name=nombre).exists():
                messages.error(request, f'El grupo {nombre} ya existe')
                return redirect('admin_grupos')
            
            grupo = Group.objects.create(name=nombre)
            permisos_seleccionados = request.POST.getlist('permissions')
            for permiso_id in permisos_seleccionados:
                grupo.permissions.add(Permission.objects.get(pk=permiso_id))
            
            messages.success(request, f'Grupo {nombre} creado exitosamente')
            return redirect('admin_grupos')
        except Exception as e:
            messages.error(request, f'Error al crear grupo: {str(e)}')
    return redirect('admin_grupos')


@login_required
@group_required('Administrador')
@require_http_methods(['POST'])
def admin_eliminar_grupo(request, grupo_id):
    try:
        grupo = get_object_or_404(Group, pk=grupo_id)
        nombre = grupo.name
        if grupo.user_set.exists():
            return JsonResponse({
                'success': False, 'error': f'El grupo {nombre} tiene usuarios asignados. Reasígnalos primero.'
            }, status=400)
        
        grupo.delete()
        return JsonResponse({'success': True, 'message': f'Grupo {nombre} eliminado exitosamente'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
