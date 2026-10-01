"""Perfiles operativos canónicos y su sincronización con permisos Django."""
from django.contrib.auth.models import Group, Permission


PERFILES = {
    'JEFE_FARMACIA': {
        'grupo': 'Jefe de Farmacia',
        'descripcion': (
            'Gestiona medicamentos y lotes; revisa, responde y completa colectivos. '
            'No administra usuarios, respaldos ni Django Admin.'
        ),
        'permisos': {
            'farmacia.view_medicamento', 'farmacia.add_medicamento',
            'farmacia.change_medicamento', 'farmacia.delete_medicamento',
            'farmacia.view_lote', 'farmacia.add_lote', 'farmacia.change_lote',
            'farmacia.delete_lote', 'enfermeria.view_colectivo',
            'enfermeria.respond_colectivo', 'enfermeria.complete_colectivo',
        },
    },
    'JEFE_ENFERMERIA': {
        'grupo': 'Jefe de Enfermería',
        'descripcion': (
            'Administra colectivos de enfermería y consulta inventario general y de '
            'antibióticos. No modifica operaciones de farmacia.'
        ),
        'permisos': {
            'enfermeria.view_colectivo', 'enfermeria.add_colectivo',
            'enfermeria.change_colectivo', 'enfermeria.delete_colectivo',
            'enfermeria.create_colectivo', 'farmacia.view_medicamento',
            'farmacia.view_lote',
        },
    },
    'FARMACIA': {
        'grupo': 'Farmacéutico',
        'descripcion': (
            'Registra entradas, salidas y medicamentos; atiende colectivos y genera '
            'reportes. No edita lotes, no elimina medicamentos ni hace cargas masivas.'
        ),
        'permisos': {
            'farmacia.view_medicamento', 'farmacia.add_medicamento',
            'farmacia.view_lote', 'farmacia.add_entrada', 'farmacia.view_entrada',
            'farmacia.create_salida', 'farmacia.view_receta',
            'farmacia.view_reportes', 'farmacia.export_reportes',
            'enfermeria.view_colectivo', 'enfermeria.respond_colectivo',
            'enfermeria.complete_colectivo',
        },
    },
    'ENFERMERIA': {
        'grupo': 'Enfermero/a',
        'descripcion': (
            'Consulta inventario general y de antibióticos; crea colectivos y descarga '
            'sus propios reportes. No cancela ni modifica colectivos.'
        ),
        'permisos': {
            'enfermeria.view_colectivo', 'enfermeria.add_colectivo',
            'enfermeria.create_colectivo', 'farmacia.view_medicamento',
            'farmacia.view_lote',
        },
    },
}


def sincronizar_perfil(usuario):
    """Hace que un usuario operativo tenga exactamente un grupo y permisos del perfil."""
    if usuario.is_superuser:
        return

    configuracion = PERFILES.get(usuario.rol)
    usuario.groups.clear()
    usuario.user_permissions.clear()

    if not configuracion:
        return

    grupo, _ = Group.objects.get_or_create(name=configuracion['grupo'])
    permisos = Permission.objects.filter(
        content_type__app_label__in=['farmacia', 'enfermeria'],
    )
    permisos = [
        permiso for permiso in permisos
        if f'{permiso.content_type.app_label}.{permiso.codename}' in configuracion['permisos']
    ]
    grupo.permissions.set(permisos)
    usuario.groups.add(grupo)


def descripcion_perfil(rol):
    configuracion = PERFILES.get(rol)
    return configuracion['descripcion'] if configuracion else 'Sin perfil operativo asignado.'
