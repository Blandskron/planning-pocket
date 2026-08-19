# Copyright (c) 2024 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path


def health_check(request):
    return JsonResponse({"status": "ok"})

def handler404(request, exception):
    return JsonResponse({"error": "Not found"}, status=404)

def handler500(request):
    return JsonResponse({"error": "Server error"}, status=500)

def home_redirect(request):
    return redirect('dashboard')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('accounts/', include('accounts.urls')),
    path('', include('rooms.urls')),
    path('', home_redirect, name='home'),
]
