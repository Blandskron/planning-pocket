# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg2-binary trae ruedas manylinux, así que no hay nada que compilar: ni
# build-essential ni libpq-dev. Instalarlos añadía cientos de megas de toolchain a una
# imagen que nunca compila nada. El job `docker` de CI construye y arranca esta imagen,
# así que si alguna dependencia vuelve a necesitar compilador, se sabe en el pull request.

# Las dependencias primero: cambian mucho menos que el código, y así la capa se reutiliza.
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Lo que NO entra aquí está en .dockerignore, y eso incluye el .env de quien construye.
COPY . /app/

# Los estáticos se recogen aquí para no necesitar el secreto real de producción durante el
# build; DJANGO_DEBUG=True sólo afecta a este comando y no queda en la imagen.
RUN DJANGO_DEBUG=True DJANGO_SECRET_KEY=build-only-key python manage.py collectstatic --noinput

RUN chmod +x /app/docker-entrypoint.sh

# Sin usuario propio, la aplicación corre como root: cualquier ejecución de código dentro
# del contenedor empieza con todos los permisos. /app queda a su nombre porque el
# entrypoint vuelve a escribir en staticfiles/ al arrancar.
RUN useradd --create-home --uid 10001 planning \
    && chown -R planning:planning /app
USER planning

EXPOSE 8000

# Comprueba que daphne acepta conexiones, no que /health/ devuelva 200. Un GET desde dentro
# del contenedor llega con Host 127.0.0.1, que no está en DJANGO_ALLOWED_HOSTS en producción
# —y con SECURE_SSL_REDIRECT también se llevaría un 301—, así que un healthcheck HTTP daría
# rojo con la aplicación perfectamente sana. /health/ sigue existiendo para el balanceador,
# que sí llega con el Host correcto.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8000), 4).close()"

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
