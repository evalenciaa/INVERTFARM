"""Funciones centralizadas para eventos de auditoría seguros y consistentes."""
from datetime import date, datetime
from decimal import Decimal

from .middleware import get_current_ip, get_current_request_context, get_current_user
from .models import Bitacora


CAMPOS_SENSIBLES = {
    'password', 'contrasena', 'token', 'refresh', 'access', 'authorization',
    'secret', 'credential', 'api_key', 'api-key',
}


def _valor_seguro(valor):
    if isinstance(valor, dict):
        return {
            str(clave)[:100]: (
                '[REDACTADO]'
                if any(campo in str(clave).lower() for campo in CAMPOS_SENSIBLES)
                else _valor_seguro(dato)
            )
            for clave, dato in valor.items()
        }
    if isinstance(valor, (list, tuple, set)):
        return [_valor_seguro(item) for item in list(valor)[:100]]
    if isinstance(valor, (datetime, date, Decimal)):
        return str(valor)
    if valor is None or isinstance(valor, (bool, int, float)):
        return valor
    return str(valor)[:1000]


def registrar_evento(accion, modelo_afectado, *, objeto=None, detalles=None, usuario=None, usuario_texto=None):
    """Crea un evento sin persistir secretos y con el contexto de la solicitud."""
    actor = usuario if usuario is not None else get_current_user()
    if not actor or not getattr(actor, 'is_authenticated', False):
        actor = None
    contexto = get_current_request_context()
    return Bitacora.objects.create(
        usuario=actor,
        usuario_texto=(usuario_texto or (actor.username if actor else 'SISTEMA/AUTO'))[:150],
        accion=accion,
        modelo_afectado=str(modelo_afectado)[:100],
        id_objeto=str(getattr(objeto, 'pk', objeto) or '')[:50] or None,
        detalles=_valor_seguro(detalles or {}),
        ip_address=get_current_ip(),
        correlacion_id=contexto.get('correlacion_id', ''),
        ruta=contexto.get('ruta', ''),
        metodo=contexto.get('metodo', ''),
        user_agent=contexto.get('user_agent', ''),
    )
