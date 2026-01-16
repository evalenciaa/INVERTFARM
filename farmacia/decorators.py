"""
Decoradores personalizados para control de acceso basado en grupos.
"""
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps


def group_required(*group_names):
    """
    Decorador que verifica si el usuario pertenece a alguno de los grupos especificados.
    Los superusuarios siempre tienen acceso.
    
    Uso:
        @group_required('Administrador', 'Farmacéutico')
        def mi_vista(request):
            ...
    
    Args:
        *group_names: Nombres de los grupos permitidos
    
    Raises:
        PermissionDenied: Si el usuario no pertenece a ningún grupo especificado
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Superusuarios siempre pasan
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Verificar si el usuario está en alguno de los grupos
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            
            # Si no tiene permiso, lanzar 403
            raise PermissionDenied(
                f"Se requiere pertenecer a alguno de estos grupos: {', '.join(group_names)}"
            )
        
        return _wrapped_view
    return decorator


def permission_required_or_superuser(perm):
    """
    Decorador que verifica permisos pero siempre permite superusuarios.
    Similar a @permission_required pero más flexible.
    
    Uso:
        @permission_required_or_superuser('farmacia.add_entrada')
        def mi_vista(request):
            ...
    
    Args:
        perm: Permiso requerido en formato 'app.codename'
    """
    def check_permission(user):
        if user.is_superuser:
            return True
        return user.has_perm(perm)
    
    return user_passes_test(
        check_permission,
        login_url='login'
    )
