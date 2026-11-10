"""WebSocket-обработчики чата.

ws/chat/<id>/ — конкретный чат: сообщения, «печатает…», прочитано, кто в чате.
ws/notify/   — личный канал пользователя: обновление значка непрочитанных на любой странице.

Протокол (JSON):
  клиент → {"type": "message", "text": "...", "client_id": "..."} | {"type": "typing"} | {"type": "read"}
  сервер → {"type": "message", "message": {...}, "client_id": "..."}
           {"type": "typing", "user_id": 1, "username": "..."}
           {"type": "read", "user_id": 1, "read_at": "ISO"}   — участник дочитал чат до read_at
           {"type": "presence", "online": [user_id, ...]}
           {"type": "unread", "total": 3}
           {"type": "error", "code": "...", "detail": "..."}
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache

from Chat import services
from Chat.models import Conversation, Message
from Chat.realtime import chat_group, unread_payloads, user_group

RATE_LIMIT_MESSAGES = 15   # не больше 15 сообщений
RATE_LIMIT_WINDOW = 10     # за 10 секунд
PRESENCE_TTL = 60 * 60 * 6


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        self.conversation_id = int(self.scope['url_route']['kwargs']['conversation_id'])
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.conversation = await self._load_conversation()
        if self.conversation is None:
            await self.close(code=4403)
            return
        self.group = chat_group(self.conversation_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self._presence_change(+1)

    async def disconnect(self, code):
        if getattr(self, 'group', None):
            await self._presence_change(-1)
            await self.channel_layer.group_discard(self.group, self.channel_name)

    # ---------- incoming ----------
    async def receive_json(self, content, **kwargs):
        kind = content.get('type')
        if kind == 'message':
            await self._handle_message(content)
        elif kind == 'typing':
            await self.channel_layer.group_send(self.group, {
                'type': 'chat.typing', 'user_id': self.user.id, 'username': self.user.username,
            })
        elif kind == 'read':
            read_at = await database_sync_to_async(services.mark_read)(self.conversation, self.user)
            await self.channel_layer.group_send(self.group, {
                'type': 'chat.read', 'user_id': self.user.id, 'read_at': read_at.isoformat(),
            })
            await self._send_own_unread()

    async def _handle_message(self, content):
        text = str(content.get('text', ''))[:Message.MAX_LENGTH].strip()
        if not text:
            return
        if not await database_sync_to_async(services.can_write)(self.user, self.conversation):
            await self.send_json({'type': 'error', 'code': 'forbidden', 'detail': 'You can no longer write here.'})
            return
        if not self._within_rate_limit():
            await self.send_json({'type': 'error', 'code': 'rate_limited', 'detail': 'Too many messages.'})
            return
        message = await database_sync_to_async(services.create_message)(self.conversation, self.user, text)
        payload = await database_sync_to_async(services.serialize_message)(message)
        await self.channel_layer.group_send(self.group, {
            'type': 'chat.message', 'message': payload, 'client_id': content.get('client_id'),
        })
        for user_id, unread in await database_sync_to_async(unread_payloads)(self.conversation, self.user.id):
            await self.channel_layer.group_send(user_group(user_id), unread)

    def _within_rate_limit(self):
        key = f'chat-rate:{self.user.id}'
        count = cache.get(key, 0)
        if count >= RATE_LIMIT_MESSAGES:
            return False
        cache.set(key, count + 1, RATE_LIMIT_WINDOW)
        return True

    # ---------- group events → this socket ----------
    async def chat_message(self, event):
        await self.send_json({'type': 'message', 'message': event['message'], 'client_id': event.get('client_id')})

    async def chat_typing(self, event):
        if event['user_id'] != self.user.id:
            await self.send_json({'type': 'typing', 'user_id': event['user_id'], 'username': event['username']})

    async def chat_read(self, event):
        if event['user_id'] != self.user.id:
            await self.send_json({'type': 'read', 'user_id': event['user_id'], 'read_at': event['read_at']})

    async def chat_presence(self, event):
        await self.send_json({'type': 'presence', 'online': event['online']})

    # ---------- helpers ----------
    @database_sync_to_async
    def _load_conversation(self):
        conversation = Conversation.objects.select_related('event').filter(pk=self.conversation_id).first()
        if conversation is None or not services.can_read(self.user, conversation):
            return None
        services.ensure_member(conversation, self.user)
        return conversation

    async def _presence_change(self, delta):
        key = f'chat-online:{self.conversation_id}'
        online = cache.get(key) or {}
        uid = str(self.user.id)
        online[uid] = max(0, online.get(uid, 0) + delta)
        if not online[uid]:
            online.pop(uid)
        cache.set(key, online, PRESENCE_TTL)
        await self.channel_layer.group_send(self.group, {
            'type': 'chat.presence', 'online': [int(user_id) for user_id in online],
        })

    async def _send_own_unread(self):
        total = await database_sync_to_async(services.total_unread)(self.user)
        await self.channel_layer.group_send(user_group(self.user.id), {'type': 'notify.unread', 'total': total})


class NotifyConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return
        self.group = user_group(self.user.id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        total = await database_sync_to_async(services.total_unread)(self.user)
        await self.send_json({'type': 'unread', 'total': total})

    async def disconnect(self, code):
        if getattr(self, 'group', None):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notify_unread(self, event):
        await self.send_json({'type': 'unread', 'total': event['total'], 'conversation_id': event.get('conversation_id')})
