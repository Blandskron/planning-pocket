from django.urls import path

from .consumers import PokerConsumer

websocket_urlpatterns = [
    path('ws/room/<str:public_id>/', PokerConsumer.as_asgi()),
]
