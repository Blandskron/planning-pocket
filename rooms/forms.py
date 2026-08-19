from django import forms

from .models import Issue, PokerRoom


class PokerRoomForm(forms.ModelForm):
    class Meta:
        model = PokerRoom
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ej. Sprint 42 Planning'}),
        }

class GuestJoinForm(forms.Form):
    display_name = forms.CharField(
        max_length=50,
        label='Your Name',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your name to join'})
    )

class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. As a user, I want to...'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional details'}),
        }
