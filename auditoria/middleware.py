import threading
import uuid
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
# Almacenamiento local del hilo (Thread Local Storage)
_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

def get_current_ip():
    return getattr(_thread_locals, 'ip', None)


def get_current_request_context():
    return getattr(_thread_locals, 'contexto', {})


def _obtener_ip(request):
    if getattr(settings, 'TRUST_X_FORWARDED_FOR', False):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

class AuditoriaMiddleware(MiddlewareMixin):
    """
    Middleware que intercepta cada petición para:
    1. Guardar el usuario e IP en memoria temporal (ThreadLocal)
    2. Que las señales (Signals) puedan acceder a estos datos.
    """
    def process_request(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        _thread_locals.ip = _obtener_ip(request)
        _thread_locals.contexto = {
            'correlacion_id': uuid.uuid4().hex,
            'ruta': request.path[:255],
            'metodo': request.method[:10],
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:512],
        }

    def process_response(self, request, response):
        # Evita atribuir tareas automáticas posteriores al último usuario del hilo.
        _thread_locals.user = None
        _thread_locals.ip = None
        _thread_locals.contexto = {}
        return response

    def process_exception(self, request, exception):
        _thread_locals.user = None
        _thread_locals.ip = None
        _thread_locals.contexto = {}

# ===== SIGNALS PARA LOGIN/LOGOUT =====
# Esto registra automáticamente cuando alguien entra o sale del sistema

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    from .services import registrar_evento
    registrar_evento('ACCESO', 'Sistema', detalles={'evento': 'inicio_sesion_exitoso'}, usuario=user)

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    # Nota: A veces user puede ser None si la sesión expiró
    if user:
        from .services import registrar_evento
        registrar_evento('SALIDA', 'Sistema', detalles={'evento': 'cierre_sesion'}, usuario=user)
