# farmacia/middleware.py
import hashlib
import time

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils.cache import add_never_cache_headers


class PasswordChangeRequiredMiddleware:
    """Impide que una contraseña temporal acceda a módulos operativos."""
    rutas_permitidas = {'/login/', '/logout/', '/cuenta/cambiar-contrasena/'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        if (
            usuario.is_authenticated
            and not usuario.is_superuser
            and usuario.requiere_cambio_contrasena
            and request.path not in self.rutas_permitidas
            and not request.path.startswith('/static/')
            and not request.path.startswith('/media/')
        ):
            return redirect('cambiar_contrasena_obligatoria')
        return self.get_response(request)


class RestoreMaintenanceMiddleware:
    """Pausa la operación clínica únicamente mientras se aplica una restauración."""
    rutas_permitidas = {'/login/', '/logout/'}

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _restauracion_activa():
        clave = 'inventfarm:restauracion_activa'
        activa = cache.get(clave)
        if activa is not None:
            return activa
        try:
            from .models import TrabajoRespaldo
            activa = TrabajoRespaldo.objects.filter(
                tipo=TrabajoRespaldo.Tipo.RESTAURAR,
                estado=TrabajoRespaldo.Estado.EJECUTANDO,
            ).exists()
        except Exception:
            # Permite aplicar migraciones sin que el middleware dependa de que
            # la tabla nueva exista todavía.
            activa = False
        cache.set(clave, activa, timeout=2)
        return activa

    def __call__(self, request):
        if not self._restauracion_activa():
            return self.get_response(request)
        if (
            request.path in self.rutas_permitidas
            or request.path.startswith('/static/')
            or request.path.startswith('/media/')
            or request.path.startswith('/backups/')
        ):
            return self.get_response(request)
        mensaje = 'El sistema está en mantenimiento por una restauración de respaldo. Intente de nuevo en unos minutos.'
        if request.path.startswith('/api/') or request.headers.get('Accept', '').startswith('application/json'):
            return JsonResponse({'error': mensaje}, status=503)
        return HttpResponse(mensaje, status=503)


class RateLimitMiddleware:
    """Limita operaciones costosas y repetitivas sin depender del navegador."""
    POLITICAS = (
        ('auth', lambda request: request.path in {'/login/', '/api/login/'}, 10, 60),
        ('upload', lambda request: request.method == 'POST' and request.path in {
            '/api/carga-masiva/procesar/', '/backups/subir/',
        }, 5, 3600),
        ('reportes', lambda request: request.path.startswith('/reportes/') or '/exportar' in request.path, 30, 60),
        ('busquedas', lambda request: request.method == 'GET' and (
            '/buscar' in request.path or '/get_paciente' in request.path
        ), 120, 60),
    )

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _identidad(request):
        if request.user.is_authenticated:
            return f'user:{request.user.pk}'
        return f'ip:{request.META.get("REMOTE_ADDR", "desconocida")}'

    def __call__(self, request):
        for nombre, coincide, limite, ventana in self.POLITICAS:
            if not coincide(request):
                continue

            marca = int(time.time() // ventana)
            identidad = self._identidad(request).encode('utf-8')
            huella = hashlib.sha256(identidad).hexdigest()
            clave = f'inventfarm:limite:{nombre}:{marca}:{huella}'
            if cache.add(clave, 1, timeout=ventana):
                break
            try:
                usos = cache.incr(clave)
            except ValueError:
                cache.set(clave, 1, timeout=ventana)
                usos = 1
            if usos > limite:
                respuesta = JsonResponse(
                    {'error': 'Demasiadas solicitudes. Intenta de nuevo más tarde.'},
                    status=429,
                )
                respuesta['Retry-After'] = str(ventana)
                return respuesta
            break
        return self.get_response(request)


class RequestLimitsMiddleware:
    """Corta solicitudes anormalmente grandes antes de analizarlas."""
    MAX_QUERY_STRING = 2048
    MAX_JSON_BODY = 1024 * 1024

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if len(request.META.get('QUERY_STRING', '')) > self.MAX_QUERY_STRING:
            return JsonResponse({'error': 'La consulta excede el tamaño permitido.'}, status=414)

        content_type = request.META.get('CONTENT_TYPE', '').split(';', 1)[0].lower()
        content_length = request.META.get('CONTENT_LENGTH', '0')
        try:
            excede_json = content_type == 'application/json' and int(content_length or 0) > self.MAX_JSON_BODY
        except ValueError:
            excede_json = True
        if excede_json:
            return JsonResponse({'error': 'El cuerpo JSON excede el tamaño permitido.'}, status=413)
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """Reduce el impacto de inyecciones de contenido en el navegador."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; base-uri 'self'; form-action 'self'; "
            "frame-ancestors 'none'; object-src 'none'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com "
            "https://cdn.jsdelivr.net https://cdn.sheetjs.com https://code.jquery.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://cdnjs.cloudflare.com; img-src 'self' data: blob:; "
            "connect-src 'self';",
        )
        response.setdefault('Referrer-Policy', 'same-origin')
        response.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        return response

class NoCacheMiddleware:
    """
    Middleware que previene el cacheo de páginas en el navegador.
    Útil para evitar que usuarios vean páginas protegidas después del logout
    usando el botón 'Atrás' del navegador.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Solo aplicar a páginas que requieren autenticación
        if request.user.is_authenticated or request.path in ['/login/', '/logout/']:
            add_never_cache_headers(response)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
