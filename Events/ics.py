"""Файл .ics (iCalendar) для кнопки «Добавить в календарь»."""
from datetime import datetime, timedelta, timezone as dt_timezone

from django.utils import timezone

DEFAULT_DURATION = timedelta(hours=2)


def _escape(value):
    return (str(value or '')
            .replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
            .replace('\r\n', '\\n').replace('\n', '\\n'))


def _fold(line):
    """Строки длиннее 75 байт переносятся по RFC 5545 (продолжение начинается с пробела)."""
    encoded = line.encode('utf-8')
    if len(encoded) <= 75:
        return line
    parts, current = [], b''
    for char in line:
        char_bytes = char.encode('utf-8')
        if len(current) + len(char_bytes) > (75 if not parts else 74):
            parts.append(current.decode('utf-8'))
            current = b''
        current += char_bytes
    parts.append(current.decode('utf-8'))
    return '\r\n '.join(parts)


def _utc(dt):
    return dt.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def build_ics(event, url, site_host='eventtown'):
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//EventTown//Events//RU',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'BEGIN:VEVENT',
        f'UID:event-{event.id}@{site_host}',
        f'DTSTAMP:{_utc(timezone.now())}',
    ]
    if event.date and event.time:
        start = timezone.make_aware(datetime.combine(event.date, event.time), timezone.get_current_timezone())
        lines += [f'DTSTART:{_utc(start)}', f'DTEND:{_utc(start + DEFAULT_DURATION)}']
    elif event.date:
        lines += [
            f'DTSTART;VALUE=DATE:{event.date:%Y%m%d}',
            f'DTEND;VALUE=DATE:{event.date + timedelta(days=1):%Y%m%d}',
        ]
    lines += [
        f'SUMMARY:{_escape(event.name)}',
        f'DESCRIPTION:{_escape((event.description or "") + chr(10) + chr(10) + url)}',
        f'URL:{url}',
    ]
    if event.location:
        lines.append(f'LOCATION:{_escape(event.location)}')
    if event.latitude is not None and event.longitude is not None:
        lines.append(f'GEO:{event.latitude:.6f};{event.longitude:.6f}')
    lines += ['END:VEVENT', 'END:VCALENDAR']
    return '\r\n'.join(_fold(line) for line in lines) + '\r\n'
