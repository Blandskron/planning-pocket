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

---

## ADR-005 — Capa de juego cosmética y autoritativa en el servidor

**Estado:** Aceptado

**Decisión:** Añadir una capa de interacción entre pares — lanzar objetos blandos a
otra persona de la mesa — que es puramente cosmética, efímera y desactivable por dos
interruptores independientes. El servidor decide cada lanzamiento; el navegador sólo
envía una intención y espera el broadcast.

**Motivo:** La sala funcionaba pero se sentía como un formulario. La espera entre el
primer voto y el último es tiempo muerto, y es justo donde un equipo que está en la
misma sala bromearía. Queremos recuperar ese momento sin convertirlo en presión.

Esto **revierte una decisión anterior de producto**: `docs/ROOM_VISUAL_DESIGN.md`
traducía «atacar» como un recordatorio amable, exclusivo del facilitador. El
recordatorio se conserva, pero deja de ser la única interacción posible entre
personas.

**Consecuencias:**

- Dos eventos nuevos en el protocolo: la acción `player.throw {target_id, item}` y el
  evento `player.hit {thrower_id, target_id, item}`. El payload se comprueba con
  igualdad exacta en los tests: es todo el contrato, y no cabe nada más.
- Tres campos nuevos: `PokerRoom.allow_playful_actions`,
  `Participant.last_throw_at` y `Participant.throws_this_round`.
- Los límites viven en `rooms/services.py`, no en el cliente: 2,5 s de espera por
  persona y un tope por ronda. El navegador no puede concederse un brazo más rápido.

**Reglas que hacen que esto siga siendo un juego.** Son parte de la decisión, no una
nota al pie:

1. **El voto sigue privado.** Ni `player.throw` ni `player.hit` transportan
   información de voto, y hay un test que lo verifica con igualdad exacta del payload.
2. **El objeto es idéntico haya votado el destinatario o no.** Las comprobaciones del
   servicio son deliberadamente ciegas a `current_vote`, así que un lanzamiento nunca
   puede leerse como una señal sobre la carta de alguien ni sobre su silencio.
3. **Nada acumula.** `throws_this_round` muere con la ronda. No hay marcador de quién
   recibió más impactos ni ranking de quién tardó más.
4. **Nada automático ni dirigido por estado.** Ningún objeto sale solo hacia quien no
   ha votado, y el aro de puntería aparece igual sobre todas las caras.
5. **El catálogo se queda blando.** Comida, papel y objetos de oficina absurdos.
   Ningún objeto que lea como arma o como daño.
6. **Doble consentimiento.** El facilitador apaga la capa para toda la sala;
   cada persona puede apagar los efectos en su propia pantalla. Y
   `prefers-reduced-motion` manda por encima de ambos.
7. **La reunión gana.** Nada tapa la mano de cartas ni el botón de revelar, nada
   bloquea la entrada, y los proyectiles y las manchas del paño tienen tope.

**Alternativa descartada:** dejar el «ataque» sólo como recordatorio del facilitador.
Es más seguro, pero mantiene la asimetría que hacía que la sala se sintiera como un
panel de administración: una persona con controles y el resto esperando.
