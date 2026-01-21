import threading
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import Bitacora

# Almacenamiento local del hilo (Thread Local Storage)
_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

def get_current_ip():
    return getattr(_thread_locals, 'ip', None)

class AuditoriaMiddleware(MiddlewareMixin):
    """
    Middleware que intercepta cada petición para:
    1. Guardar el usuario e IP en memoria temporal (ThreadLocal)
    2. Que las señales (Signals) puedan acceder a estos datos.
    """
    def process_request(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        # Obtener IP real (considerando si usas Nginx en el futuro)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        _thread_locals.ip = ip

# ===== SIGNALS PARA LOGIN/LOGOUT =====
# Esto registra automáticamente cuando alguien entra o sale del sistema

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    
    Bitacora.objects.create(
        usuario=user,
        usuario_texto=user.username,
        accion='ACCESO',
        modelo_afectado='Sistema',
        detalles={'mensaje': 'Inicio de sesión exitoso'},
        ip_address=ip
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    # Nota: A veces user puede ser None si la sesión expiró
    if user:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        
        Bitacora.objects.create(
            usuario=user,
            usuario_texto=user.username,
            accion='SALIDA',
            modelo_afectado='Sistema',
            detalles={'mensaje': 'Cierre de sesión'},
            ip_address=ip
        )