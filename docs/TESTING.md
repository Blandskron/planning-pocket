# Estrategia de Testing

Siguiendo el principio de la Pirámide de Tests, priorizamos pruebas rápidas y de bajo nivel para las reglas críticas del negocio, y usamos pruebas End-to-End para flujos integrales.

## 1. Unit Tests (Mayor volumen, más rápidos)
Enfocados en el dominio, servicios puros y reglas de negocio.
**Objetivos:**
- Máquina de estados: Transiciones válidas e inválidas de una `VotingRound`.
- Cálculo de estadísticas: Promedio, consenso, exclusión de valores no numéricos (`?`, `☕`).
- Permisos (Puros): Funciones que deciden si un Rol X puede ejecutar Acción Y.

*Herramienta:* `pytest`.

## 2. Integration Tests
Valida la interacción entre módulos, la base de datos y WebSockets.
**Objetivos:**
- ORM: Creación de salas con `public_id` único, restricciones (constraints) de votos por usuario/ronda.
- Services y Views: Respuestas HTTP a acciones, creación de identidades de invitados, mantenimiento de sesiones.
- Django Channels: Conexión WebSocket, pertenencia a grupos (rooms), recepción y transmisión de payloads de estado correctos según la fase de la ronda.

*Herramienta:* `pytest-django`, `channels_testing`.

## 3. End-to-End (E2E) Tests (Solo flujos críticos)

Prueban la mesa en un navegador real, en `rooms/test_e2e.py`. Están **fuera de la corrida por
defecto** y se ejecutan aparte:

```bash
DJANGO_ALLOW_ASYNC_UNSAFE=true pytest -m e2e
```

Requieren el navegador una sola vez: `python -m playwright install chromium`.

**Por qué una corrida aparte.** Los tests de navegador necesitan dos cosas que el resto de la suite
no quiere:

- La política `WindowsProactorEventLoop`. Importar `daphne` instala la política `Selector`, que en
  Windows no tiene transporte de subprocesos, así que Playwright no puede arrancar Chromium.
  `conftest.py` la cambia sólo cuando está definida `DJANGO_ALLOW_ASYNC_UNSAFE`.
- `DJANGO_ALLOW_ASYNC_UNSAFE`. El loop de Playwright hace que Django vea un contexto async y rechace
  cada consulta síncrona. No se define globalmente **a propósito**: ese chequeo es justo el que
  detectaría una llamada cruda al ORM colándose en un método async del consumer, y eso vale la pena
  conservarlo en la corrida normal.

**Qué cubren, y dónde está el límite.** `live_server` es WSGI, así que no hay WebSocket:

- Se ejercita de verdad todo lo que ocurre al cargar: asientos sobre el anillo (sin solapes ni
  desbordes, de 2 a 14 personas), el abanico, la identidad, el contador del paño, la accesibilidad,
  el estado de una sola persona y que el móvil no se desplace de lado.
- La coreografía que normalmente dispara un broadcast (reveal, lanzamiento, recreo) se ejecuta
  llamando a las funciones del cliente, porque lo que hay que proteger es la coreografía.
- El despacho — que un mensaje `room.revealed` o `player.hit` llegue a esas funciones — está cubierto
  por los tests de consumer en `test_websockets.py`.

*Herramienta:* `Playwright` (Python).

## 4. Cobertura

El umbral de CI es **80 % general**, que es el objetivo declarado en `AGENTS.md`, y la suite
está en **80,48 %**. El margen es estrecho a propósito: un cambio que baja la cobertura falla
en el pull request, no seis meses después.

```bash
pytest . --cov --cov-report=term-missing
```

La configuración vive en `pyproject.toml`, con cobertura de ramas activada. Quedan fuera las
migraciones, los propios archivos de test, `asgi.py`, `wsgi.py` y `settings_test.py`: medir
cobertura sobre código generado o sobre los tests mismos infla el número sin decir nada.

Estado por archivo, y dónde está la deuda:

| Archivo | Cobertura | |
| --- | --- | --- |
| `rooms/services.py` | 96 % | Las reglas de negocio. El objetivo de dominio es 90 %. |
| `rooms/models.py` | 94 % | |
| `rooms/views.py` | 80 % | |
| `rooms/consumers.py` | **67 %** | El punto flojo conocido. |
| `config/settings.py` | 67 % | Las ramas de producción no se ejercitan aquí sino en CI. |

`consumers.py` es el archivo con más superficie sin cubrir. No es tan grave como parece —lo
que decide algo vive en `services.py`, que sí está al 96 %— pero el despacho de eventos, los
caminos de error y el ciclo de conexión sí merecen más tests. Está anotado en `PLAN.md`.

## 5. Qué corre en CI

`.github/workflows/ci.yml` valida cada pull request contra `main`:

- `ruff check` sobre todo el repositorio.
- La suite por defecto en Python 3.12 y 3.13, con el umbral de cobertura.
- Los tests de navegador, con `DJANGO_ALLOW_ASYNC_UNSAFE=true` y Chromium.
- `manage.py check`, `makemigrations --check`, y —esto es lo que no cubre la suite—
  `check --deploy` y `collectstatic` con `DJANGO_DEBUG=False` y el storage real. La suite
  corre con `config.settings_test`, que desactiva whitenoise, HSTS y las cookies seguras; sin
  ese paso, un fallo en la configuración de producción no lo ve nadie hasta el despliegue.
- La imagen Docker se construye **y tiene que arrancar**.

### Por qué la suite tarda 5 segundos y no 8 minutos

Tardaba 8 min 30 s. Los tests usaban el hasher de contraseñas de producción, y cada inicio de
sesión pagaba unos nueve segundos de PBKDF2. `config/settings_test.py` fija
`PASSWORD_HASHERS` a MD5. No es una decisión de seguridad —nada de esa base de datos
sobrevive a la corrida— sino lo que hace que la suite quepa en un pull request.

## 6. Test-First en Reglas Críticas
Se implementarán pruebas antes de escribir el código funcional para las siguientes áreas:
- `cast_vote()`
- `reveal_round()`
- `reset_round()`
- Mantenimiento y validación de la identidad del Invitado (`guest identity`).
- Mecanismos de Autorización en el backend.
- Filtrado de valores de votos salientes (Privacidad).
