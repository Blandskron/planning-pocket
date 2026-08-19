from django.contrib.auth import views as auth_views
from django.urls import path

from .views import RegisterView, dashboard

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login'
    ),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
]
