"""Место мероприятия: название места, «Как найти» (только участникам), маршрут."""
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from Events.models import Event, EventRegistration
from Users.models import User


class PlaceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('host', 'host@example.test', 'Pass12345!x')
        self.guest = User.objects.create_user('guest', 'guest@example.test', 'Pass12345!x')
        self.event = Event.objects.create(
            name='Jazz', event_type='concert', creator=self.owner, date=date.today() + timedelta(days=5), time='19:00',
            venue_name='Лофт «Крыша»', location='ул. Ленина, 5', directions='Подъезд 2, код 1234#',
            latitude=43.2389, longitude=76.8897,
        )
        self.url = reverse('Events:event_detail', args=[self.event.id])

    def test_place_title_joins_venue_and_address(self):
        self.assertEqual(self.event.place_title, 'Лофт «Крыша», ул. Ленина, 5')
        self.assertEqual(Event(location='ул. Ленина, 5').place_title, 'ул. Ленина, 5')
        self.assertEqual(Event(venue_name='Кафе').place_title, 'Кафе')

    def test_directions_hidden_from_strangers(self):
        page = self.client.get(self.url)
        self.assertContains(page, 'Лофт «Крыша»')
        self.assertNotContains(page, 'код 1234')
        self.assertContains(page, 'видны после регистрации')

    def test_directions_visible_to_attendee_and_organizer(self):
        EventRegistration.objects.create(user=self.guest, event=self.event)
        for user in (self.guest, self.owner):
            self.client.force_login(user)
            self.assertContains(self.client.get(self.url), 'код 1234')

    def test_directions_not_in_public_calendar_file(self):
        content = self.client.get(reverse('Events:event_calendar', args=[self.event.id])).content.decode()
        self.assertIn('LOCATION:Лофт «Крыша»', content)
        self.assertNotIn('1234', content)

    def test_route_button_and_remembered_app_markup(self):
        page = self.client.get(self.url)
        self.assertContains(page, 'data-route')
        self.assertContains(page, 'data-app="yandex"')
        self.assertContains(page, 'rtext=')

    def test_form_saves_venue_and_directions(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('Events:create_event'), {
            'name': 'Party', 'event_type': 'concert',
            'date': (date.today() + timedelta(days=3)).strftime('%d.%m.%Y'), 'time': '20:00',
            'venue_name': 'Кафе «Пушкин»', 'location': '', 'directions': 'Вход со двора', 'description': '',
        })
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(name='Party')
        self.assertEqual((event.venue_name, event.directions), ('Кафе «Пушкин»', 'Вход со двора'))
