import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model

from config.asgi import application
from rooms.consumers import PokerConsumer
from rooms.models import Issue, Participant, PokerRoom

User = get_user_model()


async def connect_participant(room, user):
    communicator = WebsocketCommunicator(PokerConsumer.as_asgi(), "/ws/test/")
    communicator.scope["url_route"] = {"kwargs": {"public_id": room.public_id}}
    communicator.scope["user"] = user
    connected, _ = await communicator.connect()
    assert connected
    state = await communicator.receive_json_from()
    assert state["type"] == "room.state"
    return communicator, state["payload"]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_websocket_state_hides_votes_before_reveal():
    owner = await sync_to_async(User.objects.create_user)(username="owner", password="pwd")
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name="WS room")
    issue = await sync_to_async(Issue.objects.create)(room=room, title="Estimate this")
    room.active_issue = issue
    await sync_to_async(room.save)(update_fields=["active_issue"])
    await sync_to_async(Issue.objects.filter(pk=issue.pk).update)(status="active")
    await sync_to_async(Participant.objects.create)(room=room, user=owner, display_name="Owner")
    guest = await sync_to_async(Participant.objects.create)(
        room=room, display_name="Guest", current_vote="8"
    )

    communicator, state = await connect_participant(room, owner)
    guest_state = next(item for item in state["participants"] if item["id"] == guest.id)
    assert guest_state == {
        "id": guest.id,
        "display_name": "Guest",
        "has_voted": True,
        "is_online": False,
        "current_vote": None,
    }

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_invalid_messages_return_an_error_without_closing_socket():
    owner = await sync_to_async(User.objects.create_user)(username="owner", password="pwd")
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name="WS room")
    await sync_to_async(Participant.objects.create)(room=room, user=owner, display_name="Owner")

    communicator, _ = await connect_participant(room, owner)
    await communicator.receive_json_from()  # participant.joined
    await communicator.send_to(text_data="not json")
    assert await communicator.receive_json_from() == {
        "type": "error",
        "code": "invalid_payload",
        "message": "The message must be valid JSON.",
    }

    await communicator.send_json_to({"type": "not.a.real.action"})
    assert (await communicator.receive_json_from())["code"] == "unknown_action"
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_multiple_tabs_keep_participant_present_until_last_disconnect():
    owner = await sync_to_async(User.objects.create_user)(username="owner", password="pwd")
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name="WS room")
    participant = await sync_to_async(Participant.objects.create)(
        room=room, user=owner, display_name="Owner"
    )

    first, _ = await connect_participant(room, owner)
    assert (await first.receive_json_from())["type"] == "participant.joined"
    second, _ = await connect_participant(room, owner)
    assert await first.receive_nothing(timeout=0.1)

    await second.disconnect()
    assert await first.receive_nothing(timeout=0.1)
    await sync_to_async(participant.refresh_from_db)()
    assert participant.connection_count == 1

    await first.disconnect()
    await sync_to_async(participant.refresh_from_db)()
    assert participant.connection_count == 0


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_reveal_returns_votes_only_after_the_facilitator_reveals():
    owner = await sync_to_async(User.objects.create_user)(username="owner", password="pwd")
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name="WS room")
    issue = await sync_to_async(Issue.objects.create)(
        room=room, title="Estimate this", status="active"
    )
    room.active_issue = issue
    await sync_to_async(room.save)(update_fields=["active_issue"])
    await sync_to_async(Participant.objects.create)(
        room=room, user=owner, display_name="Owner", current_vote="5"
    )
    guest = await sync_to_async(Participant.objects.create)(
        room=room, display_name="Guest", current_vote="8"
    )

    communicator, _ = await connect_participant(room, owner)
    state = await communicator.receive_json_from()
    assert state["type"] == "participant.joined"
    await communicator.send_json_to({"type": "room.reveal"})
    event = await communicator.receive_json_from()
    assert event["type"] == "room.revealed"
    assert {item["current_vote"] for item in event["participants"]} == {"5", "8"}
    assert event["results"]["average"] == 6.5
    assert event["results"]["vote_count"] == 2
    assert guest.id in {item["id"] for item in event["participants"]}

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_guest_cannot_reveal_and_receives_an_explicit_error():
    owner = await sync_to_async(User.objects.create_user)(username="owner", password="pwd")
    guest_user = await sync_to_async(User.objects.create_user)(username="guest", password="pwd")
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name="WS room")
    issue = await sync_to_async(Issue.objects.create)(
        room=room, title="Estimate this", status="active"
    )
    room.active_issue = issue
    await sync_to_async(room.save)(update_fields=["active_issue"])
    await sync_to_async(Participant.objects.create)(room=room, user=owner, display_name="Owner")
    await sync_to_async(Participant.objects.create)(
        room=room, user=guest_user, display_name="Guest"
    )

    communicator, _ = await connect_participant(room, guest_user)
    await communicator.receive_json_from()  # participant.joined
    await communicator.send_json_to({"type": "room.reveal"})
    error = await communicator.receive_json_from()
    assert error["type"] == "error"
    assert error["code"] == "invalid_action"

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_websocket_rejects_an_untrusted_origin():
    communicator = WebsocketCommunicator(
        application,
        "/ws/room/anything/",
        headers=[(b"origin", b"https://attacker.invalid")],
    )
    connected, _ = await communicator.connect()
    assert not connected
