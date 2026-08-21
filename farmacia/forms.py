from django import forms
from .models import Lote, Receta, RecetaMedicamento, Medicamento, Proveedor, Institucion
from django.core.exceptions import ValidationError
from django.utils import timezone

class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = '__all__'
        widgets = {
            'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
            'fecha_surtido': forms.DateInput(attrs={'type': 'date'}),
        }

class RecetaMedicamentoForm(forms.ModelForm):
    class Meta:
        model = RecetaMedicamento
        fields = '__all__'

class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = [
            'medicamento',
            'presentacion',
            'lote_codigo',
            'fecha_caducidad',
            'cpm',
            'existencia'
        ]
        widgets = {
            'fecha_caducidad': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def clean_fecha_caducidad(self):
        fecha = self.cleaned_data['fecha_caducidad']
        if fecha <= timezone.now().date():
            raise ValidationError("La fecha de caducidad debe ser futura")
        return fecha

    def clean_existencia(self):
        existencia = self.cleaned_data['existencia']
        if existencia < 0:
            raise ValidationError("La existencia no puede ser negativa")
        return existencia


class MedicamentoForm(forms.ModelForm):
    """Formulario para registrar medicamentos - Solo clave y descripción"""
    
    class Meta:
        model = Medicamento
        fields = ['clave', 'descripcion']  # Solo estos dos campos
        
        widgets = {
            'clave': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: PAR-500',
                'required': True
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Paracetamol 500mg tabletas',
                'rows': 3,
                'required': True
            }),
        }
        
        labels = {
            'clave': 'Clave del Medicamento',
            'descripcion': 'Descripción',
        }
    
    def clean_clave(self):
        """Validar que la clave no esté duplicada"""
        clave = self.cleaned_data.get('clave')
        if clave:
            clave = clave.strip().upper()
            if Medicamento.objects.filter(clave=clave).exists():
                raise forms.ValidationError('Ya existe un medicamento con esta clave.')
        return clave
    
    def clean_descripcion(self):
        """Validar descripción"""
        descripcion = self.cleaned_data.get('descripcion')
        if descripcion:
            descripcion = descripcion.strip()
            if len(descripcion) < 5:
                raise forms.ValidationError('La descripción debe tener al menos 5 caracteres.')
        return descripcion


class SalidaForm(forms.Form):
    # --- Campos del Paciente/Receta (se envían desde el HTML) ---
    paciente_curp = forms.CharField(max_length=18, label="CURP", required=False,)
    paciente_nombre = forms.CharField(max_length=200, label="Nombre del Paciente")
    paciente_nacimiento = forms.DateField(label="Fecha de Nacimiento", widget=forms.DateInput(attrs={'type': 'date'}))
    
    # Traemos los "choices" del modelo Receta al formulario
    receta_origen = forms.ChoiceField(choices=Receta.ORIGEN_CHOICES, label="Origen", widget=forms.Select(attrs={'class': 'form-select'}))
    receta_folio = forms.CharField(max_length=20, required=False, label="Folio de Receta")

    # --- Campos del Lote/Cantidad (como antes) ---
    lote_id = forms.CharField(widget=forms.HiddenInput())
    cantidad_salida = forms.IntegerField(
        min_value=1, 
        label="Cantidad a Surtir",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Añadimos un 'empty_label' al select de origen
        self.fields['receta_origen'].choices = [('', 'Seleccione un origen...')] + list(Receta.ORIGEN_CHOICES)

    def clean_paciente_curp(self):
        # Limpiamos el CURP para guardarlo siempre igual
        curp = self.cleaned_data.get('paciente_curp')
        return curp.upper().strip() # Guardar siempre en mayúsculas y sin espacios

    def clean(self):
        cleaned_data = super().clean()
        lote_id = cleaned_data.get('lote_id')
        cantidad_salida = cleaned_data.get('cantidad_salida')

        if lote_id and cantidad_salida:
            try:
                lote = Lote.objects.get(pk=lote_id)
                if cantidad_salida > lote.existencia: 
                    raise forms.ValidationError(
                        f"No puedes surtir {cantidad_salida}. "
                        f"Solo quedan {lote.existencia} en stock."
                    )
                # Guardamos el objeto lote en el form para usarlo en la vista
                cleaned_data['lote_obj'] = lote 
            except Lote.DoesNotExist:
                raise forms.ValidationError("El lote seleccionado no existe.")
        return cleaned_data

class SalidaTransferenciaForm(forms.Form):
    institucion_destino = forms.ModelChoiceField(
        queryset=Institucion.objects.filter(activo=True),
        label="Institución Destino",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    observaciones = forms.CharField(
        required=False, widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'})
    )

class CargaMasivaForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo Excel',
        required=True,
        help_text='Selecciona un archivo Excel (.xlsx o .xls) con los medicamentos',
        widget=forms.FileInput(attrs={
            'accept': '.xlsx,.xls',
            'class': 'form-control',
            'id': 'archivo-excel'
        })
    )
    
    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        
        if not archivo:
            raise ValidationError('Debes seleccionar un archivo')
        
        # Validar extensión
        nombre_archivo = archivo.name.lower()
        if not (nombre_archivo.endswith('.xlsx') or nombre_archivo.endswith('.xls')):
            raise ValidationError('El archivo debe ser Excel (.xlsx o .xls)')
        
        # Validar tamaño (máximo 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if archivo.size > max_size:
            raise ValidationError('El archivo es demasiado grande. Máximo 10MB permitido.')
        
        return archivo