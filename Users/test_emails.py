import re
from io import StringIO
from datetime import date, time, timedelta

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from Events.models import Event, EventRegistration
from Users.models import User


def html_of(message):
    return message.alternatives[0][0]


class ConfirmationEmailTests(TestCase):
    def setUp(self):
        cache.clear()

    def register(self, language='ru'):
        self.client.get(reverse('Users:set_language', args=[language]))
        return self.client.post(reverse('Users:registration'), {
            'username': 'newbie', 'email': 'newbie@example.test', 'birthDate': '01.01.2000',
            'password1': 'Sup3r-Secret!', 'password2': 'Sup3r-Secret!',
        })

    def test_registration_sends_html_email_with_code(self):
        self.register()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Подтвердите email в EventTown')
        code = re.search(r'\b(\d{6})\b', message.body).group(1)
        self.assertIn(code, html_of(message))
        self.assertIn('/Users/Confirm/', message.body)
        user = User.objects.get(username='newbie')
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.email_confirmation_sent_at)
        self.assertEqual(user.language, 'ru')

        self.client.post(reverse('Users:confirm_email_code'), {'email': 'newbie@example.test', 'code': code})
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_email_language_follows_user(self):
        self.register('cs')
        self.assertEqual(mail.outbox[0].subject, 'Potvrďte svůj e-mail na EventTown')
        self.assertIn('Váš potvrzovací kód', html_of(mail.outbox[0]))

    def test_expired_code_is_rejected(self):
        self.register()
        code = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)
        User.objects.filter(username='newbie').update(
            email_confirmation_sent_at=timezone.now() - timedelta(hours=1)
        )
        self.client.post(reverse('Users:confirm_email_code'), {'email': 'newbie@example.test', 'code': code})
        self.assertFalse(User.objects.get(username='newbie').is_active)

    def test_resend_sends_new_code_with_cooldown(self):
        self.register()
        url = reverse('Users:resend_confirmation')
        self.client.post(url, {'email': 'newbie@example.test'})
        self.assertEqual(len(mail.outbox), 2)
        self.client.post(url, {'email': 'newbie@example.test'})
        self.assertEqual(len(mail.outbox), 2)  # cooldown

    def test_resend_does_not_reveal_unknown_email(self):
        response = self.client.post(reverse('Users:resend_confirmation'), {'email': 'ghost@example.test'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)


class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('bob', 'bob@example.test', 'Old-pass-123', language='en')

    def test_reset_flow(self):
        response = self.client.post(reverse('Users:password_reset'), {'email': 'bob@example.test'})
        self.assertRedirects(response, reverse('Users:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Reset your EventTown password')
        link = re.search(r'https?://\S+/Users/Password-reset/\S+/', mail.outbox[0].body).group(0)
        path = link.split('testserver', 1)[1]

        response = self.client.get(path, follow=True)  # Django swaps the token for a session key
        form_url = response.redirect_chain[-1][0]
        response = self.client.post(form_url, {'new_password1': 'N3w-pass-456!', 'new_password2': 'N3w-pass-456!'})
        self.assertRedirects(response, reverse('Users:password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('N3w-pass-456!'))

    def test_unknown_email_sends_nothing(self):
        response = self.client.post(reverse('Users:password_reset'), {'email': 'nobody@example.test'})
        self.assertRedirects(response, reverse('Users:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_is_throttled(self):
        url = reverse('Users:password_reset')
        self.client.post(url, {'email': 'bob@example.test'})
        self.client.post(url, {'email': 'bob@example.test'})
        self.assertEqual(len(mail.outbox), 1)


class EventNotificationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('host', 'host@example.test', 'Pass12345!x')
        self.fan = User.objects.create_user('fan', 'fan@example.test', 'Pass12345!x', language='en')
        self.quiet = User.objects.create_user('quiet', 'quiet@example.test', 'Pass12345!x', email_notifications=False)
        self.event = Event.objects.create(
            name='Rooftop jazz', date=date.today() + timedelta(days=10), time=time(19, 0),
            location='Abay 10', creator=self.owner,
        )
        EventRegistration.objects.create(user=self.owner, event=self.event)

    def test_registration_email(self):
        self.client.force_login(self.fan)
        self.client.post(reverse('Events:register_event', args=[self.event.id]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['fan@example.test'])
        self.assertEqual(mail.outbox[0].subject, "You're going: Rooftop jazz")
        html = html_of(mail.outbox[0])
        self.assertIn('/static/img/logo-mark.png', html)
        self.assertIn(f'/Event/{self.event.id}/calendar.ics', html)

    def test_opted_out_user_gets_no_email(self):
        self.client.force_login(self.quiet)
        self.client.post(reverse('Events:register_event', args=[self.event.id]))
        self.assertEqual(len(mail.outbox), 0)

    def test_update_notifies_participants_but_not_creator(self):
        EventRegistration.objects.create(user=self.fan, event=self.event)
        EventRegistration.objects.create(user=self.quiet, event=self.event)
        self.event.reminder_sent = True
        self.event.save()
        new_date = date.today() + timedelta(days=12)
        self.client.force_login(self.owner)
        self.client.post(reverse('Events:edit_event', args=[self.event.id]), {
            'name': 'Rooftop jazz', 'event_type': 'concert', 'date': new_date.strftime('%d.%m.%Y'),
            'time': '20:00', 'location': 'Abay 10', 'description': '',
        })
        self.assertEqual([m.to for m in mail.outbox], [['fan@example.test']])
        body = mail.outbox[0].body
        self.assertIn('19:00 → 20:00', body)
        self.event.refresh_from_db()
        self.assertFalse(self.event.reminder_sent)

    def test_no_email_when_nothing_relevant_changed(self):
        EventRegistration.objects.create(user=self.fan, event=self.event)
        self.client.force_login(self.owner)
        self.client.post(reverse('Events:edit_event', args=[self.event.id]), {
            'name': 'Rooftop jazz', 'event_type': 'concert', 'date': self.event.date.strftime('%d.%m.%Y'),
            'time': '19:00', 'location': 'Abay 10', 'description': 'New description',
        })
        self.assertEqual(len(mail.outbox), 0)

    def test_delete_sends_cancellation(self):
        EventRegistration.objects.create(user=self.fan, event=self.event)
        self.client.force_login(self.owner)
        self.client.post(reverse('Events:delete_event', args=[self.event.id]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Event cancelled: Rooftop jazz')

    def test_reminders_command(self):
        EventRegistration.objects.create(user=self.fan, event=self.event)
        self.event.date = timezone.localdate() + timedelta(days=1)
        self.event.save()
        call_command('send_event_reminders', stdout=StringIO())
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ['fan@example.test', 'host@example.test'])
        self.event.refresh_from_db()
        self.assertTrue(self.event.reminder_sent)

        call_command('send_event_reminders', stdout=StringIO())
        self.assertEqual(len(mail.outbox), 2)  # no duplicates


class BackgroundEmailTests(TestCase):
    def test_in_background_runs_after_commit_in_a_thread(self):
        import threading
        from django.test import override_settings
        from Users.emails import in_background

        done = threading.Event()
        seen = {}

        def task(value):
            seen['value'] = value
            seen['thread'] = threading.current_thread().name
            done.set()

        with override_settings(EMAIL_ASYNC=True):
            with self.captureOnCommitCallbacks(execute=True):
                self.assertIsNone(in_background(task, 42))
                self.assertFalse(done.is_set())  # до коммита ничего не уходит
        self.assertTrue(done.wait(5))
        self.assertEqual(seen, {'value': 42, 'thread': 'email'})

    def test_sync_when_disabled(self):
        from Users.emails import in_background
        self.assertEqual(in_background(lambda x: x * 2, 21), 42)
