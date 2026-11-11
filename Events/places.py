"""Места мероприятий: недавние адреса организатора и точка из ссылки на Яндекс / Google / 2ГИС / Mapy.cz / OSM."""
import re
import urllib.error
import urllib.request
from urllib.parse import parse_qs, unquote_plus, urlsplit

from Events.models import Event

# ---------- Недавние места ----------


def recent_places(user, limit=5):
    """Последние разные места организатора (новые первыми) — для подсказки «Мои места» и центра карты."""
    seen = set()
    places = []
    events = (Event.objects.filter(creator=user)
              .exclude(location='', venue_name='')
              .order_by('-created_at')
              .values('venue_name', 'location', 'latitude', 'longitude', 'city', 'country')[:50])
    for event in events:
        key = (event['venue_name'].strip().lower(), event['location'].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        places.append({
            'venue': event['venue_name'],
            'address': event['location'],
            'lat': event['latitude'],
            'lon': event['longitude'],
            'city': event['city'],
            'country': event['country'],
        })
        if len(places) == limit:
            break
    return places


# ---------- Точка из ссылки на карты ----------

# Хосты, к которым сервер вообще готов обращаться (и куда разрешены редиректы) — защита от SSRF
ALLOWED_HOSTS = (
    'google.com', 'google.ru', 'google.kz', 'google.cz', 'goo.gl', 'app.goo.gl',
    'yandex.ru', 'yandex.com', 'yandex.kz', 'yandex.by', 'ya.ru',
    '2gis.ru', '2gis.kz', '2gis.com', 'go.2gis.com',
    'mapy.cz', 'mapy.com',
    'openstreetmap.org', 'osm.org',
    'apple.com',
)
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 5

_NUM = r'(-?\d{1,3}(?:\.\d+)?)'


def is_map_host(host):
    host = (host or '').lower().rstrip('.')
    return any(host == allowed or host.endswith('.' + allowed) for allowed in ALLOWED_HOSTS)


def _valid(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat, lon) != (0.0, 0.0):
        return round(lat, 6), round(lon, 6)
    return None


def _pair(value, lon_first=False):
    match = re.match(rf'\s*{_NUM}\s*,\s*{_NUM}', value or '')
    if not match:
        return None
    a, b = match.groups()
    return _valid(b, a) if lon_first else _valid(a, b)


def parse_map_url(url):
    """{'lat', 'lon', 'venue'} из ссылки на карты или None. Без сети — только разбор строки."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme not in ('http', 'https') or not is_map_host(parts.hostname):
        return None
    host = parts.hostname.lower()
    query = {key: values[-1] for key, values in parse_qs(parts.query).items()}
    path = unquote_plus(parts.path)
    venue = ''
    point = None

    if 'google.' in host:
        place = re.search(r'/maps/place/([^/@]+)', path)
        if place:
            venue = place.group(1).replace('+', ' ').strip()
        precise = re.search(rf'!3d{_NUM}!4d{_NUM}', url)  # точка самого места, точнее центра карты
        if precise:
            point = _valid(*precise.groups())
        for key in ('q', 'query', 'destination', 'daddr', 'll', 'center'):
            point = point or _pair(query.get(key))
        if not point:
            at = re.search(rf'@{_NUM},{_NUM}', path)
            point = _valid(*at.groups()) if at else None
    elif 'yandex.' in host or host.endswith('ya.ru'):
        # У Яндекса порядок «долгота,широта»; pt / whatshere — сама точка, ll — центр карты
        point = _pair(query.get('pt'), lon_first=True) or _pair(query.get('whatshere[point]'), lon_first=True)
        if not point and query.get('rtext'):
            point = _pair(query['rtext'].split('~')[-1])
        point = point or _pair(query.get('ll'), lon_first=True)
    elif '2gis.' in host:
        geo = re.search(rf'/geo/(?:\d+/)?{_NUM},{_NUM}', path)
        point = _valid(geo.group(2), geo.group(1)) if geo else _pair(query.get('m', '').split('/')[0], lon_first=True)
    elif 'mapy.' in host:
        point = _valid(query.get('y'), query.get('x'))
    elif 'openstreetmap.org' in host or 'osm.org' in host:
        point = _valid(query.get('mlat'), query.get('mlon'))
        if not point:
            fragment = re.search(rf'map=\d+/{_NUM}/{_NUM}', parts.fragment)
            point = _valid(*fragment.groups()) if fragment else None
    elif 'apple.com' in host:
        for key in ('coordinate', 'daddr', 'll', 'sll'):
            point = point or _pair(query.get(key))
        venue = query.get('q', '') if point else ''

    if not point:
        return None
    return {'lat': point[0], 'lon': point[1], 'venue': venue[:120]}


class _SafeRedirects(urllib.request.HTTPRedirectHandler):
    """Редирект разрешён только на https-хосты карт и не больше MAX_REDIRECTS раз."""
    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if parts.scheme != 'https' or not is_map_host(parts.hostname):
            raise urllib.error.HTTPError(newurl, code, 'redirect to a non-map host', headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def resolve_map_url(url):
    """Короткие ссылки (maps.app.goo.gl, yandex.ru/maps/-/…, go.2gis.com) раскрываем, проходя по редиректам."""
    parsed = parse_map_url(url)
    if parsed:
        return parsed
    parts = urlsplit(url.strip())
    if parts.scheme != 'https' or not is_map_host(parts.hostname):
        return None
    opener = urllib.request.build_opener(_SafeRedirects)
    request = urllib.request.Request(url.strip(), headers={'User-Agent': 'Mozilla/5.0 (EventTown map link preview)'})
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            # Иногда точка есть только в HTML (meta-теги) — читаем немного начала страницы
            head = response.read(200_000).decode('utf-8', 'ignore')
    except (urllib.error.URLError, OSError, ValueError):
        return None
    parsed = parse_map_url(final_url)
    if parsed:
        return parsed
    # Только meta-теги (og:url, og:image со staticmap) — не случайные ссылки со страницы
    for candidate in re.findall(r'<meta[^>]+content="(https://[^"]+)"', head)[:20]:
        found = parse_map_url(candidate.replace('&amp;', '&'))
        if found:
            return found
    return None
