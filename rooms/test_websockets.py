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


async def wait_for(communicator, event_type, tries=6):
    """Return the next event of a given type, skipping whatever else arrives."""
    for _ in range(tries):
        event = await communicator.receive_json_from()
        if event.get("type") == event_type:
            return event
    raise AssertionError(f"no {event_type} event arrived")


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
    # Exact equality on purpose: it fails the moment any unexpected key reaches a
    # client. Cosmetic identity is listed explicitly because it is not a secret.
    assert guest_state == {
        "id": guest.id,
        "display_name": "Guest",
        "has_voted": True,
        "is_online": False,
        "current_vote": None,
        **guest.identity,
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
@pytest.mark.django_db(transaction=True)
async def test_facilitator_can_remind_a_connected_participant_who_has_not_voted():
    owner = await sync_to_async(User.objects.create_user)(username="owner", password="pwd")
    guest_user = await sync_to_async(User.objects.create_user)(username="guest", password="pwd")
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name="WS room")
    issue = await sync_to_async(Issue.objects.create)(
        room=room, title="Estimate this", status="active"
    )
    room.active_issue = issue
    await sync_to_async(room.save)(update_fields=["active_issue"])
    await sync_to_async(Participant.objects.create)(room=room, user=owner, display_name="Owner")
    guest = await sync_to_async(Participant.objects.create)(
        room=room, user=guest_user, display_name="Guest"
    )

    owner_socket, _ = await connect_participant(room, owner)
    await owner_socket.receive_json_from()  # owner joined
    guest_socket, _ = await connect_participant(room, guest_user)
    await owner_socket.receive_json_from()  # guest joined
    await guest_socket.receive_json_from()  # guest joined

    await owner_socket.send_json_to(
        {"type": "participant.remind", "participant_id": guest.id}
    )
    owner_event = await owner_socket.receive_json_from()
    guest_event = await guest_socket.receive_json_from()
    assert owner_event == guest_event == {
        "type": "participant.reminded",
        "participant_id": guest.id,
    }

    await owner_socket.disconnect()
    await guest_socket.disconnect()


@pytest.mark.asyncio
async def test_websocket_rejects_an_untrusted_origin():
    communicator = WebsocketCommunicator(
        application,
        "/ws/room/anything/",
        headers=[(b"origin", b"https://attacker.invalid")],
    )
    connected, _ = await communicator.connect()
    assert not connected


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_throw_broadcast_carries_no_vote_information():
    """The playful layer must never become a side channel for the hidden vote."""
    owner = await sync_to_async(User.objects.create_user)(username="owner", password="pwd")
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name="WS room")
    thrower = await sync_to_async(Participant.objects.create)(
        room=room, user=owner, display_name="Thrower"
    )
    target = await sync_to_async(Participant.objects.create)(
        room=room, display_name="Target", current_vote="13", connection_count=1
    )

    communicator, _ = await connect_participant(room, owner)
    await communicator.send_json_to(
        {"type": "player.throw", "target_id": target.id, "item": "tomate"}
    )
    event = await wait_for(communicator, "player.hit")

    # Exact equality: the payload is the whole contract, and "13" is not in it.
    assert event == {
        "type": "player.hit",
        "thrower_id": thrower.id,
        "target_id": target.id,
        "item": "tomate",
    }
    assert "13" not in str(event)

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_throwing_an_object_outside_the_catalogue_is_refused():
    owner = await sync_to_async(User.objects.create_user)(username="owner", password="pwd")
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name="WS room")
    await sync_to_async(Participant.objects.create)(room=room, user=owner, display_name="Thrower")
    target = await sync_to_async(Participant.objects.create)(
        room=room, display_name="Target", connection_count=1
    )

    communicator, _ = await connect_participant(room, owner)

    await communicator.send_json_to(
        {"type": "player.throw", "target_id": target.id, "item": "ladrillo"}
    )
    error = await wait_for(communicator, "error")
    assert error["code"] == "invalid_action"

    await communicator.send_json_to(
        {"type": "player.throw", "target_id": "not-an-id", "item": "tomate"}
    )
    error = await wait_for(communicator, "error")
    assert error["code"] == "invalid_payload"

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_only_the_facilitator_can_switch_the_playful_layer():
    owner = await sync_to_async(User.objects.create_user)(username="owner", password="pwd")
    guest_user = await sync_to_async(User.objects.create_user)(username="guest", password="pwd")
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name="WS room")
    await sync_to_async(Participant.objects.create)(room=room, user=owner, display_name="Owner")
    await sync_to_async(Participant.objects.create)(
        room=room, user=guest_user, display_name="Guest"
    )

    guest_socket, state = await connect_participant(room, guest_user)
    assert state["room"]["allow_playful_actions"] is True

    await guest_socket.send_json_to({"type": "room.set_playful", "enabled": False})
    error = await wait_for(guest_socket, "error")
    assert error["code"] == "invalid_action"
    await sync_to_async(room.refresh_from_db)()
    assert room.allow_playful_actions is True

    owner_socket, _ = await connect_participant(room, owner)
    await owner_socket.send_json_to({"type": "room.set_playful", "enabled": False})
    event = await wait_for(owner_socket, "room.playful_changed")
    assert event["allow_playful_actions"] is False
    await sync_to_async(room.refresh_from_db)()
    assert room.allow_playful_actions is False

    await guest_socket.disconnect()
    await owner_socket.disconnect()
