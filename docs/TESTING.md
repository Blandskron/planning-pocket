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

## 4. Test-First en Reglas Críticas
Se implementarán pruebas antes de escribir el código funcional para las siguientes áreas:
- `cast_vote()`
- `reveal_round()`
- `reset_round()`
- Mantenimiento y validación de la identidad del Invitado (`guest identity`).
- Mecanismos de Autorización en el backend.
- Filtrado de valores de votos salientes (Privacidad).
