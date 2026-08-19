# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.contrib import admin

from .models import PokerRoom


@admin.register(PokerRoom)
class PokerRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'public_id', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'public_id', 'owner__username')
