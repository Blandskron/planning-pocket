# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

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
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nombre de usuario'
        self.fields['password'].label = 'Contraseña'
