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
