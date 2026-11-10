import base64
import email
import json
from unittest import mock

from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from Users import gmail_backend
from Users.gmail_backend import GmailAPIBackend, GmailAPIError

GMAIL = dict(
    GMAIL_CLIENT_ID='cid', GMAIL_CLIENT_SECRET='secret', GMAIL_REFRESH_TOKEN='refresh',
    EMAIL_BACKEND='Users.gmail_backend.GmailAPIBackend',
    DEFAULT_FROM_EMAIL='EventTown <fastevent.123@gmail.com>',
)


@override_settings(**GMAIL)
class GmailBackendTests(SimpleTestCase):
    def setUp(self):
        gmail_backend._token_cache.update(value=None, expires_at=0)

    def make_message(self):
        message = EmailMultiAlternatives('Привет', 'text body', None, ['fan@example.test'])
        message.attach_alternative('<b>html</b>', 'text/html')
        return message

    def test_sends_raw_mime_with_fresh_token(self):
        calls = []

        def fake_post(url, data, headers, timeout):
            calls.append((url, data, headers))
            if url == gmail_backend.TOKEN_URL:
                return {'access_token': 'tok-1', 'expires_in': 3600}
            return {'id': 'abc'}

        with mock.patch.object(gmail_backend, '_post', side_effect=fake_post):
            sent = GmailAPIBackend().send_messages([self.make_message()])

        self.assertEqual(sent, 1)
        token_call, send_call = calls
        self.assertIn(b'grant_type=refresh_token', token_call[1])
        self.assertEqual(send_call[0], gmail_backend.SEND_URL)
        self.assertEqual(send_call[2]['Authorization'], 'Bearer tok-1')
        raw = json.loads(send_call[1])['raw']
        mime = email.message_from_bytes(base64.urlsafe_b64decode(raw))
        self.assertIn('fastevent.123@gmail.com', mime['From'])
        self.assertEqual(mime['To'], 'fan@example.test')
        self.assertTrue(mime.is_multipart())

    def test_token_is_cached(self):
        token_calls = []

        def fake_post(url, data, headers, timeout):
            if url == gmail_backend.TOKEN_URL:
                token_calls.append(1)
                return {'access_token': 'tok', 'expires_in': 3600}
            return {'id': 'x'}

        with mock.patch.object(gmail_backend, '_post', side_effect=fake_post):
            GmailAPIBackend().send_messages([self.make_message(), self.make_message()])
        self.assertEqual(len(token_calls), 1)

    def test_retries_once_on_401(self):
        state = {'sends': 0, 'tokens': 0}

        def fake_post(url, data, headers, timeout):
            if url == gmail_backend.TOKEN_URL:
                state['tokens'] += 1
                return {'access_token': f'tok-{state["tokens"]}', 'expires_in': 3600}
            state['sends'] += 1
            if state['sends'] == 1:
                raise GmailAPIError('HTTP 401: expired')
            return {'id': 'ok'}

        with mock.patch.object(gmail_backend, '_post', side_effect=fake_post):
            self.assertEqual(GmailAPIBackend().send_messages([self.make_message()]), 1)
        self.assertEqual(state, {'sends': 2, 'tokens': 2})

    def test_fail_silently_returns_zero(self):
        with mock.patch.object(gmail_backend, '_post', side_effect=GmailAPIError('HTTP 403: nope')):
            self.assertEqual(GmailAPIBackend(fail_silently=True).send_messages([self.make_message()]), 0)
            with self.assertRaises(GmailAPIError):
                GmailAPIBackend().send_messages([self.make_message()])
