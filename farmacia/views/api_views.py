"""
farmacia/views/api_views.py
Vistas REST (DRF): RegisterAPIView, LoginAPIView.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from axes.models import AccessAttempt
from axes.handlers.proxy import AxesProxyHandler

from farmacia.serializers import UserSerializer, LoginSerializer
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from farmacia.models import Institucion

logger = logging.getLogger(__name__)


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
    """Vista de login para API con protección anti-fuerza bruta"""

    def post(self, request):
        username = request.data.get('username', '').strip()

        # Verificar si está bloqueado
        if username and AxesProxyHandler.is_locked(request, credentials={'username': username}):
            intentos = AccessAttempt.objects.filter(username=username).first()
            fallos = intentos.failures_since_start if intentos else 5
            return Response({
                'error': 'Cuenta bloqueada por seguridad',
                'detail': f'Demasiados intentos fallidos ({fallos}). Intenta de nuevo en 1 hora.',
                'locked': True
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data
            if not user.is_active:
                return Response({
                    'error': 'Cuenta inactiva',
                    'detail': 'Tu cuenta ha sido desactivada. Contacta al administrador.'
                }, status=status.HTTP_403_FORBIDDEN)

            refresh = RefreshToken.for_user(user)
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