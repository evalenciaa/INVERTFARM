from django import forms
from .models import Lote, Receta, RecetaMedicamento, Medicamento, Proveedor, Institucion, CatalogoAntibioticosWHO
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
        fields = [
            'clave',
            'descripcion',
            'es_antibiotico',
            'via_administracion',
            'codigo_atc',
            'categoria_aware',
            'gramos_por_pieza',
            'valor_atc',
        ]

        widgets = {
            'clave': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: PAR-500',
                'autocomplete': 'off',
                'required': True,
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Paracetamol 500 mg tabletas',
                'rows': 3,
                'required': True,
            }),
            'es_antibiotico': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_es_antibiotico',
            }),
            'via_administracion': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_via_administracion',
            }),
            'codigo_atc': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_codigo_atc',
                'placeholder': 'Ej: J01CA04',
                'autocomplete': 'off',
            }),
            'categoria_aware': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_categoria_aware',
            }),
            'gramos_por_pieza': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_gramos_por_pieza',
                'step': '0.0001',
                'min': '0',
                'placeholder': 'Ej: 0.5000',
            }),
            'valor_atc': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'id_valor_atc',
                'step': '0.0001',
                'min': '0',
                'placeholder': 'Ej: 1.5000',
            }),
        }

        labels = {
            'clave': 'Clave del medicamento',
            'descripcion': 'Descripción',
            'es_antibiotico': '¿Es antibiótico?',
            'via_administracion': 'Vía de administración',
            'codigo_atc': 'Código ATC',
            'categoria_aware': 'Categoría AWaRe',
            'gramos_por_pieza': 'Gramos por pieza',
            'valor_atc': 'Valor ATC',
        }

    def clean_clave(self):
        clave = (self.cleaned_data.get('clave') or '').strip().upper()

        if Medicamento.objects.filter(clave=clave).exists():
            raise forms.ValidationError(
                'Ya existe un medicamento con esta clave.'
            )

        return clave

    def clean_descripcion(self):
        descripcion = (self.cleaned_data.get('descripcion') or '').strip()

        if len(descripcion) < 5:
            raise forms.ValidationError(
                'La descripción debe tener al menos 5 caracteres.'
            )

        return descripcion

    def clean_codigo_atc(self):
        codigo_atc = self.cleaned_data.get('codigo_atc')

        if codigo_atc:
            return codigo_atc.strip().upper()

        return codigo_atc

    def clean(self):
        cleaned_data = super().clean()

        es_antibiotico = cleaned_data.get('es_antibiotico')
        codigo_atc = cleaned_data.get('codigo_atc')
        via_administracion = cleaned_data.get('via_administracion')
        categoria_aware = cleaned_data.get('categoria_aware')
        gramos_por_pieza = cleaned_data.get('gramos_por_pieza')
        valor_atc = cleaned_data.get('valor_atc')

        if not es_antibiotico:
            cleaned_data['via_administracion'] = None
            cleaned_data['codigo_atc'] = None
            cleaned_data['categoria_aware'] = None
            cleaned_data['gramos_por_pieza'] = None
            cleaned_data['valor_atc'] = None
            return cleaned_data

        if not via_administracion:
            self.add_error(
                'via_administracion',
                'Selecciona la vía de administración.'
            )

        if not codigo_atc:
            self.add_error(
                'codigo_atc',
                'El código ATC es obligatorio para antibióticos.'
            )

        if gramos_por_pieza is None:
            self.add_error(
                'gramos_por_pieza',
                'Indica los gramos por pieza.'
            )

        if codigo_atc:
            catalogo = CatalogoAntibioticosWHO.objects.filter(
                codigo_atc=codigo_atc
            ).first()

            if catalogo:
                if not categoria_aware:
                    cleaned_data['categoria_aware'] = (
                        catalogo.categoria_aware
                    )

            if valor_atc is None:
                cleaned_data['valor_atc'] = catalogo.valor_atc

        return cleaned_data


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