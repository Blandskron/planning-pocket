# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

import pytest
from django.contrib.auth import get_user_model

from rooms.models import Issue, PokerRoom

User = get_user_model()

@pytest.mark.django_db
class TestIssues:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.owner = User.objects.create_user(username='owner', password='pwd')
        self.room = PokerRoom.objects.create(owner=self.owner, name='Test Room')

    def test_create_issue(self):
        issue = Issue.objects.create(room=self.room, title='Test Issue', description='Details')
        assert issue.status == 'pending'
        assert self.room.issues.count() == 1

    def test_activate_issue(self):
        issue1 = Issue.objects.create(room=self.room, title='Test Issue 1')
        Issue.objects.create(room=self.room, title='Test Issue 2')

        self.room.active_issue = issue1
        self.room.save()

        issue1.status = 'active'
        issue1.save()

        self.room.refresh_from_db()
        assert self.room.active_issue == issue1
        assert issue1.status == 'active'

    def test_finish_active_issue(self):
        issue1 = Issue.objects.create(room=self.room, title='Test Issue 1')
        self.room.active_issue = issue1
        self.room.save()



        issue1.final_result = '8'
        issue1.status = 'estimated'
        issue1.save()

        self.room.active_issue = None
        self.room.reset_voting()
        self.room.save()

        self.room.refresh_from_db()
        issue1.refresh_from_db()

        assert self.room.active_issue is None
        assert issue1.final_result == '8'
        assert issue1.status == 'estimated'
        assert self.room.voting_status == 'voting'

