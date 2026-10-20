"""Las dos reglas que el facilitador ejerce sobre la sala: la baraja y expulsar.

Ambas son autorización, así que se escriben primero y el servidor las decide. Lo que
se protege aquí no es que el botón exista, sino que exista *sólo* para quien manda y
que lo que deja detrás sea coherente: ni votos de cartas que ya no están en la mesa,
ni expulsados que vuelven a entrar con el mismo enlace.
"""

import pytest
from django.contrib.auth import get_user_model

from rooms.decks import FULL_DECK_VALUE, SHORT_DECK, SHORT_DECK_VALUE
from rooms.models import Participant, PokerRoom
from rooms.services import (
    RoomActionError,
    calculate_results,
    cast_vote,
    remove_participant,
    reveal_round,
    set_deck,
)

User = get_user_model()


@pytest.mark.django_db
class TestDeck:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username="owner", password="pwd")
        self.intruder = User.objects.create_user(username="intruder", password="pwd")
        self.room = PokerRoom.objects.create(owner=self.owner, name="Sala")
        self.guest = Participant.objects.create(room=self.room, display_name="Invitada")

    def test_a_new_room_deals_eight_cards(self):
        assert self.room.deck == SHORT_DECK_VALUE
        assert len(SHORT_DECK) == 8
        assert "21" not in SHORT_DECK and "Coffee" not in SHORT_DECK

    def test_only_the_facilitator_moves_between_the_two_decks(self):
        with pytest.raises(RoomActionError, match="Sólo el facilitador"):
            set_deck(self.room.id, True, self.intruder)
        with pytest.raises(RoomActionError, match="Sólo el facilitador"):
            set_deck(self.room.id, True, None)

        room = set_deck(self.room.id, True, self.owner)
        assert room.deck == FULL_DECK_VALUE

    def test_the_long_deck_unlocks_the_cards_the_short_one_refuses(self):
        with pytest.raises(RoomActionError, match="no está en la baraja"):
            cast_vote(self.room.id, self.guest.id, "55")

        set_deck(self.room.id, True, self.owner)
        cast_vote(self.room.id, self.guest.id, "55")
        self.guest.refresh_from_db()
        assert self.guest.current_vote == "55"

    def test_shrinking_the_deck_takes_back_the_votes_it_no_longer_holds(self):
        """Un voto de una carta que ya no está en la mesa es un voto que nadie puede
        verificar: al revelar aparecería un 55 que no se puede volver a elegir, y el
        promedio lo contaría. Se retira, y quien lo tenía vuelve a votar."""
        set_deck(self.room.id, True, self.owner)
        keeper = Participant.objects.create(room=self.room, display_name="Se queda")
        cast_vote(self.room.id, self.guest.id, "55")
        cast_vote(self.room.id, keeper.id, "8")

        room = set_deck(self.room.id, False, self.owner)

        self.guest.refresh_from_db()
        keeper.refresh_from_db()
        assert room.deck == SHORT_DECK_VALUE
        assert self.guest.current_vote is None, "el 55 sobrevivió a la baraja que lo contenía"
        assert keeper.current_vote == "8", "un voto que sigue en la baraja no se toca"

    def test_the_deck_does_not_change_under_a_revealed_round(self):
        """Cambiarla con las cartas sobre la mesa reescribe un resultado que la gente
        ya está discutiendo."""
        cast_vote(self.room.id, self.guest.id, "8")
        reveal_round(self.room.id, self.owner)

        with pytest.raises(RoomActionError, match="votación abierta"):
            set_deck(self.room.id, True, self.owner)

    def test_the_deck_does_not_change_in_a_closed_room(self):
        self.room.close_room()
        with pytest.raises(RoomActionError, match="cerrada"):
            set_deck(self.room.id, True, self.owner)


@pytest.mark.django_db
class TestRemoval:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username="owner", password="pwd")
        self.intruder = User.objects.create_user(username="intruder", password="pwd")
        self.room = PokerRoom.objects.create(owner=self.owner, name="Sala")
        self.me = Participant.objects.create(
            room=self.room, user=self.owner, display_name="Facilitador"
        )
        self.guest = Participant.objects.create(room=self.room, display_name="Invitada")

    def test_only_the_facilitator_removes_anyone(self):
        with pytest.raises(RoomActionError, match="Sólo el facilitador"):
            remove_participant(self.room.id, self.guest.id, self.intruder)
        with pytest.raises(RoomActionError, match="Sólo el facilitador"):
            remove_participant(self.room.id, self.guest.id, None)

        self.guest.refresh_from_db()
        assert self.guest.removed_at is None

    def test_the_facilitator_cannot_remove_themselves(self):
        """Una sala sin facilitador no la puede reabrir nadie."""
        with pytest.raises(RoomActionError, match="a ti"):
            remove_participant(self.room.id, self.me.id, self.owner)

    def test_removing_takes_the_seat_the_vote_and_the_connection(self):
        cast_vote(self.room.id, self.guest.id, "8")
        self.guest.connection_count = 2
        self.guest.save(update_fields=["connection_count"])

        removed = remove_participant(self.room.id, self.guest.id, self.owner)

        assert removed.removed_at is not None
        assert removed.current_vote is None, "el voto del expulsado seguía contando"
        assert removed.connection_count == 0
        assert self.guest.id not in {p.id for p in self.room.active_participants}

    def test_an_expelled_seat_leaves_the_table_arithmetic(self):
        """Si siguiera contando, la mesa esperaría para siempre un voto que no llega."""
        cast_vote(self.room.id, self.me.id, "5")
        cast_vote(self.room.id, self.guest.id, "13")
        assert calculate_results(self.room)["vote_count"] == 2

        remove_participant(self.room.id, self.guest.id, self.owner)
        assert calculate_results(self.room)["vote_count"] == 1

    def test_removing_twice_is_refused_instead_of_silently_repeated(self):
        remove_participant(self.room.id, self.guest.id, self.owner)
        with pytest.raises(RoomActionError, match="ya no está"):
            remove_participant(self.room.id, self.guest.id, self.owner)

    def test_an_expelled_participant_cannot_act_on_the_room_any_more(self):
        """El veto no sirve de nada si el socket que ya tenía abierto sigue votando."""
        remove_participant(self.room.id, self.guest.id, self.owner)
        with pytest.raises(RoomActionError, match="ya no está"):
            cast_vote(self.room.id, self.guest.id, "8")

    def test_nobody_is_removed_from_a_closed_room(self):
        self.room.close_room()
        with pytest.raises(RoomActionError, match="cerrada"):
            remove_participant(self.room.id, self.guest.id, self.owner)


@pytest.mark.django_db
class TestRemovedParticipantAtTheDoor:
    """El veto no sirve de nada si la puerta HTTP lo ignora: el cliente recarga la
    página en cuanto se le cierra el socket, y ahí es donde se decide si vuelve."""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username="owner", password="pwd-12345")
        self.room = PokerRoom.objects.create(owner=self.owner, name="Sala")
        Participant.objects.create(room=self.room, user=self.owner, display_name="Facilitador")

    def test_an_expelled_guest_gets_a_door_not_the_table(self, client):
        url = f"/p/{self.room.public_id}/"
        client.post(url, {"display_name": "Invitada"})
        guest = Participant.objects.get(room=self.room, display_name="Invitada")

        assert client.get(url).status_code == 200
        remove_participant(self.room.id, guest.id, self.owner)

        response = client.get(url)
        assert response.status_code == 200
        assert "rooms/room_removed.html" in [t.name for t in response.templates]
        # No es «la sala cerró»: la sala sigue abierta y el resto sigue dentro.
        assert "rooms/room_closed.html" not in [t.name for t in response.templates]

    def test_an_expelled_user_cannot_be_recreated_by_the_get_or_create(self, client):
        """La vista hace ``get_or_create`` por usuario. Sin la comprobación, encuentra
        la fila expulsada y la sirve como si nada."""
        member = User.objects.create_user(username="member", password="pwd-12345")
        participant = Participant.objects.create(
            room=self.room, user=member, display_name="member"
        )
        remove_participant(self.room.id, participant.id, self.owner)

        client.login(username="member", password="pwd-12345")
        response = client.get(f"/p/{self.room.public_id}/")
        assert "rooms/room_removed.html" in [t.name for t in response.templates]

    def test_the_table_stops_drawing_the_empty_seat(self, client):
        url = f"/p/{self.room.public_id}/"
        client.post(url, {"display_name": "Invitada"})
        guest = Participant.objects.get(room=self.room, display_name="Invitada")
        remove_participant(self.room.id, guest.id, self.owner)

        client.login(username="owner", password="pwd-12345")
        response = client.get(url)
        assert b"Invitada" not in response.content, "el asiento del expulsado seguía dibujado"

    def test_the_room_deals_the_short_deck_to_the_page(self, client):
        client.login(username="owner", password="pwd-12345")
        response = client.get(f"/p/{self.room.public_id}/")
        assert list(response.context["deck_cards"]) == list(SHORT_DECK)
        assert response.context["deck_expanded"] is False
