import pytest
from django.contrib.auth import get_user_model

from rooms.consumers import PokerConsumer
from rooms.forms import GuestJoinForm
from rooms.identity import COLOR_COUNT, FACE_SLUGS, PET_SLUGS, derive_identity
from rooms.models import Participant, PokerRoom
from rooms.services import RoomActionError, set_identity

User = get_user_model()


class TestDerivedIdentity:
    def test_derivation_is_stable_and_inside_the_closed_lists(self):
        for seed in ('abc', 'a3f9c1', '', None, 42):
            face, pet, color = derive_identity(seed)
            assert face in FACE_SLUGS
            assert pet in PET_SLUGS
            assert 0 <= color < COLOR_COUNT
            assert derive_identity(seed) == (face, pet, color)

    def test_different_seeds_spread_across_the_palette(self):
        colors = {derive_identity(f'token-{index}')[2] for index in range(200)}
        assert colors == set(range(COLOR_COUNT))


@pytest.mark.django_db
class TestParticipantIdentity:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username='owner', password='pwd')
        self.room = PokerRoom.objects.create(owner=self.owner, name='Table')

    def test_unset_identity_falls_back_to_a_stable_derivation(self):
        """Rows created before these fields existed still get a usable seat."""
        participant = Participant.objects.create(room=self.room, display_name='Legacy')
        identity = participant.identity
        assert identity['pet'] in PET_SLUGS
        assert identity['avatar'] in FACE_SLUGS
        assert 0 <= identity['color'] < COLOR_COUNT
        assert participant.identity == identity

    def test_stored_choices_win_over_the_derivation(self):
        participant = Participant.objects.create(
            room=self.room, display_name='Picked', pet='capibara', color_index=4
        )
        assert participant.identity['pet'] == 'capibara'
        assert participant.identity['color'] == 4

    def test_color_index_zero_is_respected_and_not_treated_as_unset(self):
        participant = Participant.objects.create(
            room=self.room, display_name='Zero', color_index=0
        )
        assert participant.identity['color'] == 0

    def test_broadcast_state_carries_identity_but_never_the_hidden_vote(self):
        participant = Participant.objects.create(
            room=self.room, display_name='Voter', pet='rana', color_index=2
        )
        participant.current_vote = '8'
        participant.save()

        self.room.voting_status = 'voting'
        state = PokerConsumer._participant_state(participant, self.room)
        assert state['pet'] == 'rana'
        assert state['color'] == 2
        assert state['avatar'] in FACE_SLUGS
        assert state['has_voted'] is True
        assert state['current_vote'] is None

        self.room.voting_status = 'revealed'
        revealed = PokerConsumer._participant_state(participant, self.room)
        assert revealed['current_vote'] == '8'
        assert revealed['pet'] == 'rana'


class TestGuestJoinForm:
    def test_identity_is_optional(self):
        form = GuestJoinForm(data={'display_name': 'Ana'})
        assert form.is_valid(), form.errors
        assert form.cleaned_data['pet'] == ''
        assert form.cleaned_data['color_index'] is None

    def test_valid_identity_is_coerced(self):
        form = GuestJoinForm(data={'display_name': 'Ana', 'pet': 'dragon', 'color_index': '5'})
        assert form.is_valid(), form.errors
        assert form.cleaned_data['pet'] == 'dragon'
        assert form.cleaned_data['color_index'] == 5

    @pytest.mark.parametrize(
        'payload',
        [
            {'pet': 'tiranosaurio'},
            {'color_index': '99'},
            {'color_index': '-1'},
            {'pet': '<script>'},
        ],
    )
    def test_values_outside_the_closed_lists_are_rejected(self, payload):
        form = GuestJoinForm(data={'display_name': 'Ana', **payload})
        assert not form.is_valid()


@pytest.mark.django_db
class TestChangingYourOwnIdentity:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username='owner', password='pwd')
        self.room = PokerRoom.objects.create(owner=self.owner, name='Table')
        self.me = Participant.objects.create(
            room=self.room, user=self.owner, display_name='Me', pet='gato', color_index=1
        )
        self.other = Participant.objects.create(room=self.room, display_name='Other')

    def test_changing_pet_and_colour(self):
        set_identity(self.room.id, self.me.id, 'dragon', 5)
        self.me.refresh_from_db()
        assert self.me.identity['pet'] == 'dragon'
        assert self.me.identity['color'] == 5

    def test_either_half_can_be_changed_alone(self):
        set_identity(self.room.id, self.me.id, 'rana', None)
        self.me.refresh_from_db()
        assert (self.me.pet, self.me.color_index) == ('rana', 1)

        set_identity(self.room.id, self.me.id, None, 0)
        self.me.refresh_from_db()
        assert (self.me.pet, self.me.color_index) == ('rana', 0)

    @pytest.mark.parametrize('pet,color', [
        ('tiranosaurio', None),
        ('', None),
        (None, 99),
        (None, -1),
        (None, COLOR_COUNT),
    ])
    def test_values_outside_the_closed_lists_are_refused(self, pet, color):
        with pytest.raises(RoomActionError):
            set_identity(self.room.id, self.me.id, pet, color)
        self.me.refresh_from_db()
        assert (self.me.pet, self.me.color_index) == ('gato', 1)

    def test_changing_identity_never_touches_a_vote(self):
        self.me.current_vote = '8'
        self.me.save(update_fields=['current_vote'])
        set_identity(self.room.id, self.me.id, 'perro', 3)
        self.me.refresh_from_db()
        assert self.me.current_vote == '8'

    def test_a_closed_room_refuses_the_change(self):
        self.room.close_room()
        with pytest.raises(RoomActionError, match='cerrada'):
            set_identity(self.room.id, self.me.id, 'perro', 3)
