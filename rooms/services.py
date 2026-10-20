"""Server-side business rules for a Planning Poker voting round."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .decks import FULL_DECK_VALUE, SHORT_DECK_VALUE, deck_values
from .identity import COLOR_COUNT, PET_SLUGS
from .models import Issue, Participant, PokerRoom
from .playful import MAX_THROWS_PER_ROUND, THROW_COOLDOWN_SECONDS, THROWABLE_SLUGS


class RoomActionError(Exception):
    """Raised when an action is not valid for the room's current state."""


class RoomFullError(RoomActionError):
    """Raised when a room has no seats left."""


# Una sala sin tope es una sala que cualquiera con el enlace puede llenar: cada
# participante nuevo multiplica el reparto de todos los eventos de la sala, así que el
# coste no crece con N sino con N². Treinta asientos están muy por encima de cualquier
# equipo que estime junto y muy por debajo de lo que duele.
MAX_PARTICIPANTS = 30


def room_has_a_free_seat(room):
    return room.active_participants.count() < MAX_PARTICIPANTS


def require_free_seat(room):
    if not room_has_a_free_seat(room):
        raise RoomFullError("Esta sala está llena.")


def _get_locked_room(room_id):
    return PokerRoom.objects.select_for_update().get(pk=room_id)


def _require_active_room(room):
    if room.status != "active":
        raise RoomActionError("Esta sala está cerrada.")


def _require_facilitator(room, actor):
    if not actor or not actor.is_authenticated or actor.pk != room.owner_id:
        raise RoomActionError("Sólo el facilitador puede hacer esto.")


def _deck_values(room):
    return set(deck_values(room.deck))


def _get_seated(room, participant_id):
    """Trae a alguien que sigue en la mesa, o se niega.

    Expulsar no borra la fila, así que una consulta por ``pk`` encuentra igualmente
    al expulsado. Todo lo que actúe sobre un participante pasa por aquí: sin esto,
    el socket que esa persona ya tenía abierto podría seguir votando después del
    veto, y el veto no sería tal.
    """
    participant = Participant.objects.select_for_update().get(pk=participant_id, room=room)
    if participant.removed_at is not None:
        raise RoomActionError("Esa persona ya no está en la sala.")
    return participant


@transaction.atomic
def cast_vote(room_id, participant_id, value):
    """Store or retract a participant vote while the active round is open."""
    room = _get_locked_room(room_id)
    _require_active_room(room)

    if room.voting_status != "voting":
        raise RoomActionError(
            "Los votos están cerrados hasta que el facilitador inicie una nueva ronda."
        )
    participant = _get_seated(room, participant_id)
    if value is not None and value not in _deck_values(room):
        raise RoomActionError("Esa carta no está en la baraja de esta sala.")

    participant.current_vote = value
    participant.save(update_fields=["current_vote"])
    return participant


@transaction.atomic
def reset_round(room_id, actor):
    """Clear all votes and reopen the current round for the facilitator."""
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    room.voting_status = "voting"
    room.save(update_fields=["voting_status"])
    room.active_participants.update(current_vote=None, throws_this_round=0)
    return room


def calculate_results(room):
    """Return display-safe aggregate information for a revealed round."""
    votes = list(
        room.active_participants
        .exclude(current_vote__isnull=True)
        .values_list("current_vote", flat=True)
    )
    numeric_votes = []
    for vote in votes:
        try:
            numeric_votes.append(Decimal(vote))
        except (InvalidOperation, TypeError):
            continue

    average = None
    if numeric_votes:
        # Rounded here because this value is rendered verbatim: an unrounded
        # Decimal division reaches the table as 1.6666666666666667.
        average = round(float(sum(numeric_votes) / len(numeric_votes)), 1)

    return {
        "vote_count": len(votes),
        "numeric_vote_count": len(numeric_votes),
        "average": average,
        "has_consensus": len(votes) > 0 and len(set(votes)) == 1,
    }


@transaction.atomic
def reveal_round(room_id, actor):
    """Lock the active round and return its aggregate results."""
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    if room.voting_status != "voting":
        raise RoomActionError("Esta ronda ya está revelada.")
    room.voting_status = "revealed"
    # The recess exists to fill the wait for the last vote. Once the cards are on
    # the table the discussion is the point, so it closes itself.
    room.recess_open = False
    room.save(update_fields=["voting_status", "recess_open"])
    return room, calculate_results(room)


@transaction.atomic
def activate_issue(room_id, issue_id, actor):
    """Make a pending issue the only active issue and start a fresh round."""
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    issue = Issue.objects.select_for_update().get(pk=issue_id, room=room)
    if issue.status == "estimated":
        raise RoomActionError("Una historia ya estimada no se puede reabrir.")

    if room.active_issue_id and room.active_issue_id != issue.id:
        Issue.objects.filter(pk=room.active_issue_id).update(status="pending")

    room.active_issue = issue
    room.voting_status = "voting"
    room.save(update_fields=["active_issue", "voting_status"])
    issue.status = "active"
    issue.save(update_fields=["status"])
    room.active_participants.update(current_vote=None, throws_this_round=0)
    return issue


@transaction.atomic
def finish_active_issue(room_id, final_result, actor):
    """Save a revealed estimate and close the active issue's round."""
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    if room.voting_status != "revealed":
        raise RoomActionError("Revela los votos antes de guardar la estimación.")
    if not room.active_issue_id:
        raise RoomActionError("No hay ninguna historia en estimación.")
    if final_result not in _deck_values(room):
        raise RoomActionError("La estimación final tiene que ser una carta de la baraja.")

    issue = Issue.objects.select_for_update().get(pk=room.active_issue_id)
    issue.final_result = final_result
    issue.status = "estimated"
    issue.save(update_fields=["final_result", "status"])

    room.active_issue = None
    room.voting_status = "voting"
    room.save(update_fields=["active_issue", "voting_status"])
    room.active_participants.update(current_vote=None, throws_this_round=0)
    return issue


@transaction.atomic
def remind_participant(room_id, participant_id, actor):
    """Send a rate-limited, facilitator-only reminder to a pending participant."""
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)
    if room.voting_status != "voting":
        raise RoomActionError("Los recordatorios sólo funcionan con la votación abierta.")

    participant = _get_seated(room, participant_id)
    if participant.current_vote is not None:
        raise RoomActionError("Esta persona ya votó.")
    if participant.connection_count == 0:
        raise RoomActionError("Esta persona no está conectada.")

    now = timezone.now()
    if participant.last_reminded_at and (now - participant.last_reminded_at).total_seconds() < 20:
        raise RoomActionError("Espera 20 segundos antes de recordárselo otra vez.")

    participant.last_reminded_at = now
    participant.save(update_fields=["last_reminded_at"])
    return participant


@transaction.atomic
def set_playful_actions(room_id, enabled, actor):
    """Turn the playful layer on or off for the whole room."""
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    room.allow_playful_actions = bool(enabled)
    room.save(update_fields=["allow_playful_actions"])
    return room


@transaction.atomic
def throw_item(room_id, thrower_id, target_id, item):
    """Register a cosmetic throw from one participant at another.

    Nothing about the round changes here. The server owns the limits because the
    browser must not be able to grant itself a faster arm, and the checks are
    deliberately blind to whether anyone has voted: a throw must never become a way
    to single out the person the table is waiting for.
    """
    room = _get_locked_room(room_id)
    _require_active_room(room)

    if not room.allow_playful_actions:
        raise RoomActionError("El facilitador desactivó el juego en esta sala.")
    if item not in THROWABLE_SLUGS:
        raise RoomActionError("Ese objeto no está en el catálogo.")
    if thrower_id == target_id:
        raise RoomActionError("Elige a otra persona de la mesa.")

    thrower = _get_seated(room, thrower_id)
    target = _get_seated(room, target_id)
    if target.connection_count == 0:
        raise RoomActionError("Esa persona no está en la mesa ahora mismo.")

    now = timezone.now()
    if thrower.last_throw_at:
        elapsed = (now - thrower.last_throw_at).total_seconds()
        if elapsed < THROW_COOLDOWN_SECONDS:
            raise RoomActionError("Espera un par de segundos antes de lanzar otra vez.")
    if thrower.throws_this_round >= MAX_THROWS_PER_ROUND:
        raise RoomActionError("Ya has lanzado suficiente en esta ronda.")

    thrower.last_throw_at = now
    thrower.throws_this_round += 1
    thrower.save(update_fields=["last_throw_at", "throws_this_round"])
    return thrower, target


@transaction.atomic
def set_deck(room_id, expanded, actor):
    """Alterna la sala entre la baraja corta y la completa.

    Sólo con la votación abierta: cambiarla con las cartas sobre la mesa reescribe
    un resultado que la gente ya está discutiendo.

    Al encoger se retiran los votos cuya carta deja de existir. La alternativa
    —dejarlos— produce una mesa donde al revelar aparece un 55 que ya no se puede
    elegir y que el promedio sigue contando: un número que nadie puede reproducir.
    """
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    if room.voting_status != "voting":
        raise RoomActionError("La baraja sólo se cambia con la votación abierta.")

    room.deck = FULL_DECK_VALUE if expanded else SHORT_DECK_VALUE
    room.save(update_fields=["deck"])
    room.active_participants.exclude(current_vote__isnull=True).exclude(
        current_vote__in=_deck_values(room)
    ).update(current_vote=None)
    return room


@transaction.atomic
def remove_participant(room_id, participant_id, actor):
    """Saca a alguien de la sala, para siempre en lo que dure la sala.

    La fila no se borra y ahí está la gracia: guarda el ``guest_token`` —o el
    usuario— con el que esa persona volvería a entrar, así que es el propio registro
    el que sostiene el veto. Borrarla dejaría que volviese con el mismo enlace diez
    segundos después, que es exactamente no haber expulsado a nadie.

    Se retira el voto además del asiento: si se quedara, la mesa esperaría para
    siempre a alguien que ya no está, y el promedio contaría su carta.
    """
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    participant = _get_seated(room, participant_id)
    if participant.user_id and participant.user_id == room.owner_id:
        raise RoomActionError("No puedes expulsarte a ti: la sala se quedaría sin facilitador.")

    participant.removed_at = timezone.now()
    participant.current_vote = None
    participant.connection_count = 0
    participant.save(update_fields=["removed_at", "current_vote", "connection_count"])
    return participant


@transaction.atomic
def set_recess(room_id, enabled, actor):
    """Open or close the recess, where people can leave their seats.

    Only the facilitator decides, and it can only be opened while voting is still
    open: once the votes are revealed the table should be talking, not wandering.
    """
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    if enabled and room.voting_status != "voting":
        raise RoomActionError("El recreo sólo se puede abrir con la votación abierta.")

    room.recess_open = bool(enabled)
    room.save(update_fields=["recess_open"])
    return room


@transaction.atomic
def set_identity(room_id, participant_id, pet, color_index):
    """Let someone change how their own seat is drawn.

    Cosmetic only, and only your own seat: nobody can restyle anyone else. Guests
    pick on the way in, but authenticated participants never see that screen, so
    this is the path that works for everybody.
    """
    room = _get_locked_room(room_id)
    _require_active_room(room)

    participant = _get_seated(room, participant_id)
    if pet is not None:
        if pet not in PET_SLUGS:
            raise RoomActionError("Esa mascota no está en la lista.")
        participant.pet = pet
    if color_index is not None:
        if not isinstance(color_index, int) or not 0 <= color_index < COLOR_COUNT:
            raise RoomActionError("Ese color no está en la paleta.")
        participant.color_index = color_index

    participant.save(update_fields=["pet", "color_index"])
    return participant
