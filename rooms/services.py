"""Server-side business rules for a Planning Poker voting round."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .models import Issue, Participant, PokerRoom


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
    if not room.active_issue_id:
        raise RoomActionError("Select an issue before voting.")

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
    Participant.objects.filter(room=room).update(current_vote=None)
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
        average = float(sum(numeric_votes) / len(numeric_votes))

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
    if not room.active_issue_id:
        raise RoomActionError("Select an issue before revealing votes.")

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
    Participant.objects.filter(room=room).update(current_vote=None)
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
    Participant.objects.filter(room=room).update(current_vote=None)
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
