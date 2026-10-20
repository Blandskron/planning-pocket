"""Topes de la sala: cuántos caben y qué pasa cuando no cabe nadie más.

Una sala sin tope es una sala que cualquiera con el enlace puede llenar, y el coste no
crece con el número de participantes sino con su cuadrado: cada persona nueva recibe
todos los eventos de todas las demás.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from rooms.models import Participant, PokerRoom
from rooms.services import MAX_PARTICIPANTS, RoomFullError, require_free_seat

User = get_user_model()


@pytest.mark.django_db
class TestSeatCap:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username="owner", password="pwd-12345")
        self.room = PokerRoom.objects.create(owner=self.owner, name="Sala")

    def fill(self, count):
        base = Participant.objects.filter(room=self.room).count()
        Participant.objects.bulk_create([
            Participant(
                room=self.room,
                display_name=f"P{base + i}",
                guest_token=f"token-{self.room.pk}-{base + i}",
            )
            for i in range(count)
        ])

    def test_the_last_seat_is_still_a_seat(self):
        self.fill(MAX_PARTICIPANTS - 1)
        require_free_seat(self.room)  # no levanta

        self.fill(1)
        with pytest.raises(RoomFullError, match="llena"):
            require_free_seat(self.room)

    def test_an_expelled_participant_frees_their_seat(self):
        """La fila del expulsado se queda para sostener el veto, pero su asiento no."""
        self.fill(MAX_PARTICIPANTS)
        with pytest.raises(RoomFullError):
            require_free_seat(self.room)

        victim = self.room.active_participants.first()
        victim.removed_at = timezone.now()
        victim.save(update_fields=["removed_at"])

        require_free_seat(self.room)  # vuelve a haber hueco

    def test_a_guest_meets_a_door_instead_of_a_traceback(self, client):
        self.fill(MAX_PARTICIPANTS)
        url = f"/p/{self.room.public_id}/"

        response = client.post(url, {"display_name": "Tarde"})
        assert response.status_code == 200
        assert "rooms/room_full.html" in [t.name for t in response.templates]
        assert not Participant.objects.filter(display_name="Tarde").exists()

    def test_an_authenticated_newcomer_meets_the_same_door(self, client):
        self.fill(MAX_PARTICIPANTS)
        User.objects.create_user(username="tarde", password="pwd-12345")
        client.login(username="tarde", password="pwd-12345")

        response = client.get(f"/p/{self.room.public_id}/")
        assert "rooms/room_full.html" in [t.name for t in response.templates]
        assert not Participant.objects.filter(user__username="tarde").exists()

    def test_someone_already_seated_still_gets_in_when_the_room_is_full(self, client):
        """El tope es para entrar, no para volver: recargar no te puede echar."""
        url = f"/p/{self.room.public_id}/"
        client.post(url, {"display_name": "Puntual"})
        self.fill(MAX_PARTICIPANTS)

        response = client.get(url)
        assert "rooms/room_detail.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_closing_a_room_also_closes_the_recess():
    """Gente paseando por una sala cerrada es un estado que no debería existir."""
    owner = User.objects.create_user(username="owner", password="pwd-12345")
    room = PokerRoom.objects.create(owner=owner, name="Sala", recess_open=True)

    room.close_room()
    room.refresh_from_db()

    assert room.status == "closed"
    assert room.recess_open is False
