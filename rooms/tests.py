# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import PokerRoom

User = get_user_model()

class RoomsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password123')
        self.other_user = User.objects.create_user(username='other', password='password123')
        self.room = PokerRoom.objects.create(owner=self.owner, name='Test Room')

    def test_anonymous_cannot_create_room(self):
        response = self.client.post(reverse('create_room'), {'name': 'New Room'})
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('create_room')}")

    def test_authenticated_can_create_room(self):
        self.client.login(username='owner', password='password123')
        response = self.client.post(reverse('create_room'), {'name': 'New Room'})
        # Should redirect to room detail
        new_room = PokerRoom.objects.get(name='New Room')
        self.assertRedirects(response, reverse('room_detail', args=[new_room.public_id]))

    def test_public_id_is_unpredictable(self):
        self.assertEqual(len(self.room.public_id), 9)
        # Should not be an integer/sequential ID
        with self.assertRaises(ValueError):
            int(self.room.public_id)

    def test_nonexistent_room_returns_404(self):
        response = self.client.get(reverse('room_detail', args=['invalidid']))
        self.assertEqual(response.status_code, 404)

    def test_owner_can_close_room(self):
        self.client.login(username='owner', password='password123')
        response = self.client.post(reverse('close_room', args=[self.room.public_id]))
        self.assertRedirects(response, reverse('dashboard'))
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'closed')
        self.assertIsNotNone(self.room.closed_at)

    def test_other_user_cannot_close_room(self):
        self.client.login(username='other', password='password123')
        response = self.client.post(reverse('close_room', args=[self.room.public_id]))
        self.assertEqual(response.status_code, 403)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'active')

    def test_guest_join_assigns_name(self):
        url = reverse('room_detail', args=[self.room.public_id])
        response = self.client.post(url, {'display_name': 'Guest User'})
        self.assertRedirects(response, url)
        self.assertTrue(self.room.participants.filter(display_name='Guest User').exists())

    def test_guest_join_empty_name_rejected(self):
        url = reverse('room_detail', args=[self.room.public_id])
        response = self.client.post(url, {'display_name': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(self.room.participants.count(), 0)

    def test_guest_refresh_preserves_identity(self):
        url = reverse('room_detail', args=[self.room.public_id])
        # Join as guest
        self.client.post(url, {'display_name': 'Refresh Guest'})

        # Second request (refresh)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Refresh Guest')
        # Ensure it didn't create a second participant
        self.assertEqual(self.room.participants.count(), 1)

    def test_room_detail_uses_the_table_participant_layout(self):
        self.client.login(username='owner', password='password123')
        response = self.client.get(reverse('room_detail', args=[self.room.public_id]))

        self.assertContains(response, 'class="poker-room"')
        self.assertContains(response, 'class="poker-table-card"')
        self.assertContains(response, 'table-seat')
        self.assertContains(response, 'Vota directamente o añade una historia')
        self.assertContains(
            response, 'class="poker-card" type="button" onclick="castVote(\'0\', this)"'
        )

    def test_cannot_join_closed_room(self):
        self.room.close_room()
        url = reverse('room_detail', args=[self.room.public_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Room Closed')
        self.assertEqual(self.room.participants.count(), 0)
