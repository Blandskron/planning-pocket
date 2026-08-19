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
Prueban la experiencia completa del usuario en el navegador.
**Escenarios Principales:**
- Autenticación y creación de sala por Facilitador.
- Ingreso de invitado a la sala vía URL.
- Interacción en tiempo real: Facilitador e invitado votan, y el Facilitador revela la ronda.
- Desconexión simulada y reconexión (refrescar página).

*Herramienta:* `Playwright` (Python).

## 4. Test-First en Reglas Críticas
Se implementarán pruebas antes de escribir el código funcional para las siguientes áreas:
- `cast_vote()`
- `reveal_round()`
- `reset_round()`
- Mantenimiento y validación de la identidad del Invitado (`guest identity`).
- Mecanismos de Autorización en el backend.
- Filtrado de valores de votos salientes (Privacidad).
