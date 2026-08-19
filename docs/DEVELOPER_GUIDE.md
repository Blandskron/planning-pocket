# Planning Pocket - Developer Guide

Welcome to the internal developer documentation for Planning Pocket. This guide explains the core architectural decisions, data flow, and conventions used throughout the repository.

## 1. Architectural Philosophy

Planning Pocket is built strictly on the **"Server as the Source of Truth"** principle.
Unlike modern SPAs (Single Page Applications) that rely heavily on client-side state management (e.g., Redux, Vuex), this application maintains a completely stateless client.
All critical logic, privacy checks, and state transitions are handled exclusively by the Django backend.

### Key Decisions
- **No JS Frameworks**: The frontend uses native Vanilla JS and standard HTML5/CSS3. This guarantees lightning-fast load times, zero build steps, and extreme simplicity.
- **WebSocket Driven**: Real-time interactivity is powered by Django Channels (`daphne` as the ASGI server).
- **Privacy by Design**: Vote values are structurally hidden. The backend *never* transmits a participant's vote payload to other clients until the facilitator explicitly triggers a reveal event.

## 2. Core Domain Models (`rooms/models.py`)

- `PokerRoom`: The central entity. Holds the `public_id` (a secure URL token) and the global `voting_status` (`voting` or `revealed`).
- `Participant`: Represents a physical user in a room. Supports both authenticated `User` instances (facilitators/registered users) and anonymous guests (tracked via `guest_token` securely stored in their HTTP session).
- `Issue`: Represents a task or user story. Rooms can have an `active_issue` that focuses the team. Once estimated, the result is saved here.

## 3. Data Flow & WebSockets (`rooms/consumers.py`)

The `PokerConsumer` is the heart of the real-time application.

### Connection Lifecycle
1. **Connect**: The browser establishes a WebSocket connection to `ws/room/<public_id>/`.
2. **Authentication**: The consumer reads the Django session to identify if the connection belongs to the Owner, a registered User, or a Guest (using `guest_tokens` map).
3. **Join Event**: The consumer joins a channel group (`room_<public_id>`) and broadcasts `participant.joined`.
4. **Disconnect**: On socket close, it broadcasts `participant.left`.

### Event Dispatcher
The `receive` method handles incoming JSON payloads via `event_type`.
Security is enforced here:
- **Guest Actions**: Guests can only send `vote.cast` events.
- **Facilitator Actions**: Only the room owner (verified via `await self.is_room_owner()`) can send `room.reveal`, `room.reset`, `issue.activate`, and `issue.finish`.

### Privacy Enforcement
The method `_get_participant_state_sync()` applies the critical privacy rule:
```python
if room.voting_status == 'revealed':
    state['current_vote'] = participant.current_vote
else:
    state['current_vote'] = None
```
This guarantees that clients (and malicious users inspecting network traffic) cannot access votes prematurely.

## 4. Testing Strategy

The repository follows a test-first approach for critical rules:
- **`pytest` & `pytest-django`**: Used to execute tests.
- **Unit Tests**: Ensure model methods (`reset_voting`, `close_room`) update states properly.
- **Integration Tests**: Verify HTTP view logic, session injections, and URL security.
- **WebSocket Tests**: Built using `channels.testing.WebsocketCommunicator`. These tests simulate the ASGI protocol directly, ensuring that JSON payloads are correctly formed and privacy filters work during active voting rounds.

## 5. UI/UX Guidelines

- **CSS Variables**: Global themes are managed in `static/css/style.css` using `:root` variables (e.g., `--primary`, `--bg-color`).
- **Responsive Layout**: Utilizing CSS Grid and Flexbox. The application gracefully degrades on mobile.
- **Heuristics Applied**: 
  - *Feedback*: Modals/Toasts (`showToast`) appear on WS events. Buttons disable themselves on submit.
  - *Freedom*: Clicking an already selected card sends a `null` vote, allowing users to "re-think".

## 6. Deployment (Docker)

The project ships with a `Dockerfile` and `docker-compose.yml` for isolated production.
- **PostgreSQL**: Used as the primary relational database.
- **Redis**: Used as the backbone for `channels_redis`, allowing multi-worker broadcasting.
- **Daphne**: Runs the ASGI application on port 8000.

**To deploy locally:**
```bash
docker-compose up --build -d
```
