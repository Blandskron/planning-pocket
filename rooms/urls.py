# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.urls import path

from .views import close_room, create_room, room_detail

urlpatterns = [
    path('create/', create_room, name='create_room'),
    path('p/<str:public_id>/', room_detail, name='room_detail'),
    path('p/<str:public_id>/close/', close_room, name='close_room'),
]
