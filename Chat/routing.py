from django.urls import path

from Chat import consumers

websocket_urlpatterns = [
    path('ws/chat/<int:conversation_id>/', consumers.ChatConsumer.as_asgi()),
    path('ws/notify/', consumers.NotifyConsumer.as_asgi()),
]
