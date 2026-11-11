"""Проставить город и страну мероприятиям, у которых есть точка на карте, но город пустой.

Нужно один раз после появления фильтра по городу: новые мероприятия получают город из подсказки адреса сами.
Запрос к Photon (komoot) — не чаще раза в секунду, чтобы не нагружать публичный сервис.

    python manage.py fill_event_cities --dry-run
    python manage.py fill_event_cities
"""
import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

from django.core.management.base import BaseCommand

from Events.models import Event

PHOTON_REVERSE = 'https://photon.komoot.io/reverse'


def reverse_city(lat, lon):
    url = f'{PHOTON_REVERSE}?{urlencode({"lat": lat, "lon": lon, "lang": "default", "limit": 1})}'
    request = urllib.request.Request(url, headers={'User-Agent': 'EventTown city backfill'})
    with urllib.request.urlopen(request, timeout=10) as response:
        features = json.load(response).get('features') or []
    if not features:
        return '', ''
    props = features[0].get('properties') or {}
    city = props.get('city') or props.get('town') or props.get('village') or props.get('county') or ''
    return city[:100], (props.get('country') or '')[:100]


class Command(BaseCommand):
    help = 'Fill Event.city / Event.country from coordinates (Photon reverse geocoding).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would change, save nothing.')

    def handle(self, *args, dry_run=False, **options):
        events = Event.objects.filter(city='', is_online=False, latitude__isnull=False, longitude__isnull=False)
        filled = failed = 0
        for event in events.iterator():
            try:
                city, country = reverse_city(event.latitude, event.longitude)
            except (urllib.error.URLError, OSError, ValueError) as error:
                failed += 1
                self.stderr.write(f'#{event.id}: {error}')
                continue
            if city:
                filled += 1
                if not dry_run:
                    Event.objects.filter(pk=event.pk).update(city=city, country=country)
                self.stdout.write(f'#{event.id}: {city}, {country}')
            time.sleep(1)
        self.stdout.write(self.style.SUCCESS(
            f'{"Would fill" if dry_run else "Filled"} {filled} event(s); failed {failed}.'
        ))
