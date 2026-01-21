from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .models import Bitacora
from .middleware import get_current_user, get_current_ip
from farmacia.models import Medicamento, UsuarioPersonalizado, Lote
from enfermeria.models import Colectivo, ColectivoMedicamento


# Lista de modelos a vigilar
MODELOS_AUDITADOS = [Medicamento, Colectivo, ColectivoMedicamento, UsuarioPersonalizado, Lote]

@receiver(pre_save)
def auditar_pre_save(sender, instance, **kwargs):
    """Captura el estado ANTES del cambio"""
    if sender in MODELOS_AUDITADOS and instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            # Guardamos temporalmente el estado anterior en la instancia
            instance._old_state = model_to_dict(old_instance)
        except sender.DoesNotExist:
            instance._old_state = {}

@receiver(post_save)
def auditar_post_save(sender, instance, created, **kwargs):
    """Registra el cambio después de guardar"""
    if sender not in MODELOS_AUDITADOS:
        return

    user = get_current_user()
    # Si es una tarea automática (sistema) o no hay usuario, definimos uno genérico
    if not user or not user.is_authenticated:
        # Opcional: Si quieres ignorar cambios hechos por el sistema, pon return
        nombre_usuario = 'SISTEMA/AUTO'
        usuario_obj = None
    else:
        nombre_usuario = user.username
        usuario_obj = user

    ip = get_current_ip()
    
    accion = 'CREAR' if created else 'EDITAR'
    cambios = {}

    if not created and hasattr(instance, '_old_state'):
        new_state = model_to_dict(instance)
        # Comparar campo por campo
        for key, value in new_state.items():
            # Ignorar campos que no nos interesan o binarios
            if key in ['password', 'last_login', 'imagen']: 
                continue
                
            old_value = instance._old_state.get(key)
            if old_value != value:
                # Convertir valores especiales (fechas, foreign keys) a string
                cambios[key] = {
                    'antes': str(old_value),
                    'despues': str(value)
                }
    elif created:
        cambios = {'mensaje': 'Registro nuevo creado'}

    # Solo guardamos si hubo creación o cambios reales
    if created or cambios:
        Bitacora.objects.create(
            usuario=usuario_obj,
            usuario_texto=nombre_usuario,
            accion=accion,
            modelo_afectado=sender.__name__,
            id_objeto=str(instance.pk),
            detalles=cambios,
            ip_address=ip
        )

@receiver(post_delete)
def auditar_delete(sender, instance, **kwargs):
    if sender not in MODELOS_AUDITADOS:
        return

    user = get_current_user()
    nombre_usuario = user.username if (user and user.is_authenticated) else 'SISTEMA'
    ip = get_current_ip()

    Bitacora.objects.create(
        usuario=user if (user and user.is_authenticated) else None,
        usuario_texto=nombre_usuario,
        accion='ELIMINAR',
        modelo_afectado=sender.__name__,
        id_objeto=str(instance.pk),
        detalles={'mensaje': f'Registro eliminado: {str(instance)}'},
        ip_address=ip
    )