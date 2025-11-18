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
from django.core.exceptions import ValidationError
from django.core.mail import send_mail


class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.nombre


class UsuarioPersonalizado(AbstractUser):
    ROLES = (
        ('ADMIN', 'Administrador'),
        ('FARMACIA', 'Farmacia'),
        ('ENFERMERIA', 'Enfermería'),
        ('ROPERIA', 'Ropería'),
    )
    rol = models.CharField(max_length=20, choices=ROLES)
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, null=True, blank=True)
    telefono = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"
    
    def check_password(self, raw_password):
        # Verificación explícita para superusuarios
        if self.is_superuser:
            return super().check_password(raw_password)
        # Verificación normal para otros usuarios
        return super().check_password(raw_password)


class PerfilUsuario(models.Model):
    user = models.OneToOneField(UsuarioPersonalizado, on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.departamento}"

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

    def __str__(self):
        if self.nombre.upper() == "CAJA":
            return f"CAJA ({self.unidades_por_caja} unidades)"
        return "UNIDAD"
    
    def __str__(self):
        if self.nombre.upper() == "AMPOLLETA":
            return f"AMPOLLETA ({self.unidades_por_caja} unidades)"
        return "UNIDAD"
    


    def delete(self, *args, **kwargs):
        """Sobrescribimos delete para desactivar en lugar de borrar"""
        self.activo = False
        self.save()


class Medicamento(models.Model):
    id = models.CharField(primary_key=True, max_length=50, editable=False)
    clave = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(verbose_name="Descripción", blank=False)
    codigo_barras = models.CharField(max_length=40, null=True, blank=True)
    costo = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Costo Unitario",
        default=0.00
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Proveedor"
    )
    presentacion = models.ForeignKey(
        Presentacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Presentación"
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.clave} - {self.descripcion}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            # Generar ID automático si no existe
            self.id = f"MED-{Medicamento.objects.count() + 1:04d}"
        super().save(*args, **kwargs)
    

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
    
    @classmethod
    def actualizar_inventario(cls, medicamento_id, lote_codigo, cantidad, fecha_caducidad, presentacion_id):
        """Método para crear/actualizar lotes de forma segura"""
        with transaction.atomic():
            lote, created = cls.objects.get_or_create(
                lote_codigo=lote_codigo,
                medicamento_id=medicamento_id,
                defaults={
                    'fecha_caducidad': fecha_caducidad,
                    'existencia': cantidad,
                    'presentacion_id': presentacion_id,
                    'id': f"LOT-{uuid.uuid4().hex[:10].upper()}"  # Generar ID único
                }
            )
            
            if not created:
                lote.existencia += cantidad
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
    fecha_nacimiento = models.DateField()

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
    surtido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="recetas_surtidas"
    )

    def __str__(self):
        return f"Receta {self.id_folio} - {self.paciente.nombre_completo}"
    

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

    def __str__(self):
        return f"{self.medicamento.descripcion} - Receta {self.receta.id_folio}"
    

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
        verbose_name="Almacén"
    )
    institucion = models.ForeignKey(
        Institucion, 
        on_delete=models.PROTECT,
        verbose_name="Institución"
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
    

# Señales

@receiver(post_save, sender=DetalleEntrada)
def sumar_existencia(sender, instance, created, **kwargs):
    if created:
        # El código de lote viene en instance.lote (CharField)
        lote_codigo = instance.lote
        cantidad = instance.cantidad

        # Ajustar cantidad si la presentación es caja
        if instance.presentacion and instance.presentacion.nombre.upper() == 'CAJA':
            cantidad *= instance.presentacion.unidades_por_caja

        try:
            lote_obj = Lote.objects.get(lote_codigo=lote_codigo)
            lote_obj.existencia += cantidad
            lote_obj.save()
        except Lote.DoesNotExist:
            # Si no existe lote, tal vez lo creas o solo pasas
            # Por ejemplo, crear nuevo lote:
            Lote.objects.create(
                id=f"auto-{lote_codigo}",  # Genera un id único si quieres
                medicamento=instance.medicamento,
                lote_codigo=lote_codigo,
                fecha_caducidad=instance.caducidad,
                existencia=cantidad,
                presentacion=instance.presentacion
            )


"""@receiver(post_save, sender=Salida)
def restar_existencia(sender, instance, created, **kwargs):
    if created:
        lote = instance.lote
        cantidad = instance.cantidad

        if lote.presentacion.nombre.upper() == 'CAJA':
            cantidad *= lote.presentacion.unidades_por_caja  # convertir a unidades

        lote.existencia -= cantidad
        lote.save()

@receiver(post_save, sender=UsuarioPersonalizado)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.create(user=instance)"""


def enviar_alerta_stock(lote, cpm_del_medicamento):
    asunto = f"⚠️ Alerta: {lote.medicamento.descripcion}"
    mensaje = f"""📅 Fecha: {now().strftime('%d/%m/%Y %H:%M')}
    🧾 Lote: {lote.lote_codigo}
    💊 Medicamento: {lote.medicamento.descripcion}
    📉 Existencia (del Lote): {lote.existencia} | CPM (del Medicamento): {cpm_del_medicamento}"""
    
    # Asegúrate de que tu correo esté correcto, el que me diste en el .py tenía un .com al final
    send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, ['valenciaeliu@gmail.com']) 

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
