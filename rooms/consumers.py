"""WebSocket protocol for the collaborative Planning Poker room."""

import json
import time
from json import JSONDecodeError

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import transaction
from django.db.models import F

from .models import Issue, Participant, PokerRoom
from .services import (
    RoomActionError,
    calculate_results,
    cast_vote,
    finish_active_issue,
    remind_participant,
    reset_round,
    reveal_round,
    set_playful_actions,
    set_recess,
    throw_item,
)
from .services import activate_issue as activate_room_issue


class PokerConsumer(AsyncWebsocketConsumer):
    """Accepts validated room actions and broadcasts server-authoritative state."""

    # A walking avatar sends roughly eight positions a second. Anything faster is
    # dropped rather than queued, so a client that falls behind loses the
    # intermediate position instead of building a backlog for everyone else.
    MOVE_MIN_INTERVAL = 0.11

    async def connect(self):
        self.public_id = self.scope["url_route"]["kwargs"]["public_id"]
        self.room_group_name = f"room_{self.public_id}"
        self.participant = await self.get_participant()
        if not self.participant:
            await self.close(code=4403)
            return

        self.last_move_at = 0.0
        self.recess_open = False
        self.was_offline = await self.participant_connected()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send_room_state()

        if self.was_offline:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "participant.joined",
                    "participant": {
                        "id": self.participant.id,
                        "display_name": self.participant.display_name,
                        "has_voted": self.participant.current_vote is not None,
                        "is_online": True,
                        "current_vote": None,
                        **self.participant.identity,
                    },
                },
            )

    async def disconnect(self, close_code):
        if not hasattr(self, "participant") or not self.participant:
            return

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        is_now_offline = await self.participant_disconnected()
        if is_now_offline:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "participant.left",
                    "participant_id": self.participant.id,
                },
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except JSONDecodeError:
            await self.send_error("invalid_payload", "The message must be valid JSON.")
            return

        if not isinstance(data, dict):
            await self.send_error("invalid_payload", "The message must be a JSON object.")
            return

        event_type = data.get("type")
        if event_type not in {
            "vote.cast",
            "room.reveal",
            "room.reset",
            "issue.activate",
            "issue.finish",
            "participant.remind",
            "player.throw",
            "room.set_playful",
            "player.move",
            "room.set_recess",
        }:
            await self.send_error("unknown_action", "This action is not supported.")
            return

        if event_type == "vote.cast":
            await self.handle_vote(data)
        elif event_type == "room.reveal":
            await self.handle_reveal()
        elif event_type == "room.reset":
            await self.handle_reset()
        elif event_type == "issue.activate":
            await self.handle_issue_activation(data)
        elif event_type == "issue.finish":
            await self.handle_issue_finish(data)
        elif event_type == "participant.remind":
            await self.handle_participant_reminder(data)
        elif event_type == "player.throw":
            await self.handle_throw(data)
        elif event_type == "room.set_playful":
            await self.handle_set_playful(data)
        elif event_type == "player.move":
            await self.handle_move(data)
        elif event_type == "room.set_recess":
            await self.handle_set_recess(data)

    async def handle_vote(self, data):
        value = data.get("value")
        if value is not None and not isinstance(value, str):
            await self.send_error("invalid_payload", "A vote must be a card value or null.")
            return

        try:
            await self.save_vote(value)
        except RoomActionError as error:
            await self.send_error("invalid_action", str(error))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "participant.voted",
                "participant_id": self.participant.id,
                "has_voted": value is not None,
            },
        )

    async def handle_reveal(self):
        try:
            results, recess_was_open = await self.reveal_room()
        except RoomActionError as error:
            await self.send_error("invalid_action", str(error))
            return

        participants = await self.get_all_participants_state()
        # Only when there was something to close, and before the reveal itself, so
        # clients seat everyone again while the countdown runs.
        if recess_was_open:
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "room.recess_changed", "recess_open": False},
            )
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "room.revealed", "participants": participants, "results": results},
        )

    async def handle_reset(self):
        try:
            await self.reset_room()
        except RoomActionError as error:
            await self.send_error("invalid_action", str(error))
            return

        await self.channel_layer.group_send(self.room_group_name, {"type": "room.resetted"})

    async def handle_issue_activation(self, data):
        issue_id = data.get("issue_id")
        if isinstance(issue_id, bool) or not isinstance(issue_id, int):
            await self.send_error("invalid_payload", "An issue id must be an integer.")
            return

        try:
            issue = await self.activate_issue(issue_id)
        except (Issue.DoesNotExist, RoomActionError) as error:
            await self.send_error("invalid_action", str(error))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "issue.activated", "issue": issue},
        )
        await self.channel_layer.group_send(self.room_group_name, {"type": "room.resetted"})

    async def handle_issue_finish(self, data):
        final_result = data.get("final_result")
        if not isinstance(final_result, str):
            await self.send_error("invalid_payload", "A final estimate must be a card value.")
            return

        try:
            issue = await self.finish_active_issue(final_result)
        except RoomActionError as error:
            await self.send_error("invalid_action", str(error))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "issue.finished", "issue": issue},
        )
        await self.channel_layer.group_send(self.room_group_name, {"type": "room.resetted"})

    async def handle_participant_reminder(self, data):
        participant_id = data.get("participant_id")
        if isinstance(participant_id, bool) or not isinstance(participant_id, int):
            await self.send_error("invalid_payload", "A participant id must be an integer.")
            return

        try:
            participant = await self.remind_participant(participant_id)
        except (Participant.DoesNotExist, RoomActionError) as error:
            await self.send_error("invalid_action", str(error))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "participant.reminded", "participant_id": participant["id"]},
        )

    async def handle_throw(self, data):
        target_id = data.get("target_id")
        item = data.get("item")
        if isinstance(target_id, bool) or not isinstance(target_id, int):
            await self.send_error("invalid_payload", "A target id must be an integer.")
            return
        if not isinstance(item, str):
            await self.send_error("invalid_payload", "An item must be a catalogue slug.")
            return

        try:
            throw = await self.register_throw(target_id, item)
        except (Participant.DoesNotExist, RoomActionError) as error:
            await self.send_error("invalid_action", str(error))
            return

        # Deliberately narrow: who threw, at whom, and what. No vote state, no
        # counters, nothing that could be read as a hint about anyone's card.
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "player.hit",
                "thrower_id": throw["thrower_id"],
                "target_id": throw["target_id"],
                "item": throw["item"],
            },
        )

    async def handle_set_playful(self, data):
        enabled = data.get("enabled")
        if not isinstance(enabled, bool):
            await self.send_error("invalid_payload", "The switch must be true or false.")
            return

        try:
            allowed = await self.update_playful(enabled)
        except RoomActionError as error:
            await self.send_error("invalid_action", str(error))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "room.playful_changed", "allow_playful_actions": allowed},
        )

    async def handle_move(self, data):
        """Relay a position during the recess. Nothing here touches the database."""
        if not self.recess_open:
            return

        x = data.get("x")
        y = data.get("y")
        if isinstance(x, bool) or isinstance(y, bool):
            return
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            return

        now = time.monotonic()
        if now - self.last_move_at < self.MOVE_MIN_INTERVAL:
            return
        self.last_move_at = now

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "player.moved",
                "participant_id": self.participant.id,
                "x": float(x),
                "y": float(y),
            },
        )

    async def handle_set_recess(self, data):
        enabled = data.get("enabled")
        if not isinstance(enabled, bool):
            await self.send_error("invalid_payload", "The switch must be true or false.")
            return

        try:
            is_open = await self.update_recess(enabled)
        except RoomActionError as error:
            await self.send_error("invalid_action", str(error))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "room.recess_changed", "recess_open": is_open},
        )

    async def send_error(self, code, message):
        await self.send(text_data=json.dumps({"type": "error", "code": code, "message": message}))

    async def send_room_state(self):
        state = await self.get_room_state()
        # Cached so handle_move can reject positions without a query per frame.
        self.recess_open = state["room"]["recess_open"]
        await self.send(text_data=json.dumps({"type": "room.state", "payload": state}))

    @database_sync_to_async
    def get_participant(self):
        try:
            room = PokerRoom.objects.get(public_id=self.public_id)
        except PokerRoom.DoesNotExist:
            return None

        user = self.scope.get("user")
        if user and user.is_authenticated:
            return Participant.objects.filter(room=room, user=user).first()

        session = self.scope.get("session", {})
        room_token = session.get("guest_tokens", {}).get(str(room.id))
        if room_token:
            return Participant.objects.filter(room=room, guest_token=room_token).first()
        return None

    @database_sync_to_async
    def participant_connected(self):
        with transaction.atomic():
            participant = Participant.objects.select_for_update().get(pk=self.participant.id)
            was_offline = participant.connection_count == 0
            Participant.objects.filter(pk=participant.id).update(
                connection_count=F("connection_count") + 1
            )
            return was_offline

    @database_sync_to_async
    def participant_disconnected(self):
        with transaction.atomic():
            participant = Participant.objects.select_for_update().get(pk=self.participant.id)
            if participant.connection_count == 0:
                return False
            participant.connection_count -= 1
            participant.save(update_fields=["connection_count"])
            return participant.connection_count == 0

    @database_sync_to_async
    def save_vote(self, value):
        room = PokerRoom.objects.get(public_id=self.public_id)
        cast_vote(room.id, self.participant.id, value)

    @database_sync_to_async
    def reveal_room(self):
        room = PokerRoom.objects.get(public_id=self.public_id)
        recess_was_open = room.recess_open
        _, results = reveal_round(room.id, self.scope.get("user"))
        return results, recess_was_open

    @database_sync_to_async
    def reset_room(self):
        room = PokerRoom.objects.get(public_id=self.public_id)
        reset_round(room.id, self.scope.get("user"))

    @database_sync_to_async
    def activate_issue(self, issue_id):
        room = PokerRoom.objects.get(public_id=self.public_id)
        issue = activate_room_issue(room.id, issue_id, self.scope.get("user"))
        return self.serialize_issue(issue)

    @database_sync_to_async
    def finish_active_issue(self, final_result):
        room = PokerRoom.objects.get(public_id=self.public_id)
        issue = finish_active_issue(room.id, final_result, self.scope.get("user"))
        return self.serialize_issue(issue)

    @database_sync_to_async
    def remind_participant(self, participant_id):
        room = PokerRoom.objects.get(public_id=self.public_id)
        participant = remind_participant(room.id, participant_id, self.scope.get("user"))
        return {"id": participant.id}

    @database_sync_to_async
    def register_throw(self, target_id, item):
        room = PokerRoom.objects.get(public_id=self.public_id)
        thrower, target = throw_item(room.id, self.participant.id, target_id, item)
        return {"thrower_id": thrower.id, "target_id": target.id, "item": item}

    @database_sync_to_async
    def update_playful(self, enabled):
        room = PokerRoom.objects.get(public_id=self.public_id)
        room = set_playful_actions(room.id, enabled, self.scope.get("user"))
        return room.allow_playful_actions

    @database_sync_to_async
    def update_recess(self, enabled):
        room = PokerRoom.objects.get(public_id=self.public_id)
        room = set_recess(room.id, enabled, self.scope.get("user"))
        return room.recess_open

    @database_sync_to_async
    def get_all_participants_state(self):
        room = PokerRoom.objects.get(public_id=self.public_id)
        return [
            self._participant_state(participant, room)
            for participant in room.participants.order_by("joined_at", "id")
        ]

    @database_sync_to_async
    def get_room_state(self):
        room = PokerRoom.objects.select_related("active_issue").get(public_id=self.public_id)
        results = calculate_results(room) if room.voting_status == "revealed" else None
        user = self.scope.get("user")
        is_facilitator = bool(user and user.is_authenticated and user.pk == room.owner_id)
        return {
            "room": {
                "status": room.status,
                "voting_status": room.voting_status,
                "deck": room.deck.split(","),
                "is_facilitator": is_facilitator,
                "allow_playful_actions": room.allow_playful_actions,
                "recess_open": room.recess_open,
            },
            "active_issue": self.serialize_issue(room.active_issue) if room.active_issue else None,
            "participants": [
                self._participant_state(participant, room)
                for participant in room.participants.order_by("joined_at", "id")
            ],
            "your_vote": Participant.objects.get(pk=self.participant.id).current_vote,
            "results": results,
        }

    @staticmethod
    def serialize_issue(issue):
        return {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "status": issue.status,
            "final_result": issue.final_result,
        }

    @staticmethod
    def _participant_state(participant, room):
        state = {
            "id": participant.id,
            "display_name": participant.display_name,
            "has_voted": participant.current_vote is not None,
            "is_online": participant.connection_count > 0,
            # Cosmetic identity is not secret: it is needed to draw the ring while
            # voting is still open, and reveals nothing about the vote itself.
            **participant.identity,
        }
        state["current_vote"] = (
            participant.current_vote if room.voting_status == "revealed" else None
        )
        return state

    @staticmethod
    def _get_participant_state(participant, room):
        """Backward-compatible helper for existing privacy tests."""
        return PokerConsumer._participant_state(participant, room)

    async def participant_joined(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "participant.joined", "participant": event["participant"]}
            )
        )

    async def participant_left(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "participant.left", "participant_id": event["participant_id"]}
            )
        )

    async def participant_voted(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "participant.voted",
                    "participant_id": event["participant_id"],
                    "has_voted": event["has_voted"],
                }
            )
        )

    async def participant_reminded(self, event):
        await self.send(
            text_data=json.dumps(
                {"type": "participant.reminded", "participant_id": event["participant_id"]}
            )
        )

    async def player_hit(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "player.hit",
                    "thrower_id": event["thrower_id"],
                    "target_id": event["target_id"],
                    "item": event["item"],
                }
            )
        )

    async def room_playful_changed(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "room.playful_changed",
                    "allow_playful_actions": event["allow_playful_actions"],
                }
            )
        )

    async def player_moved(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "player.moved",
                    "participant_id": event["participant_id"],
                    "x": event["x"],
                    "y": event["y"],
                }
            )
        )

    async def room_recess_changed(self, event):
        self.recess_open = event["recess_open"]
        await self.send(
            text_data=json.dumps(
                {"type": "room.recess_changed", "recess_open": event["recess_open"]}
            )
        )

    async def room_revealed(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "room.revealed",
                    "participants": event["participants"],
                    "results": event["results"],
                }
            )
        )

    async def room_resetted(self, event):
        await self.send(text_data=json.dumps({"type": "room.resetted"}))

    async def issue_activated(self, event):
        await self.send(text_data=json.dumps({"type": "issue.activated", "issue": event["issue"]}))

    async def issue_finished(self, event):
        await self.send(text_data=json.dumps({"type": "issue.finished", "issue": event["issue"]}))
