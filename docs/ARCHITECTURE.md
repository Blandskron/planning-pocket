# Arquitectura de Planning Pocket

## 1. Visión General
El sistema sigue una arquitectura monolítica modular basada en Django, donde el servidor es la fuente de verdad (Server-Side Authority). Se utiliza Django Channels y Redis para mantener sincronizados a los participantes de la sala en tiempo real.

## 2. Aplicaciones (Módulos)
El proyecto se dividirá en las siguientes aplicaciones Django para separar responsabilidades:

- **`accounts`**: Gestión de usuarios autenticados, registro, login y sesiones.
- **`rooms`**: Gestión de las salas de Planning Poker, creación, configuración, enlaces públicos (public_id) y control de acceso (incluyendo identidades de invitados).
- **`poker`**: Núcleo del negocio. Contiene la lógica de Issues, VotingRounds, Votes y la máquina de estados.

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
