# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

"""Content-Security-Policy con nonce por petición.

Sin dependencia nueva: son treinta líneas y lo que haría una librería es exactamente
esto. Lo que compra: el navegador deja de ejecutar cualquier script que no lleve el
nonce de esta respuesta, así que una inyección de HTML en la sala —el nombre que
escribe un invitado es el dato de tercero más expuesto que tiene el producto— no puede
convertirse en ejecución de código.

Dos concesiones, las dos deliberadas:

- `style-src` admite `'unsafe-inline'`. La mesa coloca los asientos escribiendo
  `style="--seat-angle: …"` en cada uno, y un atributo de estilo no se puede firmar con
  nonce. La protección que importa está en `script-src`, que es donde se ejecuta código.
- `connect-src` lista el WebSocket del propio host en lugar de confiar en que `'self'`
  cubra `ws://`: los navegadores no se ponen de acuerdo en eso, y una sala que no
  conecta es peor que una cabecera un poco más larga.
"""

import secrets

from django.conf import settings

NONCE_BYTES = 16


class ContentSecurityPolicyMiddleware:
    """Pone un nonce en la petición y la cabecera en la respuesta."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(NONCE_BYTES)
        response = self.get_response(request)

        # El admin de Django trae su propio JavaScript en línea sin nonce. Aplicarle
        # esta política lo rompería, y no es la superficie que se quiere proteger.
        if request.path.startswith('/admin/'):
            return response

        header = (
            'Content-Security-Policy-Report-Only'
            if getattr(settings, 'CSP_REPORT_ONLY', False)
            else 'Content-Security-Policy'
        )
        if header not in response:
            response[header] = self.policy(request)
        return response

    @staticmethod
    def policy(request):
        host = request.get_host()
        scheme = 'wss' if request.is_secure() else 'ws'
        return '; '.join([
            "default-src 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "img-src 'self' data:",
            "font-src 'self' https://fonts.gstatic.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            f"script-src 'self' 'nonce-{request.csp_nonce}'",
            f"connect-src 'self' {scheme}://{host}",
        ])


def csp_nonce(request):
    """Context processor: expone el nonce a las plantillas."""
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}
