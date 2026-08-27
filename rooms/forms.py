# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django import forms

from .identity import COLOR_CHOICES, PETS
from .models import Issue, PokerRoom


class PokerRoomForm(forms.ModelForm):
    class Meta:
        model = PokerRoom
        fields = ['name']
        widgets = {
            'name': forms.TextInput(
                attrs={'placeholder': 'Ej. Planning Sprint 42', 'autocomplete': 'off'}
            ),
        }
        labels = {'name': 'Nombre de la sala'}

class GuestJoinForm(forms.Form):
    display_name = forms.CharField(
        max_length=50,
        label='Tu nombre',
        error_messages={'required': 'Escribe tu nombre para entrar.'},
        widget=forms.TextInput(
            attrs={'placeholder': 'Ej. Andrea', 'autocomplete': 'name', 'autofocus': True}
        )
    )
    pet = forms.ChoiceField(
        choices=PETS,
        label='Tu mascota',
        required=False,
        widget=forms.RadioSelect,
        error_messages={'invalid_choice': 'Elige una de las mascotas disponibles.'},
    )
    color_index = forms.TypedChoiceField(
        choices=COLOR_CHOICES,
        coerce=int,
        # Without this an unanswered picker cleans to '', which a
        # PositiveSmallIntegerField cannot store.
        empty_value=None,
        label='Tu color',
        required=False,
        widget=forms.RadioSelect,
        error_messages={'invalid_choice': 'Elige uno de los colores disponibles.'},
    )

class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Título de la historia'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Contexto opcional'}),
        }
        labels = {'title': 'Historia', 'description': 'Descripción'}
