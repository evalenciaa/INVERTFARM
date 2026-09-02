from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date, timedelta
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.conf import settings
from django.utils.timezone import now
from datetime import date
from django.utils import timezone
from django.db import transaction
import uuid
import html
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string


class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.nombre


class UsuarioPersonalizado(AbstractUser):
    ROLES = (
        ('ADMIN', 'Administrador'),
        ('FARMACIA', 'Farmacéutico'),
        ('ENFERMERIA', 'Enfermero/a'),
        ('MEDICO', 'Médico/a'),  # ✅ NUEVO
    )
    rol = models.CharField(max_length=20, choices=ROLES)
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, null=True, blank=True)
    telefono = models.CharField(max_length=15, blank=True)
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        # ✅ PERMISOS PERSONALIZADOS
        permissions = [
            ('view_inventory_readonly', 'Puede ver inventario (solo lectura)'),
            ('manage_pharmacy', 'Puede administrar farmacia completa'),
            ('manage_nursing', 'Puede administrar enfermería completa'),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"
    
    def check_password(self, raw_password):
        if self.is_superuser:
            return super().check_password(raw_password)
        return super().check_password(raw_password)
    
    def get_rol_display(self):
        """
        Retorna el rol del usuario de forma legible.
        Si es superusuario, retorna 'Administrador'.
        Si tiene grupos, retorna el primero.
        Si no tiene grupos, retorna 'Sin rol'.
        """
        if self.is_superuser:
            return 'Administrador'
        
        grupos = self.groups.all()
        if grupos:
            # Si tiene un solo grupo
            if grupos.count() == 1:
                return grupos.first().name
            # Si tiene múltiples grupos
            else:
                return ', '.join([g.name for g in grupos])
        
        return 'Sin rol asignado'
    
    def get_rol_icono(self):
        """
        Retorna el ícono FontAwesome según el rol.
        """
        if self.is_superuser:
            return 'fa-user-shield'
        
        grupos = self.groups.values_list('name', flat=True)
        
        if 'Jefe de Farmacia' in grupos:
            return 'fa-user-tie'
        elif 'Farmacéutico' in grupos or 'Jefe farmacia' in grupos:
            return 'fa-pills'
        elif 'Jefe de Enfermería' in grupos or 'Jefe enfermeros' in grupos:
            return 'fa-user-nurse'
        elif 'Enfermero/a' in grupos:
            return 'fa-user-nurse'
        elif 'Médico' in grupos:
            return 'fa-user-md'
        
        return 'fa-user'


class PerfilUsuario(models.Model):
    user = models.OneToOneField(UsuarioPersonalizado, on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.departamento}"
    

# ===== MODELO PARA PERMISOS PERSONALIZADOS =====
class PermisosPersonalizados(models.Model):
    """
    Modelo ficticio solo para definir permisos personalizados del sistema.
    No se crea tabla en la base de datos (managed=False).
    Los permisos se almacenan en la tabla auth_permission de Django.
    """
    
    class Meta:
        managed = False  # No crear tabla en BD
        default_permissions = ()  # No crear permisos automáticos (add, change, delete, view)
        verbose_name = 'Permiso Personalizado'
        verbose_name_plural = 'Permisos Personalizados'
        
        permissions = [
            # PERMISOS DE REPORTES
            ("view_reportes", "Puede ver reportes y estadísticas"),
            ("export_reportes", "Puede exportar reportes a Excel/PDF"),
            
            # PERMISOS DE CARGA MASIVA
            ("view_carga_masiva", "Puede acceder a carga masiva de Excel"),
            ("upload_carga_masiva", "Puede subir archivos de carga masiva"),
            
            # PERMISOS DE SALIDAS
            ("view_salidas", "Puede ver historial de salidas"),
            ("create_salida", "Puede registrar salidas de medicamentos"),
            
            # PERMISOS DE INVENTARIO (adicionales)
            ("view_inventario_completo", "Puede ver todo el inventario"),
            ("edit_inventario", "Puede editar el inventario"),
            
            # PERMISOS DE GESTIÓN
            ("manage_catalogos", "Puede gestionar catálogos (presentaciones, proveedores)"),
            ("manage_cpm", "Puede gestionar CPM de medicamentos"),
        ]


class Proveedor(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Proveedor")
    rfc = models.CharField(max_length=13, blank=True, null=True, verbose_name="RFC")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class Presentacion(models.Model):
    nombre = models.CharField(max_length=20, unique=True)  # 'CAJA', 'UNIDAD'
    unidades_por_caja = models.IntegerField(default=1, help_text="Solo aplica si es caja")
    activo = models.BooleanField(default=True)

    def __str__(self):
        n = (self.nombre or "").strip().upper()

        # Solo estas presentaciones usan unidades por caja (ajusta si aplica a más)
        if n in ("CAJA", "AMPOLLETA"):
            return f"{n} ({self.unidades_por_caja} unidades)"

        # Para POLVO, SOLUCION, etc. muestra el nombre tal cual
        return self.nombre


    def delete(self, *args, **kwargs):
        """Sobrescribimos delete para desactivar en lugar de borrar"""
        self.activo = False
        self.save()


class Medicamento(models.Model):
    id = models.BigAutoField(primary_key=True)
    clave = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(verbose_name="Descripción", blank=False)
    codigo_barras = models.CharField(max_length=40, null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario", default=0.00)

    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Proveedor"
    )
    presentacion = models.ForeignKey(
        Presentacion, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Presentación"
    )
    activo = models.BooleanField(default=True)
    es_antibiotico = models.BooleanField(default=False)

    via_administracion = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ('ORAL', 'Oral'),
            ('INTRAMUSCULAR', 'Intramuscular'),
            ('INTRAVENOSA', 'Intravenosa'),
        ]
    )

    codigo_atc = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True
    )

    categoria_aware = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        choices=[
            ('Access', 'Access'),
            ('Watch', 'Watch'),
            ('Reserve', 'Reserve'),
        ]
    )

    gramos_por_pieza = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True
    )

    valor_atc = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.clave} - {self.descripcion}"
    
    class Meta:
        verbose_name = 'Medicamento'
        verbose_name_plural = 'Medicamentos'
        permissions = [
            ('view_medicamento_readonly', 'Puede ver medicamentos (solo lectura)'),
        ]

    

class CPM(models.Model):
    medicamento = models.ForeignKey(Medicamento, on_delete=models.CASCADE)
    presentacion = models.ForeignKey(Presentacion, on_delete=models.CASCADE)
    valor = models.IntegerField(default=0)  # Consumo promedio mensual en unidades

    class Meta:
        unique_together = ('medicamento', 'presentacion')

    def __str__(self):
        return f"{self.medicamento.descripcion} - {self.presentacion}: {self.valor}"


# En models.py - Agregar este modelo
class CPMMedicamento(models.Model):
    medicamento = models.OneToOneField(
        Medicamento, 
        on_delete=models.CASCADE,
        related_name='cpm_medicamento'
    )
    valor = models.PositiveIntegerField(
        default=0, 
        verbose_name="Consumo Promedio Mensual (CPM)"
    )
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        UsuarioPersonalizado, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "CPM por Medicamento"
        verbose_name_plural = "CPMs por Medicamento"

    def __str__(self):
        return f"{self.medicamento.clave} - CPM: {self.valor}"


class Lote(models.Model):
    id = models.CharField(primary_key=True, max_length=15)
    medicamento = models.ForeignKey(Medicamento, on_delete=models.CASCADE)
    lote_codigo = models.CharField(max_length=50, null=True, blank=True)
    fecha_caducidad = models.DateField(null=False)
    existencia = models.IntegerField(default=0)
    alerta_stock_enviada = models.BooleanField(default=False)
    presentacion = models.ForeignKey(Presentacion, on_delete=models.CASCADE, null=True, blank=True)
    cpm = models.PositiveIntegerField(default=0, verbose_name="Consumo Promedio Mensual")
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)], verbose_name="Costo unitario (lote)")
    origen = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo de entrada")
    contrato = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número de contrato")
    fuente_financiamiento = models.CharField(max_length=100, null=True, blank=True,verbose_name="Fuente de Financiamiento")


    def __str__(self):
        return f"Lote {self.id} ({self.medicamento.descripcion})"
    
    def color_alerta(self):
        if not self.fecha_caducidad:  # Manejar caso cuando fecha_caducidad es None
            return 'sin-fecha'
        
        hoy = date.today()
        if self.fecha_caducidad <= hoy + timedelta(days=180):
            return 'rojo'
        elif self.fecha_caducidad <= hoy + timedelta(days=365):
            return 'amarillo'
        else:
            return 'verde'
    
    def alerta_existencia(self):
        return self.existencia < 10
    
    def clean(self):
        if self.existencia < 0:
            raise ValidationError("La existencia no puede ser negativa")
        if self.fecha_caducidad < date.today():
            raise ValidationError("La fecha de caducidad debe ser futura")
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['medicamento', 'lote_codigo'], name='unique_medicamento_lote')
        ]
        permissions = [
            ('manage_lotes', 'Puede administrar lotes'),
        ]
    
    @classmethod
    def actualizar_inventario(cls, medicamento_id, lote_codigo, cantidad, fecha_caducidad, presentacion_id, costo_unitario=None):
        with transaction.atomic():
            defaults = {
                'fecha_caducidad': fecha_caducidad,
                'existencia': cantidad,
                'presentacion_id': presentacion_id,
                'id': f"LOT-{uuid.uuid4().hex[:10].upper()}",
            }
            if costo_unitario is not None:
                defaults['costo_unitario'] = costo_unitario

            lote, created = cls.objects.get_or_create(
                lote_codigo=lote_codigo,
                medicamento_id=medicamento_id,
                defaults=defaults
            )

            if not created:
                lote.existencia += cantidad
                if costo_unitario is not None:
                    lote.costo_unitario = costo_unitario
                lote.save()

            return lote
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['medicamento', 'lote_codigo'],
                name='unique_medicamento_lote'
            )
        ]


class Paciente(models.Model):
    id = models.AutoField(primary_key=True)
    nombre_completo = models.CharField(max_length=200)
    curp = models.CharField(max_length=18, unique=True, blank=True, null=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.nombre_completo


class Receta(models.Model):
    ESTADO_CHOICES = [
        ('completa', 'Completa'),
        ('parcial', 'Parcial'),
        ('no_surtida', 'No Surtida'),
    ]

    ORIGEN_CHOICES = [
        ('urgencias', 'Urgencias'),
        ('labor', 'Labor'),
        ('expulsion', 'Expulsión'),
        ('tococirugia', 'Tococirugía'),
        ('hospitalizacion_pediatria', 'Hospitalización Pediatría'),
        ('hospitalizacion_adultos', 'Hospitalización Adultos'),
        ('consulta_externa', 'Consulta Externa'),
        ('quirofano', 'Quirófano'),
        ('sala_de_choque', 'Sala de Choque'),
        ('cuidados_intensivos', 'Cuidados Intensivos'),
        ('uci_neonatal', 'UCI Neonatal'),
        ('uci_adultos', 'UCI Adultos'),
        ('ucip', 'UCI Pediátrica'),
    ]

    id_folio = models.CharField(max_length=20, unique=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    fecha_emision = models.DateField()
    fecha_surtido = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    origen = models.CharField(max_length=50, choices=ORIGEN_CHOICES)
    surtido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="recetas_surtidas"
    )
    observaciones_faltantes = models.TextField(blank=True, null=True, verbose_name='Medicamentos No Surtidos', help_text='Registro de medicamentos que no pudieron ser surtidos y el motivo'
    )

    def __str__(self):
        return f"Receta {self.id_folio} - {self.paciente.nombre_completo}"
    
    class Meta:
        verbose_name = 'Receta'
        verbose_name_plural = 'Recetas'
        permissions = [
            ('process_receta', 'Puede procesar recetas'),
            ('view_receta_readonly', 'Puede ver recetas (solo lectura)'),
        ]
    

class RecetaMedicamento(models.Model):
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE)
    medicamento = models.ForeignKey(Medicamento, on_delete=models.CASCADE)
    lote = models.ForeignKey(
        Lote, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    cantidad_solicitada = models.IntegerField()
    cantidad_surtida = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    precio_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.medicamento.descripcion} - Receta {self.receta.id_folio}"
    
    
class MedicamentoNoSurtido(models.Model):
    """Registro de medicamentos que no pudieron ser surtidos"""
    receta = models.ForeignKey(
        Receta,
        on_delete=models.CASCADE,
        related_name='medicamentos_no_surtidos'
    )
    medicamento_descripcion = models.CharField(
        max_length=200,
        verbose_name='Descripción del Medicamento'
    )
    cantidad_solicitada = models.IntegerField(
        verbose_name='Cantidad Solicitada'
    )
    motivo = models.TextField(
        verbose_name='Motivo de No Surtido'
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Medicamento No Surtido'
        verbose_name_plural = 'Medicamentos No Surtidos'
        ordering = ['-fecha_registro']
    
    def __str__(self):
        return f"{self.medicamento_descripcion} - Receta {self.receta.id_folio}"


class Almacen(models.Model):
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Almacén")
    direccion = models.TextField(verbose_name="Dirección")
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def delete(self, *args, **kwargs):
        """Borrado lógico"""
        self.activo = False
        self.save()

class Institucion(models.Model):
    TIPOS_INSTITUCION = [
        ('HOSPITAL', 'Hospital'),
        ('CENTRO_SALUD', 'Centro de Salud'),
        ('FARMACIA', 'Farmacia'),
        ('LABORATORIO', 'Laboratorio'),
        ('OTRO', 'Otro'),
    ]
    
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    tipo = models.CharField(max_length=20, choices=TIPOS_INSTITUCION, verbose_name="Tipo")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Institución"
        verbose_name_plural = "Instituciones"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class SalidaTransferencia(models.Model):
    folio = models.CharField(max_length=20, unique=True)
    institucion_destino = models.ForeignKey(
        Institucion, on_delete=models.PROTECT,
        related_name='transferencias_recibidas',
        verbose_name="Institución Destino"
    )
    fecha = models.DateTimeField(auto_now_add=True)
    autorizado_por = models.ForeignKey(
        UsuarioPersonalizado, on_delete=models.SET_NULL,
        null=True, related_name='transferencias_autorizadas'
    )
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Salida por Transferencia"
        verbose_name_plural = "Salidas por Transferencia"
        ordering = ['-fecha']
        permissions = [
            ('create_transferencia', 'Puede registrar salidas por transferencia'),
            ('view_transferencia', 'Puede ver historial de transferencias'),
        ]

    def __str__(self):
        return f"{self.folio} → {self.institucion_destino.nombre}"


class DetalleSalidaTransferencia(models.Model):
    transferencia = models.ForeignKey(
        SalidaTransferencia, on_delete=models.CASCADE, related_name='detalles'
    )
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    @property
    def total(self):
        return self.cantidad * self.costo_unitario

    def __str__(self):
        return f"{self.lote.medicamento.descripcion} x{self.cantidad}"

class FuenteFinanciamiento(models.Model):
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fuente de Financiamiento"
        verbose_name_plural = "Fuentes de Financiamiento"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Entrada(models.Model):
    TIPO_ENTRADA = [
        ('ALMACEN', 'Entrada por Almacén'),
        ('TRANSFERENCIA', 'Entrada por Transferencia'),
    ]
    
    folio = models.CharField(
        max_length=50,
        verbose_name="Folio",
        blank=True,  # Permite folio vacío para autogeneración
        null=True,   # Necesario para MySQL con unique constraint
        help_text="Dejar vacío para generación automática"
    )
    fecha = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de Entrada"
    )
    tipo_entrada = models.CharField(
        max_length=20, 
        choices=TIPO_ENTRADA,
        verbose_name="Tipo de Entrada"
    )
    almacen = models.ForeignKey(
        Almacen, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True
    )
    institucion = models.ForeignKey(
        Institucion, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True
    )
    fuente_financiamiento = models.ForeignKey(
        FuenteFinanciamiento,
        on_delete=models.PROTECT,
        verbose_name="Fuente de Financiamiento"
    )
    contrato = models.CharField(
        max_length=50, 
        verbose_name="Número de Contrato", 
        blank=True, 
        null=True
    )
    proceso = models.CharField(
        max_length=100, 
        verbose_name="Proceso"
    )
    recibido_por = models.ForeignKey(
        UsuarioPersonalizado,
        on_delete=models.PROTECT,
        verbose_name="Recibido por"
    )
    observaciones = models.TextField(
        blank=True, 
        verbose_name="Observaciones"
    )
    creado_en = models.DateTimeField(
        auto_now_add=True
    )
    actualizado_en = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Entrada de Medicamentos'
        verbose_name_plural = 'Entradas de Medicamentos'
        ordering = ['-fecha']
        constraints = [
            models.UniqueConstraint(
                fields=['folio', 'institucion'], 
                name='folio_por_institucion',
                condition=models.Q(folio__isnull=False)
            ),
        ]
        permissions = [
            ('register_entrada', 'Puede registrar entradas'),
        ]

    class Meta:
        verbose_name = "Entrada de Medicamentos"
        verbose_name_plural = "Entradas de Medicamentos"
        ordering = ['-fecha']
        constraints = [
            models.UniqueConstraint(
                fields=['folio', 'institucion'],
                name='folio_por_institucion',
                condition=models.Q(folio__isnull=False)  # Solo aplicar a folios no nulos
            )
        ]

    def clean(self):
        """Validación personalizada para folios únicos por institución"""
        from django.core.exceptions import ValidationError
        
        if self.folio:  # Solo validar si el folio no está vacío
            qs = Entrada.objects.filter(
                folio=self.folio,
                institucion=self.institucion
            )
            if self.pk:  # Para actualizaciones
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({
                    'folio': 'Ya existe una entrada con este folio para la institución seleccionada'
                })

    def __str__(self):
        return f"{self.folio} - {self.get_tipo_entrada_display()}"

    def save(self, *args, **kwargs):
        """Autogenera folio solo si no se especificó uno"""
        if not self.folio:
            date_str = date.today().strftime('%Y%m%d')
            last_entry = Entrada.objects.filter(
                folio__startswith=f'ENT-{date_str}'
            ).order_by('-folio').first()
            
            last_num = int(last_entry.folio.split('-')[-1]) if last_entry else 0
            self.folio = f"ENT-{date_str}-{last_num + 1:04d}"
            
        super().save(*args, **kwargs)


class DetalleEntrada(models.Model):
    entrada = models.ForeignKey(
        Entrada, 
        on_delete=models.CASCADE, 
        related_name='detalles',
        verbose_name="Entrada"
    )
    medicamento = models.ForeignKey(
        Medicamento, 
        on_delete=models.PROTECT,
        verbose_name="Medicamento"
    )
    lote = models.CharField(max_length=50, verbose_name="Número de Lote")
    caducidad = models.DateField(verbose_name="Fecha de Caducidad")
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Precio Unitario"
    )
    presentacion = models.ForeignKey(
        Presentacion,
        on_delete=models.PROTECT,
        verbose_name="Presentación"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Detalle de Entrada"
        verbose_name_plural = "Detalles de Entrada"
        unique_together = ('entrada', 'medicamento', 'lote')

    def __str__(self):
        return f"{self.medicamento.clave} - Lote: {self.lote}"

    @property
    def total(self):
        return self.cantidad * self.precio_unitario
    

class Salida(models.Model):
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    fecha_hora = models.DateTimeField(auto_now_add=True)

    @property
    def dia_semana(self):
        return self.fecha_hora.strftime('%A')

    def __str__(self):
        return f"Salida {self.id} - Lote {self.lote.id}"
    
class MedicamentoNoDisponibleTransferencia(models.Model):
    transferencia = models.ForeignKey(
        SalidaTransferencia,
        on_delete=models.CASCADE,
        related_name='medicamentos_no_disponibles'
    )
    medicamento_descripcion = models.CharField(max_length=200)
    cantidad_solicitada = models.IntegerField()
    motivo = models.TextField()
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['medicamento_descripcion']

    def __str__(self):
        return f"{self.medicamento_descripcion} - {self.transferencia.folio}"
    
    
class CatalogoAntibioticosWHO(models.Model):
    codigo_atc = models.CharField(max_length=20, unique=True, db_index=True)

    categoria_aware = models.CharField(
        max_length=10,
        choices=[
            ('Access', 'Access'),
            ('Watch', 'Watch'),
            ('Reserve', 'Reserve')
        ],
    )

    valor_atc = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True
    )

    fuente_ddd = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        choices=[
            ('herramienta_calculo', 'Herramienta de cálculo'),
            ('manual', 'Captura manual')
        ],
    )

    class Meta:
        verbose_name = "Catálogo WHO AWaRe/ATC"
        verbose_name_plural = "Catálogo WHO AWaRe/ATC"

    def __str__(self):
        return f"{self.codigo_atc} ({self.categoria_aware})"
    

# Señales

@receiver(post_save, sender=DetalleEntrada)
def sumar_existencia(sender, instance, created, **kwargs):
    if not created:
        return

    lote_codigo = instance.lote
    cantidad = instance.cantidad

    # Ajustar cantidad si es caja
    if instance.presentacion and instance.presentacion.nombre.upper() == "CAJA":
        cantidad *= instance.presentacion.unidades_por_caja

    try:
        lote_obj = Lote.objects.get(
            lote_codigo=lote_codigo,
            medicamento=instance.medicamento
        )
        lote_obj.existencia += cantidad
        lote_obj.costo_unitario = instance.precio_unitario  # <-- guardar costo
        lote_obj.save()
    except Lote.DoesNotExist:
        Lote.objects.create(
            id=f"LOT-{uuid.uuid4().hex[:10].upper()}",
            medicamento=instance.medicamento,
            lote_codigo=lote_codigo,
            fecha_caducidad=instance.caducidad,
            existencia=cantidad,
            presentacion=instance.presentacion,
            costo_unitario=instance.precio_unitario,  # <-- guardar costo
        )


def enviar_alerta_stock(lote, cpm_del_medicamento):
    # Calcular información adicional útil
    porcentaje_stock = (lote.existencia / cpm_del_medicamento * 100) if cpm_del_medicamento > 0 else 0
    dias_restantes = (lote.existencia / (cpm_del_medicamento / 30)) if cpm_del_medicamento > 0 else 0
    
    # Determinar nivel de criticidad
    if lote.existencia <= (cpm_del_medicamento * 0.25):
        nivel = "CRÍTICO"
        color = "#dc3545"
    elif lote.existencia <= (cpm_del_medicamento * 0.5):
        nivel = "BAJO"
        color = "#ffc107"
    else:
        nivel = "NORMAL"
        color = "#28a745"
    
    # ← ESCAPAR TODOS LOS VALORES DINÁMICOS
    descripcion_safe = html.escape(lote.medicamento.descripcion)
    clave_safe = html.escape(lote.medicamento.clave)
    lote_codigo_safe = html.escape(lote.lote_codigo)
    presentacion_safe = html.escape(lote.presentacion.nombre if lote.presentacion else 'N/A')
    
    asunto = f"⚠️ Stock {nivel}: {lote.medicamento.descripcion}"  # El asunto está bien sin escapar
    
    mensaje_texto = f"""
    ALERTA DE STOCK - {nivel}
    
    Fecha: {now().strftime('%d/%m/%Y %H:%M')}
    
    INFORMACIÓN DEL MEDICAMENTO:
    - Clave: {lote.medicamento.clave}
    - Descripción: {lote.medicamento.descripcion}
    - Presentación: {lote.presentacion.nombre if lote.presentacion else 'N/A'}
    
    INFORMACIÓN DEL LOTE:
    - Código de Lote: {lote.lote_codigo}
    - Existencia Actual: {lote.existencia} unidades
    - Fecha de Caducidad: {lote.fecha_caducidad.strftime('%d/%m/%Y')}
    
    ANÁLISIS DE CONSUMO:
    - CPM (Consumo Promedio Mensual): {cpm_del_medicamento} unidades
    - Porcentaje de Stock: {porcentaje_stock:.1f}%
    - Días de Stock Restantes: ~{dias_restantes:.0f} días
    
    ACCIÓN REQUERIDA: Revisar inventario y solicitar reabastecimiento
    
    ---
    Sistema de Gestión de Farmacia - Hospital
    """
    
    # ← USAR LAS VERSIONES ESCAPADAS EN EL HTML
    mensaje_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, {color} 0%, {color}dd 100%);
                color: white;
                padding: 20px;
                border-radius: 10px 10px 0 0;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .nivel-badge {{
                display: inline-block;
                background: rgba(255,255,255,0.3);
                padding: 5px 15px;
                border-radius: 20px;
                margin-top: 10px;
                font-weight: bold;
            }}
            .content {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 0 0 10px 10px;
            }}
            .info-box {{
                background: white;
                padding: 15px;
                margin: 15px 0;
                border-radius: 8px;
                border-left: 4px solid {color};
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .info-box h3 {{
                margin-top: 0;
                color: {color};
                font-size: 16px;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e9ecef;
            }}
            .info-row:last-child {{
                border-bottom: none;
            }}
            .label {{
                font-weight: bold;
                color: #666;
            }}
            .value {{
                color: #333;
            }}
            .alert-box {{
                background: #fff3cd;
                border: 1px solid #ffc107;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                text-align: center;
            }}
            .progress-bar {{
                width: 100%;
                height: 30px;
                background: #e9ecef;
                border-radius: 15px;
                overflow: hidden;
                margin: 10px 0;
            }}
            .progress-fill {{
                height: 100%;
                background: {color};
                width: {porcentaje_stock}%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>⚠️ ALERTA DE STOCK</h1>
            <div class="nivel-badge">NIVEL: {nivel}</div>
        </div>
        
        <div class="content">
            <p><strong>📅 Fecha:</strong> {now().strftime('%d/%m/%Y a las %H:%M hrs')}</p>
            
            <div class="info-box">
                <h3>💊 INFORMACIÓN DEL MEDICAMENTO</h3>
                <div class="info-row">
                    <span class="label">Clave:</span>
                    <span class="value">{clave_safe}</span>
                </div>
                <div class="info-row">
                    <span class="label">Descripción:</span>
                    <span class="value">{descripcion_safe}</span>
                </div>
                <div class="info-row">
                    <span class="label">Presentación:</span>
                    <span class="value">{presentacion_safe}</span>
                </div>
            </div>
            
            <div class="info-box">
                <h3>🧾 INFORMACIÓN DEL LOTE</h3>
                <div class="info-row">
                    <span class="label">Código de Lote:</span>
                    <span class="value">{lote_codigo_safe}</span>
                </div>
                <div class="info-row">
                    <span class="label">Existencia Actual:</span>
                    <span class="value" style="color: {color}; font-weight: bold;">{lote.existencia} unidades</span>
                </div>
                <div class="info-row">
                    <span class="label">Fecha de Caducidad:</span>
                    <span class="value">{lote.fecha_caducidad.strftime('%d/%m/%Y')}</span>
                </div>
            </div>
            
            <div class="info-box">
                <h3>📊 ANÁLISIS DE CONSUMO</h3>
                <div class="info-row">
                    <span class="label">CPM (Consumo Promedio Mensual):</span>
                    <span class="value">{cpm_del_medicamento} unidades</span>
                </div>
                <div class="info-row">
                    <span class="label">Días de Stock Restantes:</span>
                    <span class="value">~{dias_restantes:.0f} días</span>
                </div>
            </div>
            
            <div style="margin: 20px 0;">
                <strong>Nivel de Stock:</strong>
                <div class="progress-bar">
                    <div class="progress-fill">{porcentaje_stock:.1f}%</div>
                </div>
            </div>
            
            <div class="alert-box">
                <strong>⚡ ACCIÓN REQUERIDA</strong><br>
                Revisar inventario y solicitar reabastecimiento inmediato
            </div>
        </div>
        
        <div class="footer">
            <p>Sistema de Gestión de Farmacia - Hospital<br>
            Este es un mensaje automático, por favor no responder.</p>
        </div>
    </body>
    </html>
    """
    
    msg = EmailMultiAlternatives(
        asunto, 
        mensaje_texto, 
        settings.DEFAULT_FROM_EMAIL, 
        ['HMICFarmacia@gmail.com']
    )
    msg.attach_alternative(mensaje_html, "text/html")
    msg.send()
    


@receiver(post_save, sender=Lote)
def verificar_existencia_cpm(sender, instance, **kwargs):
    
    try:
        # Esta es la ruta para obtener el CPM que SÍ usas en tu inventario
        cpm_real = instance.medicamento.cpm_medicamento.valor
    except (Medicamento.cpm_medicamento.RelatedObjectDoesNotExist, AttributeError):
        # Si el medicamento no tiene un CPM general, no hacemos nada
        cpm_real = 0

    # Si no hay CPM real, detenemos la función
    if cpm_real == 0:
        return 

    # Comparamos la existencia del LOTE contra el CPM (general) del MEDICAMENTO
    if instance.existencia <= (cpm_real // 2) and not instance.alerta_stock_enviada:
        
        # Le pasamos el CPM real (ej. 50) a la función de correo
        enviar_alerta_stock(instance, cpm_real) 
        
        instance.alerta_stock_enviada = True
        instance.save(update_fields=["alerta_stock_enviada"])
    
    # Reseteamos la alerta si el stock vuelve a subir
    elif instance.existencia > (cpm_real // 2) and instance.alerta_stock_enviada:
        instance.alerta_stock_enviada = False
        instance.save(update_fields=["alerta_stock_enviada"])
