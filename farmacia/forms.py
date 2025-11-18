from django import forms
from .models import Lote, Receta, RecetaMedicamento, Medicamento, Proveedor
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
    class Meta:
        model = Medicamento
        fields = ['clave', 'descripcion', 'codigo_barras', 'costo', 'proveedor']
        widgets = {
            'clave': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: PAR-500',
                'pattern': '[A-Za-z0-9-]+',
                'title': 'Solo letras, números y guiones'
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Paracetamol 500mg tabletas'
            }),
            'codigo_barras': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 750123456789',
                'pattern': '[0-9]+',
                'title': 'Solo números'
            }),
            'costo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 25.50',
                'step': '0.01',
                'min': '0'
            }),
            'proveedor': forms.Select(attrs={
                'class': 'form-control'
            })
        }
        labels = {
            'clave': 'Clave del Medicamento',
            'descripcion': 'Descripción',
            'codigo_barras': 'Código de Barras',
            'costo': 'Costo Unitario',
            'proveedor': 'Proveedor'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.filter(activo=True)
        self.fields['proveedor'].empty_label = "Seleccione un proveedor..."
        
    def clean_clave(self):
        clave = self.cleaned_data['clave']
        if Medicamento.objects.filter(clave=clave).exists():
            raise forms.ValidationError("Esta clave ya está registrada")
        return clave
        
    def clean_codigo_barras(self):
        codigo = self.cleaned_data['codigo_barras']
        if codigo and Medicamento.objects.filter(codigo_barras=codigo).exists():
            raise forms.ValidationError("Este código de barras ya está registrado")
        return codigo


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