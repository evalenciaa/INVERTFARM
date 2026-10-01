"""Autenticación JWT con revocación por usuario."""
from datetime import datetime, timezone as datetime_timezone

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class InventFarmJWTAuthentication(JWTAuthentication):
    """Rechaza tokens emitidos antes de un alta o restablecimiento de contraseña."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        validos_desde = user.tokens_validos_desde
        issued_at = validated_token.get('iat')
        if validos_desde and (
            issued_at is None
            or datetime.fromtimestamp(issued_at, datetime_timezone.utc) < validos_desde.astimezone(datetime_timezone.utc)
        ):
            raise InvalidToken({'detail': 'El token fue revocado; vuelve a iniciar sesión.'})
        return user
