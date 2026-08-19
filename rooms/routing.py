# Copyright (c) 2024 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.urls import path

from .consumers import PokerConsumer

websocket_urlpatterns = [
    path('ws/room/<str:public_id>/', PokerConsumer.as_asgi()),
]
