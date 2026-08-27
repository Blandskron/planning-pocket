# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

from .identity import COLOR_COUNT, FACES, PETS, derive_identity
from .utils import generate_guest_token, generate_public_id


class PokerRoom(models.Model):
    """
    Represents a Planning Poker room.

    A room is created by a Facilitator (owner) and can host multiple Participants.
    It manages the global state of the voting process (voting vs revealed),
    the current deck of cards, and points to the currently active issue being estimated.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('closed', 'Closed'),
    )
    VOTING_STATUS_CHOICES = (
        ('voting', 'Voting'),
        ('revealed', 'Revealed'),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rooms',
        help_text="The user who created and facilitates the room."
    )
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    voting_status = models.CharField(
        max_length=20,
        choices=VOTING_STATUS_CHOICES,
        default='voting',
        help_text="Controls the privacy of votes. If 'voting', votes are hidden from clients."
    )
    deck = models.CharField(max_length=100, default='0,1,2,3,5,8,13,21,34,55,89,?,Coffee')
    allow_playful_actions = models.BooleanField(
        default=True,
        help_text="Facilitator switch for the playful layer across the whole room."
    )
    recess_open = models.BooleanField(
        default=False,
        help_text=(
            "Whether people can leave their seats and walk around. Only meaningful "
            "while voting; closed automatically on reveal. Positions are never stored."
        )
    )

    active_issue = models.ForeignKey(
        'Issue', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )

    public_id = models.CharField(
        max_length=20,
        unique=True,
        default=generate_public_id,
        db_index=True,
        help_text="Secure, unguessable ID used in sharing URLs."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def close_room(self):
        """Transitions the room to a closed state, preventing further interaction."""
        if self.status != 'closed':
            self.status = 'closed'
            self.closed_at = timezone.now()
            self.save(update_fields=['status', 'closed_at'])

    def reset_voting(self):
        """
        Clears all participant votes and transitions the room back to 'voting' state.
        This is typically called to start a new estimation round.
        """
        self.voting_status = 'voting'
        self.save(update_fields=['voting_status'])
        self.participants.update(current_vote=None, throws_this_round=0)

    def __str__(self):
        return f"{self.name} ({self.public_id})"

class Issue(models.Model):
    """
    Represents a specific task, user story, or issue to be estimated in a PokerRoom.
    Issues are created by the facilitator and can hold the final agreed-upon result.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('estimated', 'Estimated'),
    )
    room = models.ForeignKey(PokerRoom, on_delete=models.CASCADE, related_name='issues')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    final_result = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Participant(models.Model):
    """
    Represents a user (authenticated or guest) currently inside a PokerRoom.
    Maintains their display name and their current vote state.
    """
    room = models.ForeignKey(PokerRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Linked user account, if the participant is registered."
    )
    display_name = models.CharField(max_length=50)
    current_vote = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="The value voted. Set to null if they haven't voted or retracted their vote."
    )
    guest_token = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        default=generate_guest_token,
        help_text="Session-linked token for tracking guest identities without user accounts."
    )
    avatar = models.CharField(
        max_length=20,
        choices=FACES,
        blank=True,
        help_text="Cosmetic face drawn on the seat. Blank means derive one."
    )
    pet = models.CharField(
        max_length=20,
        choices=PETS,
        blank=True,
        help_text="Cosmetic companion drawn beside the seat. Blank means derive one."
    )
    color_index = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(COLOR_COUNT - 1)],
        help_text="Index into the seat palette. Null means derive one."
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    connection_count = models.PositiveIntegerField(default=0)
    last_reminded_at = models.DateTimeField(null=True, blank=True)
    last_throw_at = models.DateTimeField(
        null=True, blank=True, help_text="Cooldown anchor for the playful layer."
    )
    throws_this_round = models.PositiveSmallIntegerField(
        default=0,
        help_text="Per-round throw count. Reset with the votes; never accumulates."
    )

    class Meta:
        unique_together = ('room', 'user')  # A registered user can only join a room once

    @property
    def identity(self):
        """Return the cosmetic identity used to draw this seat.

        Stored choices win; anything unset falls back to a stable derivation, so
        participants created before these fields existed still get a seat that
        looks like theirs and stays the same between sessions.
        """
        face, pet, color = derive_identity(self.guest_token or self.pk)
        return {
            'avatar': self.avatar or face,
            'pet': self.pet or pet,
            'color': self.color_index if self.color_index is not None else color,
        }

    def __str__(self):
        return self.display_name

