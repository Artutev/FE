from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from Events.models import Event, EventRegistration
from Events.templatetags.map_tags import build_map_links
from Users.models import User


class EventAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@example.test', 'Pass12345!x')
        self.guest = User.objects.create_user('guest', 'guest@example.test', 'Pass12345!x')
        future = date.today() + timedelta(days=5)
        self.public = Event.objects.create(name='Public', date=future, creator=self.owner)
        self.private = Event.objects.create(
            name='Secret wedding', event_type='wedding', is_private=True, date=future, creator=self.owner,
        )
        self.past = Event.objects.create(name='Old', date=date.today() - timedelta(days=5), creator=self.owner)

    def test_private_event_requires_token(self):
        self.client.force_login(self.guest)
        url = reverse('Events:event_detail', args=[self.private.id])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(f'{url}?token={self.private.access_token}').status_code, 200)

    def test_owner_sees_private_event_without_token(self):
        self.client.force_login(self.owner)
        url = reverse('Events:event_detail', args=[self.private.id])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_invitation_requires_token(self):
        self.client.force_login(self.guest)
        url = reverse('Events:download_invitation', args=[self.private.id])
        self.assertEqual(self.client.get(url).status_code, 404)
        response = self.client.get(f'{url}?token={self.private.access_token}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])

    def test_register_requires_post(self):
        self.client.force_login(self.guest)
        url = reverse('Events:register_event', args=[self.public.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertTrue(EventRegistration.objects.filter(user=self.guest, event=self.public).exists())

    def test_unregister_requires_post(self):
        EventRegistration.objects.create(user=self.guest, event=self.public)
        self.client.force_login(self.guest)
        url = reverse('Events:unregister_event', args=[self.public.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertFalse(EventRegistration.objects.filter(user=self.guest, event=self.public).exists())

    def test_cannot_register_for_past_event(self):
        self.client.force_login(self.guest)
        self.client.post(reverse('Events:register_event', args=[self.past.id]))
        self.assertFalse(EventRegistration.objects.filter(user=self.guest, event=self.past).exists())

    def test_only_creator_can_edit(self):
        self.client.force_login(self.guest)
        self.assertEqual(self.client.get(reverse('Events:edit_event', args=[self.public.id])).status_code, 404)

    def test_has_passed(self):
        self.assertTrue(self.past.has_passed)
        self.assertFalse(self.public.has_passed)


class EventListTests(TestCase):
    def test_list_hides_private_and_past(self):
        future = date.today() + timedelta(days=2)
        Event.objects.create(name='Visible', date=future)
        Event.objects.create(name='Hidden', date=future, is_private=True)
        Event.objects.create(name='Gone', date=date.today() - timedelta(days=2))
        content = self.client.get(reverse('Events:event_list')).content.decode()
        self.assertIn('Visible', content)
        self.assertNotIn('Hidden', content)
        self.assertNotIn('Gone', content)


class MapLinksTests(TestCase):
    def test_links_use_coordinates_when_available(self):
        event = Event(name='Jazz', location='Abay 10', latitude=43.2389, longitude=76.8897)
        links = build_map_links(event)
        self.assertIn('2gis.ru/geo/76.889700,43.238900', links['2gis'])
        self.assertIn('pt=76.889700%2C43.238900', links['yandex'])

    def test_links_fall_back_to_address(self):
        links = build_map_links(Event(name='Jazz', location='Abay 10'))
        self.assertIn('text=Abay+10', links['yandex'])
        self.assertIn('query=Abay+10', links['google'])

    def test_no_links_without_location(self):
        self.assertEqual(build_map_links(Event(name='Jazz')), {})


class CalendarFileTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('cal_owner', 'cal@example.test', 'Pass12345!x')

    def test_ics_for_public_event(self):
        from datetime import time
        event = Event.objects.create(
            name='Jazz, rooftop; night', date=date.today() + timedelta(days=3), time=time(19, 0),
            location='Abay 10', creator=self.owner,
        )
        response = self.client.get(reverse('Events:event_calendar', args=[event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/calendar; charset=utf-8')
        body = response.content.decode()
        self.assertIn('BEGIN:VEVENT', body)
        self.assertIn('SUMMARY:Jazz\, rooftop\; night', body)
        self.assertIn('LOCATION:Abay 10', body)
        self.assertRegex(body, r'DTSTART:\d{8}T\d{6}Z')

    def test_ics_all_day_without_time(self):
        event = Event.objects.create(name='Fair', date=date.today() + timedelta(days=3), creator=self.owner)
        body = self.client.get(reverse('Events:event_calendar', args=[event.id])).content.decode()
        self.assertIn('DTSTART;VALUE=DATE:', body)

    def test_ics_private_event_requires_token(self):
        event = Event.objects.create(name='Secret', date=date.today() + timedelta(days=3),
                                     creator=self.owner, is_private=True)
        url = reverse('Events:event_calendar', args=[event.id])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(f'{url}?token={event.access_token}').status_code, 200)


class CreatedEmailTests(TestCase):
    def test_creator_gets_email_with_private_link(self):
        from django.core import mail
        owner = User.objects.create_user('host', 'host@example.test', 'Pass12345!x')
        self.client.force_login(owner)
        response = self.client.post(reverse('Events:create_event'), {
            'name': 'Квартирник', 'event_type': 'other', 'is_private': 'on',
            'date': (date.today() + timedelta(days=3)).isoformat(), 'time': '19:00',
            'description': '', 'location': '',
        })
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(name='Квартирник')
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['host@example.test'])
        self.assertIn('Квартирник', message.subject)
        self.assertIn(f'token={event.access_token}', message.body)

    def test_no_email_when_notifications_are_off(self):
        from django.core import mail
        owner = User.objects.create_user('quiet', 'quiet@example.test', 'Pass12345!x', email_notifications=False)
        self.client.force_login(owner)
        self.client.post(reverse('Events:create_event'), {
            'name': 'Тихо', 'event_type': 'other',
            'date': (date.today() + timedelta(days=3)).isoformat(), 'time': '19:00',
        })
        self.assertTrue(Event.objects.filter(name='Тихо').exists())
        self.assertEqual(len(mail.outbox), 0)


class InviteFriendsTests(TestCase):
    def setUp(self):
        from Users.models import FriendRequest
        self.ann = User.objects.create_user('ann', 'ann@example.test', 'Pass12345!x')
        self.bob = User.objects.create_user('bob', 'bob@example.test', 'Pass12345!x')
        self.cat = User.objects.create_user('cat', 'cat@example.test', 'Pass12345!x')
        self.eve = User.objects.create_user('eve', 'eve@example.test', 'Pass12345!x')  # не друг
        for friend in (self.bob, self.cat):
            FriendRequest.objects.create(from_user=self.ann, to_user=friend, status='accepted')
        future = date.today() + timedelta(days=4)
        self.event = Event.objects.create(name='Jazz', date=future, creator=self.ann)
        self.private = Event.objects.create(name='Secret', date=future, is_private=True, creator=self.ann)
        self.client.force_login(self.ann)

    def invite(self, event, *users, token=''):
        url = reverse('Events:invite_friends', args=[event.id]) + (f'?token={token}' if token else '')
        return self.client.post(url, {'friends': [u.pk for u in users]})

    def test_invite_sends_chat_message_with_link(self):
        from Chat.models import Message
        from Events.models import EventInvite
        self.invite(self.event, self.bob, self.eve)
        self.assertEqual(list(EventInvite.objects.values_list('invitee__username', flat=True)), ['bob'])
        message = Message.objects.get()
        self.assertEqual(message.author, self.ann)
        self.assertIn('Jazz', message.text)
        self.assertIn(reverse('Events:event_detail', args=[self.event.id]), message.text)
        self.assertEqual(
            set(message.conversation.memberships.values_list('user__username', flat=True)), {'ann', 'bob'},
        )

    def test_no_duplicates_and_registered_friends_skipped(self):
        from Chat.models import Message
        EventRegistration.objects.create(user=self.cat, event=self.event)
        self.invite(self.event, self.bob, self.cat)
        self.invite(self.event, self.bob)
        self.assertEqual(Message.objects.count(), 1)

    def test_private_invite_contains_token(self):
        from Chat.models import Message
        self.invite(self.private, self.bob)
        self.assertIn(f'token={self.private.access_token}', Message.objects.get().text)

    def test_stranger_cannot_invite_to_private_event_without_token(self):
        self.client.force_login(self.bob)
        self.assertEqual(self.invite(self.private, self.cat).status_code, 404)

    def test_cannot_invite_to_past_event(self):
        from Events.models import EventInvite
        past = Event.objects.create(name='Old', date=date.today() - timedelta(days=2), creator=self.ann)
        self.invite(past, self.bob)
        self.assertFalse(EventInvite.objects.exists())

    def test_detail_page_lists_friends_with_status(self):
        EventRegistration.objects.create(user=self.cat, event=self.event)
        content = self.client.get(reverse('Events:event_detail', args=[self.event.id])).content.decode()
        self.assertIn('id="inviteSheet"', content)
        self.assertIn(f'value="{self.bob.pk}"', content)
        self.assertIn('invite-tag--going', content)
        self.assertNotIn(f'value="{self.eve.pk}"', content)
