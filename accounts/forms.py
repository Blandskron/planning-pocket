# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from . import throttling
from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nombre de usuario'
        self.fields['username'].help_text = 'Hasta 150 caracteres. Usa letras, números y @/./+/-/_.'
        self.fields['password1'].label = 'Contraseña'
        self.fields['password1'].help_text = (
            'Usa al menos 8 caracteres y evita claves demasiado comunes o solo numéricas.'
        )
        self.fields['password2'].label = 'Confirmar contraseña'
        self.fields['password2'].help_text = 'Repite la contraseña para confirmar.'


class SpanishAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'El nombre de usuario o la contraseña no son correctos.',
        'inactive': 'Esta cuenta está inactiva.',
        'locked_out': (
            'Demasiados intentos fallidos con este usuario. '
            'Espera unos minutos antes de volver a probar.'
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nombre de usuario'
        self.fields['password'].label = 'Contraseña'

    def clean(self):
        """Cuenta los intentos antes y después de comprobar la contraseña.

        Aquí y no en la vista porque es el único sitio que distingue un intento fallido
        de un formulario mal rellenado. El mensaje de bloqueo no dice si el usuario
        existe: es el mismo para una cuenta real y para una inventada.
        """
        username = self.cleaned_data.get('username')
        if username and throttling.is_locked_out(username):
            raise forms.ValidationError(
                self.error_messages['locked_out'], code='locked_out'
            )
        try:
            cleaned = super().clean()
        except forms.ValidationError:
            if username:
                throttling.record_failure(username)
            raise
        if username:
            throttling.clear(username)
        return cleaned
