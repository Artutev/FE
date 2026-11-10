import json
from datetime import date, timedelta

from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from Chat import crypto, services
from Chat.models import Conversation, Message
from Chat.routing import websocket_urlpatterns
from Events.models import Event, EventRegistration
from Users.models import FriendRequest, User


def make_friends(a, b):
    FriendRequest.objects.create(from_user=a, to_user=b, status='accepted')


class ChatAccessTests(TestCase):
    def setUp(self):
        self.ann = User.objects.create_user('ann', 'ann@example.test', 'Pass12345!x')
        self.bob = User.objects.create_user('bob', 'bob@example.test', 'Pass12345!x')
        self.eve = User.objects.create_user('eve', 'eve@example.test', 'Pass12345!x')
        make_friends(self.ann, self.bob)

    def test_start_direct_only_with_friends(self):
        self.client.force_login(self.ann)
        response = self.client.post(reverse('Chat:start_direct', args=['bob']))
        conversation = Conversation.objects.get(kind=Conversation.DIRECT)
        self.assertRedirects(response, reverse('Chat:detail', args=[conversation.pk]))
        # повторно — тот же чат
        self.client.post(reverse('Chat:start_direct', args=['bob']))
        self.assertEqual(Conversation.objects.count(), 1)
        # не друг — чат не создаётся
        self.client.post(reverse('Chat:start_direct', args=['eve']))
        self.assertEqual(Conversation.objects.count(), 1)

    def test_strangers_cannot_open_chat(self):
        conversation = services.get_or_create_direct(self.ann, self.bob)
        self.client.force_login(self.eve)
        self.assertEqual(self.client.get(reverse('Chat:detail', args=[conversation.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('Chat:older', args=[conversation.pk])).status_code, 404)

    def test_unfriended_can_read_but_not_write(self):
        conversation = services.get_or_create_direct(self.ann, self.bob)
        FriendRequest.objects.all().delete()
        self.assertTrue(services.can_read(self.ann, conversation))
        self.assertFalse(services.can_write(self.ann, conversation))

    def test_event_chat_requires_registration(self):
        event = Event.objects.create(name='Jazz', date=date.today() + timedelta(days=3), creator=self.ann)
        self.client.force_login(self.bob)
        response = self.client.get(reverse('Chat:event', args=[event.pk]))
        self.assertRedirects(response, reverse('Events:event_detail', args=[event.pk]))
        EventRegistration.objects.create(user=self.bob, event=event)
        response = self.client.get(reverse('Chat:event', args=[event.pk]))
        conversation = Conversation.objects.get(event=event)
        self.assertRedirects(response, reverse('Chat:detail', args=[conversation.pk]))

    def test_unread_counts_and_mark_read(self):
        conversation = services.get_or_create_direct(self.ann, self.bob)
        services.create_message(conversation, self.ann, 'привет')
        services.create_message(conversation, self.ann, 'как дела?')
        self.assertEqual(services.total_unread(self.bob), 2)
        self.assertEqual(services.total_unread(self.ann), 0)
        self.client.force_login(self.bob)
        self.client.get(reverse('Chat:detail', args=[conversation.pk]))
        self.assertEqual(services.total_unread(self.bob), 0)

    def test_http_fallback_send_and_history(self):
        conversation = services.get_or_create_direct(self.ann, self.bob)
        self.client.force_login(self.ann)
        response = self.client.post(reverse('Chat:send', args=[conversation.pk]), {'text': '  hi <b>there</b>  '})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message']['text'], 'hi <b>there</b>')
        for i in range(60):
            services.create_message(conversation, self.bob, f'm{i}')
        first_page = self.client.get(reverse('Chat:older', args=[conversation.pk])).json()
        self.assertEqual(len(first_page['messages']), 50)
        self.assertTrue(first_page['has_more'])
        oldest = first_page['messages'][0]['id']
        rest = self.client.get(reverse('Chat:older', args=[conversation.pk]), {'before': oldest}).json()
        self.assertEqual(len(rest['messages']), 11)
        self.assertFalse(rest['has_more'])

    def test_detail_page_passes_read_marks(self):
        conversation = services.get_or_create_direct(self.ann, self.bob)
        services.create_message(conversation, self.ann, 'привет')
        self.assertEqual(list(services.read_marks(conversation)), [self.ann.pk])
        read_at = services.mark_read(conversation, self.bob)
        self.assertEqual(services.read_marks(conversation)[self.bob.pk], read_at.isoformat())

        self.client.force_login(self.ann)
        content = self.client.get(reverse('Chat:detail', args=[conversation.pk])).content.decode()
        raw = content.split('<script id="chatReads" type="application/json">', 1)[1].split('</script>', 1)[0]
        self.assertEqual(json.loads(raw)[str(self.bob.pk)], read_at.isoformat())

    def test_list_page_shows_conversations_and_badge(self):
        conversation = services.get_or_create_direct(self.ann, self.bob)
        services.create_message(conversation, self.bob, 'yo')
        self.client.force_login(self.ann)
        content = self.client.get(reverse('Chat:list')).content.decode()
        self.assertIn('bob', content)
        self.assertIn('data-chat-badge', content)
        self.assertIn('class="ch-badge">1<', content)


class ChatWebSocketTests(TransactionTestCase):
    """Настоящие WebSocket-соединения через in-memory channel layer."""

    def setUp(self):
        cache.clear()
        self.ann = User.objects.create_user('ann', 'ann@example.test', 'Pass12345!x')
        self.bob = User.objects.create_user('bob', 'bob@example.test', 'Pass12345!x')
        self.eve = User.objects.create_user('eve', 'eve@example.test', 'Pass12345!x')
        make_friends(self.ann, self.bob)
        self.conversation = services.get_or_create_direct(self.ann, self.bob)

    def connect(self, user, path):
        communicator = WebsocketCommunicator(URLRouter(websocket_urlpatterns), path)
        communicator.scope['user'] = user
        return communicator

    def test_message_delivery_typing_and_unread(self):
        async def scenario():
            path = f'/ws/chat/{self.conversation.pk}/'
            ann = self.connect(self.ann, path)
            bob = self.connect(self.bob, path)
            bob_notify = self.connect(self.bob, '/ws/notify/')
            self.assertTrue((await ann.connect())[0])
            self.assertTrue((await bob.connect())[0])
            self.assertTrue((await bob_notify.connect())[0])
            self.assertEqual((await bob_notify.receive_json_from())['total'], 0)

            # presence: оба в чате
            # Боб подключился вторым: его первое событие — присутствие обоих
            presence = await bob.receive_json_from()
            self.assertEqual(presence['type'], 'presence')
            self.assertEqual(sorted(presence['online']), sorted([self.ann.pk, self.bob.pk]))

            await ann.send_json_to({'type': 'typing'})
            typing = await bob.receive_json_from()
            self.assertEqual(typing, {'type': 'typing', 'user_id': self.ann.pk, 'username': 'ann'})

            await ann.send_json_to({'type': 'message', 'text': 'Привет!', 'client_id': 'c1'})
            got = await bob.receive_json_from()
            while got['type'] != 'message':
                got = await bob.receive_json_from()
            self.assertEqual(got['message']['text'], 'Привет!')
            self.assertEqual(got['client_id'], 'c1')
            unread = await bob_notify.receive_json_from()
            self.assertEqual(unread['total'], 1)

            await bob.send_json_to({'type': 'read'})
            self.assertEqual((await bob_notify.receive_json_from())['total'], 0)

            for c in (ann, bob, bob_notify):
                await c.disconnect()

        async_to_sync(scenario)()
        self.assertEqual(Message.objects.filter(conversation=self.conversation).count(), 1)

    def test_read_receipt_reaches_the_sender(self):
        async def scenario():
            path = f'/ws/chat/{self.conversation.pk}/'
            ann = self.connect(self.ann, path)
            bob = self.connect(self.bob, path)
            await ann.connect()
            await bob.connect()
            await ann.send_json_to({'type': 'message', 'text': 'Ты тут?', 'client_id': 'c1'})
            # как клиент: «прочитано» Боб шлёт, когда сообщение уже пришло
            got = await bob.receive_json_from()
            while got['type'] != 'message':
                got = await bob.receive_json_from()
            await bob.send_json_to({'type': 'read'})

            got = await ann.receive_json_from()
            while got['type'] != 'read':
                got = await ann.receive_json_from()
            self.assertEqual(got['user_id'], self.bob.pk)
            # своё «прочитано» Бобу не возвращается
            bob_events = []
            while not await bob.receive_nothing(timeout=0.3):
                bob_events.append((await bob.receive_json_from())['type'])
            self.assertNotIn('read', bob_events)
            for c in (ann, bob):
                await c.disconnect()
            return got['read_at']

        read_at = async_to_sync(scenario)()
        message = Message.objects.get(conversation=self.conversation)
        bob_mark = services.read_marks(self.conversation)[self.bob.pk]
        self.assertEqual(read_at, bob_mark)
        membership = self.conversation.memberships.get(user=self.bob)
        self.assertGreaterEqual(membership.last_read_at, message.created_at)

    def test_stranger_and_anonymous_are_rejected(self):
        from django.contrib.auth.models import AnonymousUser

        async def scenario():
            path = f'/ws/chat/{self.conversation.pk}/'
            for user in (self.eve, AnonymousUser()):
                communicator = self.connect(user, path)
                connected, _ = await communicator.connect()
                self.assertFalse(connected)

        async_to_sync(scenario)()

    def test_rate_limit(self):
        async def scenario():
            ann = self.connect(self.ann, f'/ws/chat/{self.conversation.pk}/')
            await ann.connect()
            errors = 0
            kinds = []
            for i in range(20):
                await ann.send_json_to({'type': 'message', 'text': f'spam {i}'})
            # 20 отправок = 20 ответов (сообщение или ошибка лимита); ждём каждый, а не «тишину»
            # (иначе на медленной машине тест заканчивался раньше, чем доходили ошибки)
            while len(kinds) < 20:
                event = await ann.receive_json_from(timeout=10)
                if event['type'] == 'presence':
                    continue
                kinds.append(event['type'])
                if event['type'] == 'error' and event['code'] == 'rate_limited':
                    errors += 1
            await ann.disconnect()
            return errors

        errors = async_to_sync(scenario)()
        self.assertGreater(errors, 0)
        self.assertEqual(Message.objects.count(), 15)


class MessageEncryptionTests(TestCase):
    def setUp(self):
        self.ann = User.objects.create_user('ann', 'ann@example.test', 'Pass12345!x')
        self.bob = User.objects.create_user('bob', 'bob@example.test', 'Pass12345!x')
        make_friends(self.ann, self.bob)
        self.conversation = services.get_or_create_direct(self.ann, self.bob)

    def raw_text(self, message):
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT text FROM "{Message._meta.db_table}" WHERE id = %s', [message.pk])
            return cursor.fetchone()[0]

    def test_text_is_encrypted_in_db_and_plain_in_app(self):
        message = services.create_message(self.conversation, self.ann, 'Секретная встреча в 19:00')
        raw = self.raw_text(message)
        self.assertTrue(crypto.is_encrypted(raw))
        self.assertNotIn('Секретная', raw)
        self.assertEqual(Message.objects.get(pk=message.pk).text, 'Секретная встреча в 19:00')
        # последнее сообщение в списке чатов (Subquery) тоже расшифровано
        self.assertEqual(services.conversations_for(self.bob)[0].last_text, 'Секретная встреча в 19:00')

    def test_same_text_gives_different_ciphertext(self):
        a = services.create_message(self.conversation, self.ann, 'привет')
        b = services.create_message(self.conversation, self.ann, 'привет')
        self.assertNotEqual(self.raw_text(a), self.raw_text(b))

    def test_text_that_looks_encrypted_is_still_encrypted(self):
        message = services.create_message(self.conversation, self.ann, 'fernet:hello')
        self.assertNotEqual(self.raw_text(message), 'fernet:hello')
        self.assertEqual(Message.objects.get(pk=message.pk).text, 'fernet:hello')

    def test_legacy_plaintext_rows_are_still_readable(self):
        message = services.create_message(self.conversation, self.ann, 'x')
        with connection.cursor() as cursor:
            cursor.execute(f'UPDATE "{Message._meta.db_table}" SET text = %s WHERE id = %s', ['старое', message.pk])
        self.assertEqual(Message.objects.get(pk=message.pk).text, 'старое')

    def test_key_rotation_keeps_old_messages_readable(self):
        from cryptography.fernet import Fernet
        old_key, new_key = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        with self.settings(CHAT_ENCRYPTION_KEYS=[old_key]):
            message = services.create_message(self.conversation, self.ann, 'до смены ключа')
        with self.settings(CHAT_ENCRYPTION_KEYS=[new_key, old_key]):
            self.assertEqual(Message.objects.get(pk=message.pk).text, 'до смены ключа')
        with self.settings(CHAT_ENCRYPTION_KEYS=[new_key]):
            self.assertEqual(Message.objects.get(pk=message.pk).text, '🔒')
