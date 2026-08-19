# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.contrib.auth.forms import UserCreationForm

from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields
