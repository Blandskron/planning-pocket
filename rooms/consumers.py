# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Participant, PokerRoom


class PokerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handles new WebSocket connections.
        Authenticates the user (via session or standard Auth) and assigns them to the room group.
        Broadcasts a 'participant.joined' event to all other clients in the room.
        """
        self.public_id = self.scope['url_route']['kwargs']['public_id']
        self.room_group_name = f'room_{self.public_id}'

        # Resolve participant
        import logging
        logger = logging.getLogger(__name__)

        try:
            self.participant = await self.get_participant()
        except Exception as e:
            logger.error(f"Error resolving participant: {e}")
            self.participant = None

        if not self.participant:
            logger.warning("Participant not found or error, closing.")
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Notify others
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'participant.joined',
                'participant': {
                    'id': self.participant.id,
                    'display_name': self.participant.display_name
                }
            }
        )

    async def disconnect(self, close_code):
        """
        Handles WebSocket disconnections.
        Removes the connection from the room group and broadcasts a 'participant.left' event.
        Note: The participant record is kept in the database to allow reconnections.
        """
        if hasattr(self, 'participant') and self.participant:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'participant.left',
                    'participant_id': self.participant.id
                }
            )

    async def receive(self, text_data):
        """
        Main router for incoming WebSocket messages from the client.
        Enforces security (Facilitator-only actions vs Guest actions).
        """
        data = json.loads(text_data)
        event_type = data.get('type')

        if not self.participant:
            return

        if event_type == 'vote.cast':
            vote_value = data.get('value')
            await self.save_vote(vote_value)

            # Broadcast that this participant voted or un-voted
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'participant.voted',
                    'participant_id': self.participant.id,
                    'value': vote_value
                }
            )

        elif event_type == 'room.reveal':
            # Check if owner
            is_owner = await self.is_room_owner()
            if is_owner:
                await self.reveal_room()
                # Broadcast reveal
                participants_state = await self.get_all_participants_state()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'room.revealed',
                        'participants': participants_state
                    }
                )

        elif event_type == 'room.reset':
            is_owner = await self.is_room_owner()
            if is_owner:
                await self.reset_room()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'room.resetted'
                    }
                )

        elif event_type == 'issue.activate':
            is_owner = await self.is_room_owner()
            if is_owner:
                issue_id = data.get('issue_id')
                await self.activate_issue(issue_id)
                issue_data = await self.get_issue_data(issue_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'issue.activated',
                        'issue': issue_data
                    }
                )

        elif event_type == 'issue.finish':
            is_owner = await self.is_room_owner()
            if is_owner:
                final_result = data.get('final_result')
                issue_data = await self.finish_active_issue(final_result)
                if issue_data:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'issue.finished',
                            'issue': issue_data
                        }
                    )
                    # Reset room after finishing
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'room.resetted'
                        }
                    )

    # Database operations
    @database_sync_to_async
    def save_vote(self, value):
        """
        Persists a vote to the database if the room is currently in 'voting' mode.
        """
        room = PokerRoom.objects.get(public_id=self.public_id)
        if room.voting_status == 'voting':
            self.participant.current_vote = value
            self.participant.save(update_fields=['current_vote'])

    @database_sync_to_async
    def is_room_owner(self):
        """Checks if the connected user is the creator/facilitator of the room."""
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            return False
        room = PokerRoom.objects.get(public_id=self.public_id)
        return room.owner == user

    @database_sync_to_async
    def reveal_room(self):
        """Transitions the room status to 'revealed', locking votes."""
        room = PokerRoom.objects.get(public_id=self.public_id)
        room.voting_status = 'revealed'
        room.save(update_fields=['voting_status'])

    @database_sync_to_async
    def reset_room(self):
        """Clears all votes and restarts the voting phase."""
        room = PokerRoom.objects.get(public_id=self.public_id)
        room.reset_voting()

    @database_sync_to_async
    def get_all_participants_state(self):
        """Returns the serialized state of all participants, applying privacy filters."""
        room = PokerRoom.objects.get(public_id=self.public_id)
        return [self._get_participant_state_sync(p, room) for p in room.participants.all()]

    @staticmethod
    def _get_participant_state_sync(participant, room):
        """
        CRITICAL SECURITY RULE: Privacy logic.
        If the room is not revealed, the actual 'current_vote' payload is forcefully 
        blanked out (set to None) before being sent to the client, preventing inspection via DevTools.
        """
        state = {
            'id': participant.id,
            'display_name': participant.display_name,
            'has_voted': participant.current_vote is not None,
        }
        if room.voting_status == 'revealed':
            state['current_vote'] = participant.current_vote
        else:
            state['current_vote'] = None

        return state

    @staticmethod
    def _get_participant_state(participant, room):
        return PokerConsumer._get_participant_state_sync(participant, room)

    @database_sync_to_async
    def get_participant(self):
        try:
            room = PokerRoom.objects.get(public_id=self.public_id)
        except PokerRoom.DoesNotExist:
            return None

        user = self.scope.get('user')
        if user and user.is_authenticated:
            return Participant.objects.filter(room=room, user=user).first()
        else:
            session = self.scope.get('session', {})
            guest_tokens = session.get('guest_tokens', {})
            room_token = guest_tokens.get(str(room.id))
            if room_token:
                return Participant.objects.filter(room=room, guest_token=room_token).first()
        return None

    # Event Handlers
    async def participant_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant.joined',
            'participant': event['participant']
        }))

    async def participant_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant.left',
            'participant_id': event['participant_id']
        }))

    async def participant_voted(self, event):
        # We only send whether the user has voted or not, NOT the actual value for privacy
        await self.send(text_data=json.dumps({
            'type': 'participant.voted',
            'participant_id': event['participant_id'],
            'value': 'voted' if event.get('value') is not None else None
        }))

    async def room_revealed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'room.revealed',
            'participants': event['participants']
        }))

    async def room_resetted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'room.resetted'
        }))

    async def issue_activated(self, event):
        await self.send(text_data=json.dumps({
            'type': 'issue.activated',
            'issue': event['issue']
        }))

    @database_sync_to_async
    def activate_issue(self, issue_id):
        from .models import Issue
        room = PokerRoom.objects.get(public_id=self.public_id)
        issue = Issue.objects.get(id=issue_id, room=room)

        room.active_issue = issue
        room.save(update_fields=['active_issue'])

        issue.status = 'active'
        issue.save(update_fields=['status'])

    @database_sync_to_async
    def get_issue_data(self, issue_id):
        from .models import Issue
        issue = Issue.objects.get(id=issue_id)
        return {
            'id': issue.id,
            'title': issue.title,
            'description': issue.description,
            'status': issue.status,
            'final_result': issue.final_result,
        }

    async def issue_finished(self, event):
        await self.send(text_data=json.dumps({
            'type': 'issue.finished',
            'issue': event['issue']
        }))

    @database_sync_to_async
    def finish_active_issue(self, final_result):
        room = PokerRoom.objects.get(public_id=self.public_id)
        if room.active_issue:
            issue = room.active_issue
            issue.final_result = final_result
            issue.status = 'estimated'
            issue.save(update_fields=['final_result', 'status'])

            # Clear active issue and reset room
            room.active_issue = None
            room.reset_voting()
            room.save(update_fields=['active_issue'])

            return {
                'id': issue.id,
                'title': issue.title,
                'description': issue.description,
                'status': issue.status,
                'final_result': issue.final_result,
            }
        return None
