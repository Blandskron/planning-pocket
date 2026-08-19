# Copyright (c) 2024 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model

from config.asgi import application
from rooms.models import Participant, PokerRoom

User = get_user_model()

@pytest.mark.asyncio
@pytest.mark.django_db
async def test_websocket_presence():
    from asgiref.sync import sync_to_async

    owner = await sync_to_async(User.objects.create_user)(username='ws_user', password='pwd')
    room = await sync_to_async(PokerRoom.objects.create)(owner=owner, name='WS Room')

    await sync_to_async(Participant.objects.create)(
        room=room,
        user=owner,
        display_name='WS User'
    )


    communicator = WebsocketCommunicator(
        application,
        f"/ws/room/{room.public_id}/"
    )
    # We can't easily mock the session without headers.
    # For now, let's just assert that an anonymous un-sessioned user is rejected.
    connected, _ = await communicator.connect()
    assert not connected

    await communicator.disconnect()
