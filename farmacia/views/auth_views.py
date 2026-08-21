"""
farmacia/views/auth_views.py
Vistas de autenticación: inicio, login, logout, bienvenida (principal).
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.utils.http import url_has_allowed_host_and_scheme
from axes.models import AccessAttempt
from axes.handlers.proxy import AxesProxyHandler

logger = logging.getLogger(__name__)


def inicio(request):
    """Vista raíz que redirige al login o al principal según autenticación"""
    if request.user.is_authenticated:
        return redirect('principal')
    return redirect('login')


def vista_farmacia(request):
    return render(request, 'farmacia.html')


def vista_farmacia_g(request):
    """Vista para el inventario por lotes"""
    return render(request, 'farmacia_g.html', {
        'user': request.user
    })


@never_cache
@require_http_methods(['GET', 'POST'])
def login_view(request):
    """Vista de login con validación estricta y protección anti-fuerza bruta"""
    if request.user.is_authenticated:
        return redirect('principal')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Usuario y contraseña son requeridos')
            return render(request, 'inicio.html', {'username': username})

        # Verificar si el usuario está bloqueado por Axes
        if AxesProxyHandler.is_locked(request, credentials={'username': username}):
            intentos = AccessAttempt.objects.filter(username=username).first()
            if intentos:
                fallos = intentos.failures_since_start
                messages.error(
                    request,
                    f'❌ Cuenta bloqueada por seguridad después de {fallos} intentos fallidos. '
                    f'Intenta de nuevo en 1 hora o contacta al administrador.'
                )
            else:
                messages.error(
                    request,
                    'Demasiados intentos fallidos. Tu cuenta está bloqueada temporalmente. '
                    'Intenta de nuevo en 1 hora.'
                )
            logger.warning(f"Cuenta bloqueada: intento para '{username}' desde IP {request.META.get('REMOTE_ADDR')}")
            return render(request, 'inicio.html', {'username': username, 'bloqueado': True})

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                request.session.flush()
                login(request, user)
                request.session.save()
                logger.info(f"Login exitoso: usuario='{user.username}' rol='{user.rol}'")

                next_url = request.POST.get('next') or request.GET.get('next', '')
                if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    next_url = 'principal'
                return redirect(next_url)
            else:
                messages.error(request, 'Tu cuenta ha sido desactivada. Contacta al administrador.')
                logger.warning(f"Intento de acceso a cuenta inactiva: '{username}'")
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
            logger.warning(f"Login fallido para '{username}' desde IP {request.META.get('REMOTE_ADDR')}")

            intentos_restantes = None
            intentos = AccessAttempt.objects.filter(username=username).first()
            if intentos:
                fallos_actuales = intentos.failures_since_start + 1
                intentos_restantes = max(0, 5 - fallos_actuales)
                logger.warning(f"Intentos fallidos: {fallos_actuales}/5 para '{username}'")
                if intentos_restantes == 0:
                    messages.warning(request, '⚠️ Último intento. La próxima vez tu cuenta será bloqueada por 1 hora.')

            return render(request, 'inicio.html', {'username': username, 'intentos_restantes': intentos_restantes})

    return render(request, 'inicio.html')


@never_cache
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Cierra sesión y destruye completamente la sesión del usuario"""
    if request.user.is_authenticated:
        request.session.flush()
        logout(request)
        messages.success(request, 'Sesión cerrada correctamente')

    response = redirect('login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@never_cache
def bienvenida(request):
    from django.contrib.auth.decorators import login_required
    # Decorated dynamically, applied in __init__.py
    def tiene_acceso(user, grupos_requeridos):
        if user.is_superuser or user.rol == 'ADMIN':
            return True
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
    ]

    return render(request, 'principal.html', {
        'modulos': modulos,
        'last_login': request.user.last_login
    })
