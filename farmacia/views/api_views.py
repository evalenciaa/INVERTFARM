"""Vistas REST de autenticación y consultas autorizadas."""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from axes.models import AccessAttempt
from axes.handlers.proxy import AxesProxyHandler

from farmacia.serializers import LoginSerializer
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_GET
from farmacia.models import Institucion
from auditoria.services import registrar_evento

logger = logging.getLogger(__name__)


class LoginAPIView(APIView):
    """Vista de login para API con protección anti-fuerza bruta"""

    def post(self, request):
        username = request.data.get('username', '').strip()

        # Verificar si está bloqueado
        if username and AxesProxyHandler.is_locked(request, credentials={'username': username}):
            registrar_evento(
                'FALLO_ACCESO', 'API', detalles={'motivo': 'cuenta_bloqueada'},
                usuario_texto=username,
            )
            intentos = AccessAttempt.objects.filter(username=username).first()
            fallos = intentos.failures_since_start if intentos else 5
            return Response({
                'error': 'Cuenta bloqueada por seguridad',
                'detail': f'Demasiados intentos fallidos ({fallos}). Intenta de nuevo en 1 hora.',
                'locked': True
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = LoginSerializer(
            data=request.data,
            context={'request': request._request},
        )

        if serializer.is_valid():
            user = serializer.validated_data
            if not user.is_active:
                registrar_evento(
                    'FALLO_ACCESO', 'API', detalles={'motivo': 'cuenta_inactiva'},
                    usuario=user,
                )
                return Response({
                    'error': 'Cuenta inactiva',
                    'detail': 'Tu cuenta ha sido desactivada. Contacta al administrador.'
                }, status=status.HTTP_403_FORBIDDEN)

            if user.requiere_cambio_contrasena and not user.is_superuser:
                return Response({
                    'error': 'Cambio de contraseña requerido',
                    'detail': 'Inicia sesión en la aplicación web para establecer tu contraseña personal.',
                    'password_change_required': True,
                }, status=status.HTTP_403_FORBIDDEN)

            refresh = RefreshToken.for_user(user)
            registrar_evento(
                'ACCESO', 'API', detalles={'evento': 'inicio_sesion_exitoso'}, usuario=user,
            )
            logger.info(f"API Login exitoso: usuario='{user.username}'")
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'username': user.username,
                    'rol': user.rol,
                    'nombre_completo': f"{user.first_name} {user.last_name}".strip()
                }
            })

        logger.warning(f"API Login fallido para: '{username}'")
        registrar_evento(
            'FALLO_ACCESO', 'API', detalles={'motivo': 'credenciales_invalidas'},
            usuario_texto=username or 'ANONIMO',
        )
        if username:
            intentos = AccessAttempt.objects.filter(username=username).first()
            if intentos:
                fallos_actuales = intentos.failures_since_start + 1
                restantes = 5 - fallos_actuales
                return Response({
                    'error': 'Credenciales incorrectas',
                    'detail': f'Usuario o contraseña incorrectos. Intentos restantes: {restantes}',
                    'attempts_remaining': max(0, restantes)
                }, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

@login_required
@require_GET
@permission_required('farmacia.create_transferencia', raise_exception=True)
def buscar_instituciones_autocomplete(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    instituciones = Institucion.objects.filter(
        nombre__icontains=query, activo=True
    ).order_by('nombre')[:10]
    results = [
        {'id': inst.id, 'nombre': inst.nombre, 'tipo': inst.get_tipo_display(), 'codigo': inst.codigo}
        for inst in instituciones
    ]
    return JsonResponse({'results': results})
