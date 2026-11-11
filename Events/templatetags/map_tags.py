from urllib.parse import quote, urlencode

from django import template

register = template.Library()


def _coords(event):
    if event.latitude is None or event.longitude is None:
        return None
    return f'{event.latitude:.6f}', f'{event.longitude:.6f}'


def build_map_links(event):
    """Ссылки на внешние карты. Если есть координаты — точная точка, иначе поиск по адресу."""
    address = (event.location or '').strip()
    coords = _coords(event)
    links = {}

    if coords:
        lat, lon = coords
        # Google, Яндекс и Apple — сразу маршрут до точки (на телефоне откроется приложение)
        links['google'] = 'https://www.google.com/maps/dir/?' + urlencode({'api': 1, 'destination': f'{lat},{lon}'})
        links['yandex'] = 'https://yandex.ru/maps/?' + urlencode({'rtext': f'~{lat},{lon}', 'rtt': 'auto', 'pt': f'{lon},{lat}', 'z': 17})
        links['2gis'] = f'https://2gis.ru/geo/{lon},{lat}'
        links['apple'] = 'https://maps.apple.com/?' + urlencode({'daddr': f'{lat},{lon}', 'q': address or event.name})
        links['mapy'] = 'https://mapy.cz/zakladni?' + urlencode({'x': lon, 'y': lat, 'z': 17, 'source': 'coor', 'id': f'{lon},{lat}'})
        links['osm'] = f'https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}'
        links['waze'] = 'https://waze.com/ul?' + urlencode({'ll': f'{lat},{lon}', 'navigate': 'yes'})
    elif address:
        links['google'] = 'https://www.google.com/maps/dir/?' + urlencode({'api': 1, 'destination': address})
        links['yandex'] = 'https://yandex.ru/maps/?' + urlencode({'text': address})
        links['2gis'] = 'https://2gis.ru/search/' + quote(address, safe='')
        links['apple'] = 'https://maps.apple.com/?' + urlencode({'q': address})
        links['mapy'] = 'https://mapy.cz/zakladni?' + urlencode({'q': address})
        links['osm'] = 'https://www.openstreetmap.org/search?' + urlencode({'query': address})
        links['waze'] = 'https://waze.com/ul?' + urlencode({'q': address, 'navigate': 'yes'})
    return links


PROVIDERS = {
    'yandex': ('Яндекс Карты', 'Yandex Maps', 'Yandex Mapy', '#FC3F1D'),
    '2gis': ('2ГИС', '2GIS', '2GIS', '#1BA136'),
    'google': ('Google Карты', 'Google Maps', 'Mapy Google', '#1A73E8'),
    'apple': ('Apple Карты', 'Apple Maps', 'Apple Mapy', '#111111'),
    'mapy': ('Mapy.cz', 'Mapy.cz', 'Mapy.cz', '#E5262B'),
    'waze': ('Waze — маршрут', 'Waze — directions', 'Waze — trasa', '#33CCFF'),
    'osm': ('OpenStreetMap', 'OpenStreetMap', 'OpenStreetMap', '#7EBC6F'),
}

ORDER = {
    'ru': ('yandex', '2gis', 'google', 'apple', 'waze', 'osm', 'mapy'),
    'en': ('google', 'apple', 'waze', 'osm', 'yandex', '2gis', 'mapy'),
    'cs': ('mapy', 'google', 'apple', 'waze', 'osm', 'yandex', '2gis'),
}


@register.simple_tag(takes_context=True)
def map_links(context, event):
    language = context.get('LANGUAGE_CODE', 'ru')
    index = {'ru': 0, 'en': 1, 'cs': 2}.get(language, 0)
    links = build_map_links(event)
    result = []
    for key in ORDER.get(language, ORDER['ru']):
        if key in links:
            names = PROVIDERS[key]
            result.append({'key': key, 'name': names[index], 'url': links[key], 'color': names[3]})
    return result
