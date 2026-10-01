from django.db import migrations, models


PERFILES = {
    'JEFE_FARMACIA': {
        'grupo': 'Jefe de Farmacia',
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
        'permisos': {
            'enfermeria.view_colectivo', 'enfermeria.add_colectivo',
            'enfermeria.change_colectivo', 'enfermeria.delete_colectivo',
            'enfermeria.create_colectivo', 'farmacia.view_medicamento',
            'farmacia.view_lote',
        },
    },
    'FARMACIA': {
        'grupo': 'Farmacéutico',
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
        'permisos': {
            'enfermeria.view_colectivo', 'enfermeria.add_colectivo',
            'enfermeria.create_colectivo', 'farmacia.view_medicamento',
            'farmacia.view_lote',
        },
    },
}


def normalizar_perfiles(apps, schema_editor):
    User = apps.get_model('farmacia', 'UsuarioPersonalizado')
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    permisos = {
        f'{permiso.content_type.app_label}.{permiso.codename}': permiso
        for permiso in Permission.objects.filter(
            content_type__app_label__in=['farmacia', 'enfermeria']
        ).select_related('content_type')
    }

    grupos = {}
    for rol, configuracion in PERFILES.items():
        grupo, _ = Group.objects.get_or_create(name=configuracion['grupo'])
        grupo.permissions.set([
            permisos[codigo]
            for codigo in configuracion['permisos']
            if codigo in permisos
        ])
        grupos[rol] = grupo

    for usuario in User.objects.prefetch_related('groups').all():
        if usuario.is_superuser:
            continue

        nombres_grupos = set(usuario.groups.values_list('name', flat=True))
        if 'Jefe de Farmacia' in nombres_grupos or 'Jefe farmacia' in nombres_grupos:
            rol = 'JEFE_FARMACIA'
        elif 'Jefe de Enfermería' in nombres_grupos or 'Jefe enfermeros' in nombres_grupos:
            rol = 'JEFE_ENFERMERIA'
        elif usuario.rol in ('FARMACIA', 'ENFERMERIA'):
            rol = usuario.rol
        else:
            rol = 'PENDIENTE'

        usuario.rol = rol
        usuario.groups.clear()
        usuario.user_permissions.clear()
        if rol in grupos:
            usuario.groups.add(grupos[rol])
        usuario.save(update_fields=['rol'])


class Migration(migrations.Migration):

    dependencies = [
        ('farmacia', '0019_lote_existencia_no_negativa'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuariopersonalizado',
            name='requiere_cambio_contrasena',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='usuariopersonalizado',
            name='tokens_validos_desde',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='usuariopersonalizado',
            name='rol',
            field=models.CharField(
                choices=[
                    ('PENDIENTE', 'Sin perfil operativo'),
                    ('JEFE_FARMACIA', 'Jefe de Farmacia'),
                    ('JEFE_ENFERMERIA', 'Jefe de Enfermería'),
                    ('FARMACIA', 'Farmacéutico'),
                    ('ENFERMERIA', 'Enfermero/a'),
                    ('MEDICO', 'Médico/a'),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(normalizar_perfiles, migrations.RunPython.noop),
    ]
