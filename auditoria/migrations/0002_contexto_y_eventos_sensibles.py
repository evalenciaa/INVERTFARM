from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bitacora',
            name='correlacion_id',
            field=models.CharField(blank=True, db_index=True, max_length=32),
        ),
        migrations.AddField(
            model_name='bitacora',
            name='metodo',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='bitacora',
            name='ruta',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='bitacora',
            name='user_agent',
            field=models.CharField(blank=True, max_length=512),
        ),
        migrations.AlterField(
            model_name='bitacora',
            name='accion',
            field=models.CharField(
                choices=[
                    ('CREAR', 'Creación'), ('EDITAR', 'Edición'),
                    ('ELIMINAR', 'Eliminación'), ('ACCESO', 'Login/Acceso'),
                    ('SALIDA', 'Logout'), ('FALLO_ACCESO', 'Acceso fallido'),
                    ('RESPALDO', 'Operación de respaldo'),
                ],
                max_length=20,
            ),
        ),
    ]
