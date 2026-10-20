# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

"""Freno de intentos de acceso, contado por nombre de usuario.

Por usuario y no por IP, a propósito. La aplicación corre detrás de un proxy
(`SECURE_PROXY_SSL_HEADER` está puesto), así que `REMOTE_ADDR` es la IP del proxy:
contar por ahí significa o confiar en una cabecera que cualquiera puede escribir, o
meter a todo el mundo en el mismo cubo y que un solo atacante deje fuera a la empresa
entera. Contar por usuario ataca lo que de verdad se quiere frenar —probar miles de
contraseñas contra una cuenta— sin ninguna de las dos cosas.

Tiene un coste conocido y aceptado: alguien puede dejar bloqueada una cuenta ajena
fallando a propósito. Por eso la ventana es corta y el contador se borra en cuanto se
entra bien. Sin dependencia nueva: el almacén es la caché, que en producción es el
mismo Redis que ya usa la capa de canales.
"""

import hashlib

from django.core.cache import cache

MAX_ATTEMPTS = 10
WINDOW_SECONDS = 15 * 60


def _key(username):
    # Hasheado: el nombre de usuario es un dato personal y no tiene por qué quedar
    # legible en las claves de un Redis compartido.
    digest = hashlib.sha256((username or '').strip().lower().encode('utf-8')).hexdigest()
    return f'login-attempts:{digest[:32]}'


def attempts_left(username):
    return max(0, MAX_ATTEMPTS - cache.get(_key(username), 0))


def is_locked_out(username):
    return attempts_left(username) == 0


def record_failure(username):
    """Suma un intento fallido y devuelve cuántos quedan."""
    key = _key(username)
    # `add` sólo escribe si no existe, así que fija la ventana en el primer fallo y no
    # la renueva con cada intento: si no, un atacante constante mantendría la cuenta
    # bloqueada indefinidamente.
    cache.add(key, 0, WINDOW_SECONDS)
    try:
        cache.incr(key)
    except ValueError:
        # La clave expiró entre el `add` y el `incr`.
        cache.set(key, 1, WINDOW_SECONDS)
    return attempts_left(username)


def clear(username):
    cache.delete(_key(username))
