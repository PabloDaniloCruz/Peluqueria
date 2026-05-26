from django import forms
from django.contrib.auth.models import User
from .models import (
    Cliente, Profesional, Servicio, FichaTecnica, Producto, Venta, 
    HorarioAtencion, CierreExcepcional, EtapaServicio
)
from django.forms import inlineformset_factory


class ReservaAlPasoForm(forms.Form):
    # --- Datos del Cliente ---
    nombre = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'}))
    apellido = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'}))
    telefono = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 387...'}))
    
    # --- Datos del Turno ---
    profesional = forms.ModelChoiceField(
        queryset=Profesional.objects.filter(activo=True), 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    servicio = forms.ModelChoiceField(
        queryset=Servicio.objects.filter(activo=True), 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # Campos desglosados para UX
    fecha = forms.DateField(
        label="Fecha",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    hora = forms.TimeField(
        label="Hora",
        widget=forms.HiddenInput()
    )

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        
        if fecha and hora:
            # Combinamos fecha y hora
            from django.utils import timezone
            from datetime import datetime
            dt = datetime.combine(fecha, hora)
            cleaned_data['fecha_hora'] = timezone.make_aware(dt)
        
        return cleaned_data

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'apellido', 'telefono', 'email']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono de contacto'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            qs = Cliente.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Este correo electrónico ya pertenece a un cliente registrado.")
        return email

class FacturacionForm(forms.Form):
    total = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    metodo_pago = forms.ChoiceField(
        choices=Venta.METODO_PAGO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class FichaTecnicaForm(forms.ModelForm):
    class Meta:
        model = FichaTecnica
        fields = ['descripcion', 'formula_quimica', 'observaciones']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2, 
                'placeholder': 'Ej. Coloración rubio ceniza, reflejos, etc.'
            }),
            'formula_quimica': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Ej. 30g de 8.1 + 30g de revelador 20 vol...'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'Sensibilidad capilar, resultados previos, etc.'
            })
        }

class ProfesionalForm(forms.ModelForm):
    habilidades_list = forms.ModelMultipleChoiceField(
        queryset=Servicio.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Servicios que realiza"
    )
    crear_usuario = forms.BooleanField(
        required=False, 
        label="¿Crear cuenta de acceso?",
        help_text="Seleccioná esto si el peluquero va a iniciar sesión en el sistema."
    )
    username = forms.CharField(
        required=False, 
        max_length=150, 
        label="Nombre de usuario",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        required=False, 
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Profesional
        fields = ['nombre', 'apellido', 'telefono', 'email', 'porcentaje_comision']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'porcentaje_comision': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['habilidades_list'].initial = self.instance.habilidades.all()
            if self.instance.usuario:
                self.fields['crear_usuario'].initial = True
                self.fields['crear_usuario'].help_text = "El empleado ya tiene usuario."
                self.fields['username'].initial = self.instance.usuario.username
                self.fields['username'].widget.attrs['readonly'] = True
                self.fields['password'].help_text = "Dejá este campo vacío si NO querés cambiar la contraseña."
                self.fields['password'].widget.attrs['placeholder'] = "•••••••• (Sin cambios)"

    def clean(self):
        cleaned_data = super().clean()
        crear_usuario = cleaned_data.get('crear_usuario')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password', '').strip()

        if crear_usuario:
            if not username:
                self.add_error('username', 'Este campo es obligatorio si se crea un usuario.')
            
            # Si estamos editando y ya tenía usuario, el password es opcional.
            # Si es nuevo, es obligatorio.
            if not self.instance.pk or not self.instance.usuario:
                if not password:
                    self.add_error('password', 'La contraseña es obligatoria para usuarios nuevos.')
            
            # Validamos que no exista otro usuario con ese nombre (si es uno nuevo)
            if username and (not self.instance.pk or not self.instance.usuario) and User.objects.filter(username=username).exists():
                self.add_error('username', 'Ese nombre de usuario ya está en uso.')
        
        return cleaned_data

class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'descripcion', 'precio_sugerido']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio_sugerido': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

EtapaServicioFormSet = inlineformset_factory(
    Servicio,
    EtapaServicio,
    fields=['orden', 'nombre', 'duracion', 'tipo_estacion', 'requiere_profesional'],
    extra=1,
    can_delete=True,
    widgets={
        'orden': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Lavado'}),
        'duracion': forms.NumberInput(attrs={'class': 'form-control', 'min': 5, 'step': 5}),
        'tipo_estacion': forms.Select(attrs={'class': 'form-select'}),
        'requiere_profesional': forms.CheckboxInput(attrs={'class': 'form-check-input'})
    }
)

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'es_para_venta', 'es_insumo', 'unidad_medida', 'precio', 'stock_actual', 'stock_minimo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'es_para_venta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_insumo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        es_para_venta = cleaned_data.get('es_para_venta')
        precio = cleaned_data.get('precio')

        if es_para_venta and precio is None:
            self.add_error('precio', 'El precio es obligatorio si el producto es para la venta.')
        return cleaned_data


class HorarioAtencionForm(forms.ModelForm):
    class Meta:
        model = HorarioAtencion
        fields = ['dia_semana', 'hora_apertura', 'hora_cierre', 'abierto']
        widgets = {
            'dia_semana': forms.Select(attrs={'class': 'form-select'}),
            'hora_apertura': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_cierre': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'abierto': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CierreExcepcionalForm(forms.ModelForm):
    class Meta:
        model = CierreExcepcional
        fields = ['fecha', 'descripcion', 'es_dia_completo', 'hora_inicio', 'hora_fin']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Feriado Nacional'}),
            'es_dia_completo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

