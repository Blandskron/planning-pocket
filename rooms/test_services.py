import pytest
from django.contrib.auth import get_user_model

from rooms.models import Issue, Participant, PokerRoom
from rooms.services import (
    RoomActionError,
    activate_issue,
    calculate_results,
    cast_vote,
    finish_active_issue,
    reset_round,
    reveal_round,
)

User = get_user_model()


@pytest.mark.django_db
class TestVotingRoundService:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username="owner", password="pwd")
        self.other_user = User.objects.create_user(username="other", password="pwd")
        self.room = PokerRoom.objects.create(owner=self.owner, name="Test room")
        self.owner_participant = Participant.objects.create(
            room=self.room, user=self.owner, display_name="Owner"
        )
        self.guest = Participant.objects.create(room=self.room, display_name="Guest")
        self.issue = Issue.objects.create(room=self.room, title="Estimate this")

    def test_votes_require_an_active_issue_and_deck_value(self):
        with pytest.raises(RoomActionError, match="Select an issue"):
            cast_vote(self.room.id, self.guest.id, "5")

        activate_issue(self.room.id, self.issue.id, self.owner)
        cast_vote(self.room.id, self.guest.id, "5")
        self.guest.refresh_from_db()
        assert self.guest.current_vote == "5"

        with pytest.raises(RoomActionError, match="not available"):
            cast_vote(self.room.id, self.guest.id, "999")

    def test_reveal_locks_votes_and_returns_results(self):
        activate_issue(self.room.id, self.issue.id, self.owner)
        cast_vote(self.room.id, self.owner_participant.id, "5")
        cast_vote(self.room.id, self.guest.id, "?")

        room, results = reveal_round(self.room.id, self.owner)
        assert room.voting_status == "revealed"
        assert results == {
            "vote_count": 2,
            "numeric_vote_count": 1,
            "average": 5.0,
            "has_consensus": False,
        }

        with pytest.raises(RoomActionError, match="locked"):
            cast_vote(self.room.id, self.guest.id, "8")

    def test_only_facilitator_can_control_the_round(self):
        activate_issue(self.room.id, self.issue.id, self.owner)

        with pytest.raises(RoomActionError, match="Only the facilitator"):
            reveal_round(self.room.id, self.other_user)

        with pytest.raises(RoomActionError, match="Only the facilitator"):
            reset_round(self.room.id, self.other_user)

    def test_switching_issues_resets_votes_and_previous_issue(self):
        next_issue = Issue.objects.create(room=self.room, title="Second issue")
        activate_issue(self.room.id, self.issue.id, self.owner)
        cast_vote(self.room.id, self.guest.id, "3")

        activate_issue(self.room.id, next_issue.id, self.owner)

        self.room.refresh_from_db()
        self.issue.refresh_from_db()
        next_issue.refresh_from_db()
        self.guest.refresh_from_db()
        assert self.room.active_issue == next_issue
        assert self.issue.status == "pending"
        assert next_issue.status == "active"
        assert self.guest.current_vote is None

    def test_finish_requires_reveal_and_a_deck_value(self):
        activate_issue(self.room.id, self.issue.id, self.owner)
        with pytest.raises(RoomActionError, match="Reveal the votes"):
            finish_active_issue(self.room.id, "5", self.owner)

        reveal_round(self.room.id, self.owner)
        with pytest.raises(RoomActionError, match="must be in this deck"):
            finish_active_issue(self.room.id, "999", self.owner)

        finish_active_issue(self.room.id, "5", self.owner)
        self.room.refresh_from_db()
        self.issue.refresh_from_db()
        assert self.room.active_issue is None
        assert self.issue.status == "estimated"
        assert self.issue.final_result == "5"

    def test_results_report_consensus(self):
        activate_issue(self.room.id, self.issue.id, self.owner)
        cast_vote(self.room.id, self.owner_participant.id, "8")
        cast_vote(self.room.id, self.guest.id, "8")

        assert calculate_results(self.room) == {
            "vote_count": 2,
            "numeric_vote_count": 2,
            "average": 8.0,
            "has_consensus": True,
        }
