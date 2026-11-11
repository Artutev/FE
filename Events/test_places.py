"""Место мероприятия: название места, «Как найти» (только участникам), маршрут."""
from datetime import date, timedelta

from unittest import mock

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


class MapLinkTests(TestCase):
    def test_parse_common_links(self):
        from Events.places import parse_map_url
        cases = {
            'https://www.google.com/maps/place/Caf%C3%A9+Pushkin/@55.7638,37.6047,17z/data=!3m1!4b1!4m6!3m5!1s0x0:0x0!8m2!3d55.763835!4d37.604689':
                (55.763835, 37.604689, 'Café Pushkin'),
            'https://www.google.com/maps/dir/?api=1&destination=43.2389,76.8897': (43.2389, 76.8897, ''),
            'https://yandex.ru/maps/213/moscow/?ll=37.617635%2C55.755814&pt=37.611644%2C55.758310&z=17':
                (55.75831, 37.611644, ''),
            'https://yandex.kz/maps/?whatshere%5Bpoint%5D=76.889709%2C43.238949&z=17': (43.238949, 76.889709, ''),
            'https://2gis.kz/almaty/geo/9430047375011839/76.889700,43.238900': (43.2389, 76.8897, ''),
            'https://mapy.cz/zakladni?x=14.4378&y=50.0755&z=17': (50.0755, 14.4378, ''),
            'https://www.openstreetmap.org/#map=17/50.07550/14.43780': (50.0755, 14.4378, ''),
            'https://maps.apple.com/?ll=50.0755,14.4378&q=Kavárna': (50.0755, 14.4378, 'Kavárna'),
        }
        for url, (lat, lon, venue) in cases.items():
            found = parse_map_url(url)
            self.assertIsNotNone(found, url)
            self.assertAlmostEqual(found['lat'], lat, places=5, msg=url)
            self.assertAlmostEqual(found['lon'], lon, places=5, msg=url)
            self.assertEqual(found['venue'], venue, url)

    def test_rejects_non_map_hosts_and_garbage(self):
        from Events.places import parse_map_url, resolve_map_url
        for url in ('https://evil.example/maps?ll=1,2', 'http://127.0.0.1/?q=55,37', 'https://google.com.evil.io/@55,37',
                    'javascript:alert(1)', 'not a link', 'https://www.google.com/maps/@0,0,3z'):
            self.assertIsNone(parse_map_url(url), url)
        with mock.patch('urllib.request.OpenerDirector.open') as opener:
            self.assertIsNone(resolve_map_url('https://169.254.169.254/latest/meta-data'))
            self.assertIsNone(resolve_map_url('http://maps.app.goo.gl/abc'))  # только https
            opener.assert_not_called()

    def test_redirect_to_other_host_is_blocked(self):
        from Events.places import _SafeRedirects
        import urllib.error
        handler = _SafeRedirects()
        with self.assertRaises(urllib.error.HTTPError):
            handler.redirect_request(None, None, 302, 'Found', {}, 'https://169.254.169.254/')

    def test_endpoint(self):
        url = reverse('Events:map_link')
        self.assertEqual(self.client.get(url, {'url': 'x'}).status_code, 302)  # только после входа
        self.client.force_login(User.objects.create_user('host', 'h@example.test', 'Pass12345!x'))
        response = self.client.get(url, {'url': 'https://mapy.cz/zakladni?x=14.4378&y=50.0755'})
        self.assertEqual(response.json()['lat'], 50.0755)
        with mock.patch('Events.places.resolve_map_url', return_value=None):
            self.assertEqual(self.client.get(url, {'url': 'https://maps.app.goo.gl/x'}).status_code, 404)

    def test_endpoint_is_rate_limited(self):
        from django.core.cache import cache
        cache.clear()
        self.client.force_login(User.objects.create_user('host', 'h@example.test', 'Pass12345!x'))
        url = reverse('Events:map_link')
        with mock.patch('Events.places.resolve_map_url', return_value=None):
            codes = [self.client.get(url, {'url': 'https://maps.app.goo.gl/x'}).status_code for _ in range(31)]
        self.assertEqual(codes[-1], 429)


class RecentPlacesTests(TestCase):
    def test_recent_places_are_distinct_and_shown_on_form(self):
        from Events.places import recent_places
        owner = User.objects.create_user('host', 'h@example.test', 'Pass12345!x')
        for name in ('A', 'B'):
            Event.objects.create(name=name, creator=owner, venue_name='Лофт', location='ул. Ленина, 5',
                                 latitude=55.75, longitude=37.61)
        Event.objects.create(name='C', creator=owner, location='Тверская 7')
        Event.objects.create(name='Other', creator=User.objects.create_user('x', 'x@example.test', 'Pass12345!x'),
                             location='Чужой адрес')
        places = recent_places(owner)
        self.assertEqual([p['address'] for p in places], ['Тверская 7', 'ул. Ленина, 5'])
        self.client.force_login(owner)
        page = self.client.get(reverse('Events:create_event'))
        self.assertContains(page, 'loc-recent-chip')
        self.assertNotContains(page, 'Чужой адрес')


class OnlineAndCityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('host', 'h@example.test', 'Pass12345!x')
        self.soon = date.today() + timedelta(days=4)

    def test_online_event_hides_place_and_shows_link_to_attendees(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('Events:create_event'), {
            'name': 'Webinar', 'event_type': 'lecture', 'date': self.soon.strftime('%d.%m.%Y'), 'time': '18:00',
            'is_online': 'on', 'online_url': 'https://meet.example.test/abc',
            'location': 'Старый адрес', 'venue_name': 'Лофт', 'latitude': '55.7', 'longitude': '37.6', 'city': 'Москва',
            'description': '',
        })
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(name='Webinar')
        self.assertTrue(event.is_online)
        self.assertEqual((event.location, event.venue_name, event.city, event.latitude), ('', '', '', None))
        url = reverse('Events:event_detail', args=[event.id])
        self.assertContains(self.client.get(url), 'https://meet.example.test/abc')  # организатор
        guest = User.objects.create_user('guest', 'g@example.test', 'Pass12345!x')
        self.client.force_login(guest)
        page = self.client.get(url)
        self.assertNotContains(page, 'meet.example.test')
        self.assertContains(page, 'Ссылка появится после регистрации')
        EventRegistration.objects.create(user=guest, event=event)
        self.assertContains(self.client.get(url), 'https://meet.example.test/abc')

    def test_online_url_dropped_for_offline_event(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('Events:create_event'), {
            'name': 'Party', 'event_type': 'other', 'date': self.soon.strftime('%d.%m.%Y'), 'time': '18:00',
            'online_url': 'https://meet.example.test/x', 'location': 'ул. Ленина, 5', 'city': 'Москва', 'description': '',
        })
        event = Event.objects.get(name='Party')
        self.assertEqual((event.online_url, event.city), ('', 'Москва'))

    def test_city_filter_and_map_view(self):
        Event.objects.create(name='Moscow jazz', creator=self.owner, date=self.soon, city='Москва',
                             location='Тверская 7', latitude=55.758, longitude=37.611)
        Event.objects.create(name='Prague talk', creator=self.owner, date=self.soon, city='Praha')
        Event.objects.create(name='Webinar', creator=self.owner, date=self.soon, is_online=True)
        url = reverse('Events:event_list')
        page = self.client.get(url)
        self.assertEqual(set(page.context['cities']), {'Москва', 'Praha'})
        self.assertTrue(page.context['has_online'])
        names = lambda r: [e.name for e in r.context['events']]
        self.assertEqual(names(self.client.get(url, {'city': 'москва'})), ['Moscow jazz'])
        self.assertEqual(names(self.client.get(url, {'city': 'online'})), ['Webinar'])
        page = self.client.get(url, {'view': 'map', 'city': 'Москва'})
        self.assertEqual([p['name'] for p in page.context['map_points']], ['Moscow jazz'])
        self.assertContains(page, 'eventsMapData')
        self.assertContains(page, 'markercluster')
        # Чипы сохраняют остальные фильтры
        self.assertContains(page, 'view=map&amp;city=Praha')

    def test_fill_event_cities_command(self):
        from io import StringIO
        from django.core.management import call_command
        event = Event.objects.create(name='Old', creator=self.owner, date=self.soon, latitude=50.08, longitude=14.43)
        with mock.patch('Events.management.commands.fill_event_cities.reverse_city', return_value=('Praha', 'Česko')), \
                mock.patch('Events.management.commands.fill_event_cities.time.sleep'):
            call_command('fill_event_cities', '--dry-run', stdout=StringIO())
            event.refresh_from_db()
            self.assertEqual(event.city, '')
            call_command('fill_event_cities', stdout=StringIO())
        event.refresh_from_db()
        self.assertEqual((event.city, event.country), ('Praha', 'Česko'))
