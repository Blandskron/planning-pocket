# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Nada de efectos secundarios aquí. Este módulo se importa una vez por proceso ASGI,
# antes de que las migraciones puedan haber pasado, así que cualquier consulta en este
# punto corre en el peor momento posible. La creación del superusuario vive en
# docker-entrypoint.sh y en build.sh, que corren una vez y en el orden correcto.
django_asgi_app = get_asgi_application()

import rooms.routing  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(rooms.routing.websocket_urlpatterns))
    ),
})
