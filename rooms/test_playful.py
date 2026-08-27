from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from rooms.models import Issue, Participant, PokerRoom
from rooms.playful import MAX_THROWS_PER_ROUND, THROWABLE_SLUGS
from rooms.services import (
    RoomActionError,
    activate_issue,
    cast_vote,
    reset_round,
    reveal_round,
    set_playful_actions,
    set_recess,
    throw_item,
)

User = get_user_model()


@pytest.mark.django_db
class TestThrowItem:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username='owner', password='pwd')
        self.stranger = User.objects.create_user(username='stranger', password='pwd')
        self.room = PokerRoom.objects.create(owner=self.owner, name='Table')
        self.issue = Issue.objects.create(room=self.room, title='Estimate this')
        self.alice = Participant.objects.create(
            room=self.room, user=self.owner, display_name='Alice', connection_count=1
        )
        self.bob = Participant.objects.create(
            room=self.room, display_name='Bob', connection_count=1
        )

    def test_a_throw_changes_nothing_about_the_round(self):
        cast_vote(self.room.id, self.bob.id, '8')
        throw_item(self.room.id, self.alice.id, self.bob.id, 'tomate')

        self.bob.refresh_from_db()
        self.room.refresh_from_db()
        assert self.bob.current_vote == '8'
        assert self.room.voting_status == 'voting'
        assert self.room.active_issue_id is None

    def test_every_catalogue_item_is_accepted(self):
        for item in THROWABLE_SLUGS:
            Participant.objects.filter(pk=self.alice.id).update(
                last_throw_at=None, throws_this_round=0
            )
            thrower, target = throw_item(self.room.id, self.alice.id, self.bob.id, item)
            assert thrower.id == self.alice.id
            assert target.id == self.bob.id

    def test_objects_outside_the_catalogue_are_refused(self):
        for item in ('ladrillo', 'cuchillo', '', 'TOMATE', 'tomate ', '<script>'):
            with pytest.raises(RoomActionError, match='no está en el catálogo'):
                throw_item(self.room.id, self.alice.id, self.bob.id, item)

    def test_cooldown_is_enforced_by_the_server(self):
        throw_item(self.room.id, self.alice.id, self.bob.id, 'papel')
        with pytest.raises(RoomActionError, match='un par de segundos'):
            throw_item(self.room.id, self.alice.id, self.bob.id, 'papel')

    def test_cooldown_expires(self):
        throw_item(self.room.id, self.alice.id, self.bob.id, 'papel')
        Participant.objects.filter(pk=self.alice.id).update(
            last_throw_at=timezone.now() - timedelta(seconds=10)
        )
        thrower, _ = throw_item(self.room.id, self.alice.id, self.bob.id, 'papel')
        assert thrower.throws_this_round == 2

    def test_per_round_cap_stops_a_food_fight(self):
        Participant.objects.filter(pk=self.alice.id).update(
            throws_this_round=MAX_THROWS_PER_ROUND
        )
        with pytest.raises(RoomActionError, match='suficiente en esta ronda'):
            throw_item(self.room.id, self.alice.id, self.bob.id, 'cafe')

    def test_the_round_budget_dies_with_the_round(self):
        """Nothing about the playful layer may accumulate across rounds."""
        Participant.objects.filter(pk=self.alice.id).update(
            throws_this_round=MAX_THROWS_PER_ROUND
        )
        reset_round(self.room.id, self.owner)
        self.alice.refresh_from_db()
        assert self.alice.throws_this_round == 0

        Participant.objects.filter(pk=self.alice.id).update(
            throws_this_round=MAX_THROWS_PER_ROUND
        )
        activate_issue(self.room.id, self.issue.id, self.owner)
        self.alice.refresh_from_db()
        assert self.alice.throws_this_round == 0

    def test_nobody_can_throw_at_themselves(self):
        with pytest.raises(RoomActionError, match='otra persona'):
            throw_item(self.room.id, self.alice.id, self.alice.id, 'tomate')

    def test_absent_people_cannot_be_targeted(self):
        Participant.objects.filter(pk=self.bob.id).update(connection_count=0)
        with pytest.raises(RoomActionError, match='no está en la mesa'):
            throw_item(self.room.id, self.alice.id, self.bob.id, 'tomate')

    def test_people_outside_the_room_are_not_reachable(self):
        other_room = PokerRoom.objects.create(owner=self.owner, name='Elsewhere')
        outsider = Participant.objects.create(
            room=other_room, display_name='Outsider', connection_count=1
        )
        with pytest.raises(Participant.DoesNotExist):
            throw_item(self.room.id, self.alice.id, outsider.id, 'tomate')

    def test_throwing_is_blind_to_whether_the_target_voted(self):
        """The same object, the same rules, voted or not: a throw can never be a
        signal about someone's card or their silence."""
        voted = throw_item(self.room.id, self.alice.id, self.bob.id, 'tomate')
        Participant.objects.filter(pk=self.alice.id).update(last_throw_at=None)
        cast_vote(self.room.id, self.bob.id, '5')
        after_voting = throw_item(self.room.id, self.alice.id, self.bob.id, 'tomate')
        assert voted[1].id == after_voting[1].id

    def test_it_still_works_after_the_reveal(self):
        cast_vote(self.room.id, self.bob.id, '8')
        reveal_round(self.room.id, self.owner)
        thrower, target = throw_item(self.room.id, self.alice.id, self.bob.id, 'sello')
        assert thrower.id == self.alice.id and target.id == self.bob.id

    def test_a_closed_room_refuses_throws(self):
        self.room.close_room()
        with pytest.raises(RoomActionError, match='cerrada'):
            throw_item(self.room.id, self.alice.id, self.bob.id, 'tomate')


@pytest.mark.django_db
class TestPlayfulSwitch:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username='owner', password='pwd')
        self.stranger = User.objects.create_user(username='stranger', password='pwd')
        self.room = PokerRoom.objects.create(owner=self.owner, name='Table')
        self.alice = Participant.objects.create(
            room=self.room, user=self.owner, display_name='Alice', connection_count=1
        )
        self.bob = Participant.objects.create(
            room=self.room, display_name='Bob', connection_count=1
        )

    def test_the_layer_is_on_by_default(self):
        assert self.room.allow_playful_actions is True

    def test_the_facilitator_can_turn_it_off_and_throws_stop(self):
        set_playful_actions(self.room.id, False, self.owner)
        with pytest.raises(RoomActionError, match='desactivó el juego'):
            throw_item(self.room.id, self.alice.id, self.bob.id, 'tomate')

        set_playful_actions(self.room.id, True, self.owner)
        thrower, _ = throw_item(self.room.id, self.alice.id, self.bob.id, 'tomate')
        assert thrower.id == self.alice.id

    def test_only_the_facilitator_can_flip_the_switch(self):
        with pytest.raises(RoomActionError, match='Sólo el facilitador'):
            set_playful_actions(self.room.id, False, self.stranger)

    def test_turning_it_off_does_not_touch_voting(self):
        cast_vote(self.room.id, self.bob.id, '3')
        set_playful_actions(self.room.id, False, self.owner)
        cast_vote(self.room.id, self.bob.id, '5')
        self.bob.refresh_from_db()
        assert self.bob.current_vote == '5'


@pytest.mark.django_db
class TestRecess:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username='owner', password='pwd')
        self.stranger = User.objects.create_user(username='stranger', password='pwd')
        self.room = PokerRoom.objects.create(owner=self.owner, name='Table')
        self.alice = Participant.objects.create(
            room=self.room, user=self.owner, display_name='Alice', connection_count=1
        )
        self.bob = Participant.objects.create(
            room=self.room, display_name='Bob', connection_count=1
        )

    def test_the_recess_starts_closed(self):
        assert self.room.recess_open is False

    def test_the_facilitator_opens_and_closes_it(self):
        assert set_recess(self.room.id, True, self.owner).recess_open is True
        assert set_recess(self.room.id, False, self.owner).recess_open is False

    def test_only_the_facilitator_decides(self):
        with pytest.raises(RoomActionError, match='Sólo el facilitador'):
            set_recess(self.room.id, True, self.stranger)

    def test_it_cannot_be_opened_once_the_votes_are_out(self):
        cast_vote(self.room.id, self.bob.id, '5')
        reveal_round(self.room.id, self.owner)
        with pytest.raises(RoomActionError, match='con la votación abierta'):
            set_recess(self.room.id, True, self.owner)

    def test_revealing_closes_it_by_itself(self):
        """The recess fills the wait for the last vote; the discussion replaces it."""
        set_recess(self.room.id, True, self.owner)
        cast_vote(self.room.id, self.bob.id, '5')
        reveal_round(self.room.id, self.owner)
        self.room.refresh_from_db()
        assert self.room.recess_open is False

    def test_it_can_always_be_closed_even_after_a_reveal(self):
        set_recess(self.room.id, True, self.owner)
        self.room.voting_status = 'revealed'
        self.room.save(update_fields=['voting_status'])
        assert set_recess(self.room.id, False, self.owner).recess_open is False

    def test_voting_keeps_working_during_the_recess(self):
        set_recess(self.room.id, True, self.owner)
        cast_vote(self.room.id, self.bob.id, '13')
        self.bob.refresh_from_db()
        assert self.bob.current_vote == '13'

    def test_a_closed_room_refuses_the_recess(self):
        self.room.close_room()
        with pytest.raises(RoomActionError, match='cerrada'):
            set_recess(self.room.id, True, self.owner)
