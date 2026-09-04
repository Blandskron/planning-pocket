# Arquitectura de Planning Pocket

## 1. Visión General
El sistema sigue una arquitectura monolítica modular basada en Django, donde el servidor es la fuente de verdad (Server-Side Authority). Se utiliza Django Channels y Redis para mantener sincronizados a los participantes de la sala en tiempo real.

## 2. Aplicaciones (Módulos)
El proyecto se divide en dos aplicaciones Django:

- **`accounts`**: Gestión de usuarios autenticados, registro, login y sesiones.
- **`rooms`**: Todo lo demás. Salas, enlaces públicos (`public_id`), identidades de invitados,
  issues, la máquina de estados de la votación y la capa de tiempo real.

El diseño original preveía una tercera app `poker` para el núcleo del negocio. Nunca llegó a
tener código: las reglas viven en `rooms/services.py`, que es el único lugar que decide si una
acción es válida. La app vacía se eliminó antes de la v1.0.0 en vez de arrastrarla como
promesa. Si el dominio crece lo bastante para justificar la separación, el corte natural sigue
siendo `services.py`.

## 3. Límites de Responsabilidad
- **Backend (Django)**: Valida todas las acciones, autoriza a los usuarios y mantiene el estado. Calcula resultados estadísticos y determina qué información es visible.
- **Frontend (HTML/JS/CSS)**: Renderiza el estado proporcionado por el backend y envía intenciones de acción (ej. "quiero votar un 5"). El navegador no tiene autoridad sobre la validez del estado.
- **Channel Layer (Redis)**: Actúa como broker de mensajes para distribuir eventos de estado a los clientes conectados vía WebSocket.

## 4. Máquina de Estados (Voting Round)
El flujo de una ronda de votación para una Issue está gobernado por estados explícitos:

- **`WAITING`**: Estado inicial antes de abrir la votación (o cuando se está configurando la tarea).
- **`VOTING`**: La votación está abierta. Los participantes pueden emitir o cambiar sus votos. **Regla de privacidad activa**: Los valores de los votos de los demás participantes no se exponen; solo se comunica el evento `has_voted=true`.
- **`REVEALED`**: El facilitador revela los votos. La ronda se cierra para nuevos votos. El backend calcula promedios y transmite los valores exactos a los clientes.
- **`CLOSED`**: La ronda finaliza (se puede haber guardado el consenso o pasado a una nueva ronda).

Transiciones válidas:
- `WAITING -> VOTING` (Facilitador inicia la ronda)
- `VOTING -> REVEALED` (Facilitador revela)
- `REVEALED -> VOTING` / `REVEALED -> WAITING` (Facilitador reinicia la ronda)
- `REVEALED -> CLOSED` (Se guarda estimación y se cierra)

## 5. Protocolo WebSocket Inicial
La comunicación WebSocket transmitirá principalmente actualizaciones de estado.

**Estructura del Mensaje Base:**
```json
{
  "type": "event_type",
  "payload": {}
}
```

**Eventos Clave:**
- `participant.joined` / `participant.left`: Un usuario entra/sale de la sala.
- `vote.changed`: Un usuario ha votado. Durante `VOTING`, el payload solo envía `{"participant_id": "123", "has_voted": true}`.
- `round.started`: Inicia una nueva ronda.
- `round.revealed`: Revela la ronda actual. El payload contendrá los resultados y los votos reales.
- `round.reset`: Se reinicia la mesa.
- `issue.selected`: El facilitador cambió la historia a estimar.
- `player.hit`: Alguien lanzó un objeto a otra persona. Payload exacto:
  `{"thrower_id": 1, "target_id": 2, "item": "tomate"}`. Es cosmético y deliberadamente
  estrecho: no transporta información de voto (ver ADR-005).
- `room.playful_changed`: El facilitador activó o desactivó la capa de juego para la sala.
- `player.moved`: Posición de alguien durante el recreo, en coordenadas normalizadas
  `{"participant_id": 1, "x": 0.25, "y": 0.75}`. **Efímero**: se reenvía y no se persiste.
  El servidor descarta en silencio lo que llegue más rápido que un movimiento cada 110 ms,
  lo rechaza si el recreo está cerrado, y nunca lo encola.
- `participant.updated`: Alguien cambió su mascota o su color. Lleva el estado completo del
  participante, con la misma regla de privacidad que el resto.
- `room.recess_changed`: Se abrió o cerró el recreo. Al revelar se emite antes del
  `room.revealed`, y sólo si había un recreo abierto.
