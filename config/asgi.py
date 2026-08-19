"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

import rooms.routing  # noqa: E402

# Auto-create superuser if credentials are in environment
from django.contrib.auth import get_user_model  # noqa: E402
User = get_user_model()
su_username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
su_email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
su_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if su_username and su_password:
    try:
        if not User.objects.filter(username=su_username).exists():
            User.objects.create_superuser(
                username=su_username,
                email=su_email,
                password=su_password
            )
            print(f"Superuser '{su_username}' created successfully.")
    except Exception as e:
        print(f"Failed to auto-create superuser: {e}")

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            rooms.routing.websocket_urlpatterns
        )
    ),
})
