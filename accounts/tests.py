# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

class AccountsTests(TestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = 'testpassword123'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_dashboard_unauthenticated_redirects(self):
        url = reverse('dashboard')
        response = self.client.get(url)
        # Should redirect to login with 'next' parameter
        self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_dashboard_authenticated(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Rooms")
        self.assertContains(response, self.username)

    def test_login_valid(self):
        response = self.client.post(reverse('login'), {
            'username': self.username,
            'password': self.password
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_invalid(self):
        response = self.client.post(reverse('login'), {
            'username': self.username,
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Please enter a correct username and password. "
            "Note that both fields may be case-sensitive."
        )

    def test_logout(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_registration_valid(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'NewPassword123!',
            'password2': 'NewPassword123!',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_registration_invalid(self):
        # Passwords mismatch
        response = self.client.post(reverse('register'), {
            'username': 'newuser2',
            'password1': 'NewPassword123!',
            'password2': 'DifferentPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser2').exists())
