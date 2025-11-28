# farmacia/middleware.py
from django.utils.cache import add_never_cache_headers

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
