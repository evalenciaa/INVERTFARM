from django import forms
from .models import Colectivo, ColectivoMedicamento
from farmacia.models import Medicamento, Paciente

class ColectivoForm(forms.ModelForm):
    """
    Formulario para crear colectivos (Paciente o Stock)
    """
    class Meta:
        model = Colectivo
        fields = [
            'tipo_colectivo',
            'paciente',
            'numero_cama',
            'turno',
            'servicio',
            'observaciones_enfermeria'
        ]
        widgets = {
            'tipo_colectivo': forms.RadioSelect(attrs={
                'class': 'tipo-radio'
            }),
            'paciente': forms.Select(attrs={
                'class': 'form-control',
                'id': 'paciente_id'
            }),
            'numero_cama': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: C-101',
                'id': 'numero_cama'
            }),
            'turno': forms.Select(attrs={
                'class': 'form-control',
                'id': 'turno'
            }),
            'servicio': forms.Select(attrs={
                'class': 'form-control',
                'id': 'servicio'
            }),
            'observaciones_enfermeria': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ej: Paciente alérgico a penicilina, administrar con alimentos, etc.',
                'id': 'observaciones'
            })
        }
        labels = {
            'tipo_colectivo': 'Tipo de Colectivo',
            'paciente': 'Paciente',
            'numero_cama': 'Número de Cama',
            'turno': 'Turno Solicitante',
            'servicio': 'Servicio o Área',
            'observaciones_enfermeria': 'Indicaciones especiales'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizar queryset de pacientes
        self.fields['paciente'].queryset = Paciente.objects.all().order_by('nombre_completo')
        self.fields['paciente'].empty_label = "Seleccione un paciente..."
        
        # Crear opciones de servicio como choices
        servicios_opciones = [
            ('', 'Seleccione un servicio...'),
            ('Urgencias', 'Urgencias'),
            ('Hospitalización Piso 1', 'Hospitalización Piso 1'),
            ('Hospitalización Piso 2', 'Hospitalización Piso 2'),
            ('Hospitalización Piso 3', 'Hospitalización Piso 3'),
            ('UCI Adultos', 'UCI Adultos'),
            ('UCI Pediátrica', 'UCI Pediátrica'),
            ('UCI Neonatal', 'UCI Neonatal'),
            ('Quirófano', 'Quirófano'),
            ('Labor y Parto', 'Labor y Parto'),
            ('Tococirugía', 'Tococirugía'),
            ('Sala de Choque', 'Sala de Choque'),
            ('Consulta Externa', 'Consulta Externa'),
        ]
        
        self.fields['servicio'].widget = forms.Select(
            choices=servicios_opciones,
            attrs={'class': 'form-control', 'id': 'servicio'}
        )
        
        # Hacer campos opcionales por defecto (se validarán según el tipo)
        self.fields['paciente'].required = False
        self.fields['numero_cama'].required = False
        self.fields['turno'].required = False
        self.fields['servicio'].required = True  # Siempre requerido
    
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_colectivo')
        
        # ✅ Validar según el tipo de colectivo
        if tipo == 'PACIENTE':
            # Campos obligatorios para PACIENTE
            if not cleaned_data.get('paciente'):
                self.add_error('paciente', 'El paciente es obligatorio para colectivos de tipo PACIENTE')
            
            if not cleaned_data.get('numero_cama'):
                self.add_error('numero_cama', 'El número de cama es obligatorio para colectivos de tipo PACIENTE')
            
            # ✅ Limpiar campo de turno
            cleaned_data['turno'] = None
        
        elif tipo == 'STOCK':
            # Campos obligatorios para STOCK
            if not cleaned_data.get('turno'):
                self.add_error('turno', 'El turno es obligatorio para colectivos de tipo STOCK')
            
            # ✅ Limpiar campos de paciente (IMPORTANTE)
            cleaned_data['paciente'] = None
            cleaned_data['numero_cama'] = None
        
        return cleaned_data
        
