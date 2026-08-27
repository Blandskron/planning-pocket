"""Server-side business rules for a Planning Poker voting round."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .models import Issue, Participant, PokerRoom
from .playful import MAX_THROWS_PER_ROUND, THROW_COOLDOWN_SECONDS, THROWABLE_SLUGS


class RoomActionError(Exception):
    """Raised when an action is not valid for the room's current state."""


def _get_locked_room(room_id):
    return PokerRoom.objects.select_for_update().get(pk=room_id)


def _require_active_room(room):
    if room.status != "active":
        raise RoomActionError("This room is closed.")


def _require_facilitator(room, actor):
    if not actor or not actor.is_authenticated or actor.pk != room.owner_id:
        raise RoomActionError("Only the facilitator can perform this action.")


def _deck_values(room):
    return {value.strip() for value in room.deck.split(",") if value.strip()}


@transaction.atomic
def cast_vote(room_id, participant_id, value):
    """Store or retract a participant vote while the active round is open."""
    room = _get_locked_room(room_id)
    _require_active_room(room)

    if room.voting_status != "voting":
        raise RoomActionError("Votes are locked until the facilitator resets the round.")
    participant = Participant.objects.select_for_update().get(pk=participant_id, room=room)
    if value is not None and value not in _deck_values(room):
        raise RoomActionError("That value is not available in this deck.")

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
    Participant.objects.filter(room=room).update(current_vote=None, throws_this_round=0)
    return room


def calculate_results(room):
    """Return display-safe aggregate information for a revealed round."""
    votes = list(
        Participant.objects.filter(room=room)
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
        raise RoomActionError("This round has already been revealed.")
    room.voting_status = "revealed"
    room.save(update_fields=["voting_status"])
    return room, calculate_results(room)


@transaction.atomic
def activate_issue(room_id, issue_id, actor):
    """Make a pending issue the only active issue and start a fresh round."""
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    issue = Issue.objects.select_for_update().get(pk=issue_id, room=room)
    if issue.status == "estimated":
        raise RoomActionError("An estimated issue cannot be reactivated.")

    if room.active_issue_id and room.active_issue_id != issue.id:
        Issue.objects.filter(pk=room.active_issue_id).update(status="pending")

    room.active_issue = issue
    room.voting_status = "voting"
    room.save(update_fields=["active_issue", "voting_status"])
    issue.status = "active"
    issue.save(update_fields=["status"])
    Participant.objects.filter(room=room).update(current_vote=None, throws_this_round=0)
    return issue


@transaction.atomic
def finish_active_issue(room_id, final_result, actor):
    """Save a revealed estimate and close the active issue's round."""
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)

    if room.voting_status != "revealed":
        raise RoomActionError("Reveal the votes before saving an estimate.")
    if not room.active_issue_id:
        raise RoomActionError("There is no active issue to finish.")
    if final_result not in _deck_values(room):
        raise RoomActionError("The final estimate must be in this deck.")

    issue = Issue.objects.select_for_update().get(pk=room.active_issue_id)
    issue.final_result = final_result
    issue.status = "estimated"
    issue.save(update_fields=["final_result", "status"])

    room.active_issue = None
    room.voting_status = "voting"
    room.save(update_fields=["active_issue", "voting_status"])
    Participant.objects.filter(room=room).update(current_vote=None, throws_this_round=0)
    return issue


@transaction.atomic
def remind_participant(room_id, participant_id, actor):
    """Send a rate-limited, facilitator-only reminder to a pending participant."""
    room = _get_locked_room(room_id)
    _require_active_room(room)
    _require_facilitator(room, actor)
    if room.voting_status != "voting":
        raise RoomActionError("Reminders are available only while voting is open.")

    participant = Participant.objects.select_for_update().get(pk=participant_id, room=room)
    if participant.current_vote is not None:
        raise RoomActionError("This participant has already voted.")
    if participant.connection_count == 0:
        raise RoomActionError("This participant is not connected.")

    now = timezone.now()
    if participant.last_reminded_at and (now - participant.last_reminded_at).total_seconds() < 20:
        raise RoomActionError("Wait 20 seconds before sending another reminder.")

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
        raise RoomActionError("The facilitator turned off playful actions.")
    if item not in THROWABLE_SLUGS:
        raise RoomActionError("That object is not available.")
    if thrower_id == target_id:
        raise RoomActionError("Pick someone else at the table.")

    thrower = Participant.objects.select_for_update().get(pk=thrower_id, room=room)
    target = Participant.objects.select_for_update().get(pk=target_id, room=room)
    if target.connection_count == 0:
        raise RoomActionError("That person is not at the table right now.")

    now = timezone.now()
    if thrower.last_throw_at:
        elapsed = (now - thrower.last_throw_at).total_seconds()
        if elapsed < THROW_COOLDOWN_SECONDS:
            raise RoomActionError("Give it a couple of seconds before throwing again.")
    if thrower.throws_this_round >= MAX_THROWS_PER_ROUND:
        raise RoomActionError("That is enough throwing for this round.")

    thrower.last_throw_at = now
    thrower.throws_this_round += 1
    thrower.save(update_fields=["last_throw_at", "throws_this_round"])
    return thrower, target
