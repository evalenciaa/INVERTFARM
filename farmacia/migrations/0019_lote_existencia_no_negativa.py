from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('farmacia', '0018_rename_fuente_ddd_catalogoantibioticoswho_fuente_valor_atc'),
    ]

    operations = [
        migrations.CreateModel(
            name='FolioConsecutivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(max_length=10)),
                ('fecha', models.DateField()),
                ('ultimo_numero', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.AlterModelOptions(
            name='entrada',
            options={
                'ordering': ['-fecha'],
                'permissions': [('register_entrada', 'Puede registrar entradas')],
                'verbose_name': 'Entrada de Medicamentos',
                'verbose_name_plural': 'Entradas de Medicamentos',
            },
        ),
        migrations.AlterModelOptions(
            name='lote',
            options={
                'permissions': [('manage_lotes', 'Puede administrar lotes')],
            },
        ),
        migrations.RemoveConstraint(
            model_name='entrada',
            name='folio_por_institucion',
        ),
        migrations.AlterField(
            model_name='entrada',
            name='folio',
            field=models.CharField(blank=True, help_text='Dejar vacío para generación automática', max_length=50, null=True, unique=True, verbose_name='Folio'),
        ),
        migrations.AddConstraint(
            model_name='folioconsecutivo',
            constraint=models.UniqueConstraint(fields=('tipo', 'fecha'), name='folio_consecutivo_tipo_fecha_unico'),
        ),
        migrations.AddConstraint(
            model_name='lote',
            constraint=models.CheckConstraint(
                condition=models.Q(existencia__gte=0),
                name='lote_existencia_no_negativa',
            ),
        ),
    ]
