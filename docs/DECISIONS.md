# Registro de Decisiones Arquitectónicas (ADR)

Este documento registra decisiones técnicas y de diseño importantes que impactan a Planning Pocket.

---

## ADR-001 — Django como framework central

**Estado:** Aceptado

**Decisión:** Utilizar Python con Django como el entorno principal para construir el producto, y renderizar el frontend inicial con Django Templates. No crear una SPA de inmediato.

**Motivo:** Queremos mantener el proyecto simple, rápido de iterar y reducir la complejidad del ciclo de CI/CD. Django nos proporciona autenticación, ORM seguro, sesiones de manera inmediata, eliminando la fricción de manejar CORS, tokens JWT y APIs REST para operaciones triviales iniciales.

**Consecuencias:**
- La experiencia inicial podría parecer tradicional, pero se compensará con interactividad incremental (WebSockets/HTMX).
- Mayor dependencia en la redención de plantillas en el servidor.

---

## ADR-002 — Django Channels y Redis para tiempo real

**Estado:** Aceptado

**Decisión:** Adoptar WebSockets mediante Django Channels y usar Redis como capa base.

**Motivo:** Una aplicación de Planning Poker pierde su utilidad si la mesa requiere F5/recargar para ver los votos de los demás. Requerimos notificaciones push desde el backend a todos los clientes de una sala concurrentemente con latencia baja.

**Consecuencias:**
- Requiere correr ASGI (como Daphane o Uvicorn) en lugar del tradicional WSGI en producción.
- Añade Redis a la matriz de dependencias e infraestructura.

---

## ADR-003 — Autoridad en el Servidor (Server-Side Authority)

**Estado:** Aceptado

**Decisión:** El frontend carece totalmente de poder sobre las validaciones, el estado de la ronda, y los cálculos estadísticos.

**Motivo:** Al existir roles (Facilitador, Invitado) y reglas estrictas de privacidad antes del *reveal*, la arquitectura no puede confiar en el lado del cliente (Navegador) para ocultar información, porque es fácilmente auditable o manipulable.

**Consecuencias:**
- Todo evento generado por el usuario ("Votar") es solo una "intención" que el Servidor debe ejecutar.
- El servidor deberá enviar estados consolidados por WebSockets a los clientes.

---

## ADR-004 — URL Compartida con Identificador Impredecible

**Estado:** Aceptado

**Decisión:** Las URL para unirse como invitado se basarán en un identificador alfanumérico aleatorio (ej. `public_id`).

**Motivo:** Facilitar el acceso rápido al equipo sin cuentas, y prevenir enumeración y robo de privacidad si se usaran identificadores numéricos incrementales.
