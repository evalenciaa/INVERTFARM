from django.contrib.auth.models import Group, Permission
from django.db.models.signals import m2m_changed, post_save, post_delete, pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .services import registrar_evento
from farmacia.models import (
    DetalleEntrada, DetalleSalidaTransferencia, Entrada, Lote, Medicamento,
    Receta, RecetaMedicamento, Salida, SalidaTransferencia, UsuarioPersonalizado,
    CatalogoAntibioticosWHO,
)
from enfermeria.models import Colectivo, ColectivoMedicamento


# Lista de modelos a vigilar
MODELOS_AUDITADOS = (
    Medicamento, Lote, Entrada, DetalleEntrada, Salida, Receta,
    RecetaMedicamento, SalidaTransferencia, DetalleSalidaTransferencia,
    Colectivo, ColectivoMedicamento, UsuarioPersonalizado, CatalogoAntibioticosWHO,
)
CAMPOS_OMITIDOS = {'password', 'last_login', 'imagen', 'groups', 'user_permissions'}

@receiver(pre_save)
def auditar_pre_save(sender, instance, **kwargs):
    """Captura el estado ANTES del cambio"""
    if sender in MODELOS_AUDITADOS and instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_state = model_to_dict(old_instance)
        except sender.DoesNotExist:
            instance._old_state = {}

@receiver(post_save)
def auditar_post_save(sender, instance, created, **kwargs):
    """Registra el cambio después de guardar"""
    if sender not in MODELOS_AUDITADOS:
        return

    accion = 'CREAR' if created else 'EDITAR'
    cambios = {}

    if not created and hasattr(instance, '_old_state'):
        new_state = model_to_dict(instance)
        # Comparar campo por campo
        for key, value in new_state.items():
            if key in CAMPOS_OMITIDOS:
                continue
            old_value = instance._old_state.get(key)
            if old_value != value:
                cambios[key] = {
                    'antes': old_value,
                    'despues': value,
                }
    elif created:
        cambios = {'evento': 'registro_creado'}

    # Solo guardamos si hubo creación o cambios reales
    if created or cambios:
        registrar_evento(accion, sender.__name__, objeto=instance, detalles=cambios)

@receiver(post_delete)
def auditar_delete(sender, instance, **kwargs):
    if sender not in MODELOS_AUDITADOS:
        return

    objeto_pk = instance.pk
    registrar_evento(
        'ELIMINAR',
        sender.__name__,
        objeto=objeto_pk,
        detalles={'estado_final': model_to_dict(instance)},
    )


def _registrar_cambio_m2m(instance, campo, accion, valores):
    registrar_evento(
        'EDITAR',
        'UsuarioPersonalizado',
        objeto=instance,
        detalles={
            'campo': campo,
            'operacion': accion,
            'valores': valores,
        },
    )


@receiver(m2m_changed, sender=UsuarioPersonalizado.groups.through)
def auditar_grupos_usuario(sender, instance, action, pk_set, **kwargs):
    """Registra las asignaciones de perfil/grupo realizadas desde Django Admin."""
    if action == 'pre_clear':
        instance._grupos_auditoria = list(instance.groups.values_list('name', flat=True))
        return
    if action == 'post_clear':
        _registrar_cambio_m2m(instance, 'grupos', action, getattr(instance, '_grupos_auditoria', []))
        return
    if action in {'post_add', 'post_remove'}:
        nombres = list(Group.objects.filter(pk__in=pk_set or set()).values_list('name', flat=True))
        _registrar_cambio_m2m(instance, 'grupos', action, nombres)


@receiver(m2m_changed, sender=UsuarioPersonalizado.user_permissions.through)
def auditar_permisos_directos_usuario(sender, instance, action, pk_set, **kwargs):
    """Deja evidencia de excepciones de permisos directos, sin exponer secretos."""
    if action == 'pre_clear':
        instance._permisos_auditoria = list(instance.user_permissions.values_list('codename', flat=True))
        return
    if action == 'post_clear':
        _registrar_cambio_m2m(instance, 'permisos_directos', action, getattr(instance, '_permisos_auditoria', []))
        return
    if action in {'post_add', 'post_remove'}:
        codenames = list(Permission.objects.filter(pk__in=pk_set or set()).values_list('codename', flat=True))
        _registrar_cambio_m2m(instance, 'permisos_directos', action, codenames)
