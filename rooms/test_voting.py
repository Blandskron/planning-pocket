# Copyright (c) 2024 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

import pytest
from django.contrib.auth import get_user_model

from rooms.models import Participant, PokerRoom

User = get_user_model()

@pytest.mark.django_db
class TestVotingEngine:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username='owner', password='pwd')
        self.room = PokerRoom.objects.create(owner=self.owner, name='Test Room')
        self.participant1 = Participant.objects.create(
            room=self.room, user=self.owner, display_name='P1'
        )
        self.participant2 = Participant.objects.create(
            room=self.room, display_name='P2'
        )
        self.participant3 = Participant.objects.create(
            room=self.room, display_name='P3'
        )

    def test_cast_vote_saves_vote(self):
        # We'll test this via DB logic first, or consumer if we can
        self.participant1.current_vote = '5'
        self.participant1.save()
        assert Participant.objects.get(id=self.participant1.id).current_vote == '5'

    def test_privacy_before_reveal(self):
        self.participant1.current_vote = '5'
        self.participant1.save()
        self.room.voting_status = 'voting'
        self.room.save()

        # Mock what the consumer will send when someone casts a vote
        # It should NOT send the value '5' to others.
        from rooms.consumers import PokerConsumer
        data = PokerConsumer._get_participant_state(self.participant1, self.room)
        assert data['id'] == self.participant1.id
        assert data['has_voted'] is True
        assert 'current_vote' not in data or data['current_vote'] is None

    def test_reveal_discloses_votes(self):
        self.participant1.current_vote = '5'
        self.participant1.save()

        self.room.voting_status = 'revealed'
        self.room.save()

        from rooms.consumers import PokerConsumer
        data = PokerConsumer._get_participant_state(self.participant1, self.room)
        assert data['id'] == self.participant1.id
        assert data['has_voted'] is True
        assert data['current_vote'] == '5'

    def test_reset_clears_votes_and_status(self):
        self.participant1.current_vote = '5'
        self.participant1.save()
        self.room.voting_status = 'revealed'
        self.room.save()

        self.room.reset_voting()
        self.room.refresh_from_db()
        self.participant1.refresh_from_db()

        assert self.room.voting_status == 'voting'
        assert self.participant1.current_vote is None

