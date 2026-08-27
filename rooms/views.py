# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import GuestJoinForm, IssueForm, PokerRoomForm
from .models import Participant, PokerRoom
from .playful import THROWABLES


@login_required
def create_room(request):
    """
    HTTP View for Facilitators to create a new PokerRoom.
    Requires authentication. Upon creation, automatically redirects to the new room.
    """
    if request.method == 'POST':
        form = PokerRoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.owner = request.user
            room.save()
            return redirect('room_detail', public_id=room.public_id)
    else:
        form = PokerRoomForm()

    return render(request, 'rooms/create_room.html', {'form': form})

def room_detail(request, public_id):
    """
    Main HTTP View for the PokerRoom interface.
    Handles the initial load of the room state (participants, issues, deck).
    Also acts as the identity resolver:
    - If user is authenticated and is owner, grants facilitator controls.
    - If user is authenticated (but not owner) or a guest, checks if they have a Participant record.
    - If no Participant record exists, redirects to 'join_room' to ask for a display name.
    """
    room = get_object_or_404(PokerRoom, public_id=public_id)
    is_owner = request.user == room.owner

    if room.status == 'closed' and not is_owner:
        return render(request, 'rooms/room_closed.html', {'room': room})

    participant = None

    if request.user.is_authenticated:
        # Get or create participant for authenticated user
        participant, _ = Participant.objects.get_or_create(
            room=room,
            user=request.user,
            defaults={'display_name': request.user.username}
        )
    else:
        # Handle guest
        guest_tokens = request.session.get('guest_tokens', {})
        room_token = guest_tokens.get(str(room.id))

        if room_token:
            # Check if participant exists
            participant = Participant.objects.filter(room=room, guest_token=room_token).first()

        if not participant:
            if request.method == 'POST':
                form = GuestJoinForm(request.POST)
                if form.is_valid():
                    participant = Participant.objects.create(
                        room=room,
                        display_name=form.cleaned_data['display_name'],
                        pet=form.cleaned_data.get('pet') or '',
                        color_index=form.cleaned_data.get('color_index'),
                    )
                    # Save token in session
                    guest_tokens[str(room.id)] = participant.guest_token
                    request.session['guest_tokens'] = guest_tokens
                    return redirect('room_detail', public_id=public_id)
            else:
                form = GuestJoinForm()
            return render(request, 'rooms/join_guest.html', {'room': room, 'form': form})

    participants = room.participants.order_by('joined_at', 'id')
    deck_cards = room.deck.split(',')
    issues = room.issues.all().order_by('created_at')

    if is_owner and request.method == 'POST' and 'add_issue' in request.POST:
        issue_form = IssueForm(request.POST)
        if issue_form.is_valid():
            issue = issue_form.save(commit=False)
            issue.room = room
            issue.save()
            return redirect('room_detail', public_id=public_id)
    else:
        issue_form = IssueForm()

    return render(request, 'rooms/room_detail.html', {
        'room': room,
        'is_owner': is_owner,
        'participant': participant,
        'participants': participants,
        'deck_cards': deck_cards,
        'issues': issues,
        'issue_form': issue_form,
        'throwables': THROWABLES,
    })


@login_required
def close_room(request, public_id):
    room = get_object_or_404(PokerRoom, public_id=public_id)

    if request.user != room.owner:
        return HttpResponseForbidden("You are not allowed to close this room.")

    if request.method == 'POST':
        room.close_room()
        return redirect('dashboard')

    return render(request, 'rooms/close_room_confirm.html', {'room': room})
