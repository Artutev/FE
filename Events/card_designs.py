"""Каталог дизайнов пригласительных: шаблоны, палитры, шрифты, форматы.

Шаблон задаёт вёрстку (CSS-класс .ic--<template> в static/css/invite_card.css),
палитра — пять цветов, шрифт — пара «заголовки / текст». Всё это только данные:
новые палитры и шрифты добавляются здесь, без миграций.
"""

# Палитра: bg — фон, bg2 — второй цвет фона/украшений, fg — текст, muted — второстепенный текст, accent — акцент
TEMPLATES = {
    'classic': {
        'name': ('Классика', 'Classic'),
        'font': 'serif',
        'palettes': {
            'ivory': ('Слоновая кость', 'Ivory', '#FBF7EF', '#EADBC0', '#2B2118', '#7A6A55', '#B08D57'),
            'blush': ('Пудровый', 'Blush', '#FBF1EF', '#F0D3CD', '#3A2226', '#8A6468', '#C27B7F'),
            'sage': ('Шалфей', 'Sage', '#F3F5EE', '#D5DFC8', '#24301F', '#66745C', '#7E9467'),
            'navy': ('Ночь и золото', 'Navy & gold', '#1B2338', '#2C3756', '#F5EEDF', '#B9B0A0', '#D4AF6A'),
        },
    },
    'party': {
        'name': ('Вечеринка', 'Party'),
        'font': 'grotesk',
        'palettes': {
            'neon': ('Неон', 'Neon', '#130B2E', '#6D28D9', '#FFFFFF', '#D6CCF7', '#F0ABFC'),
            'sunset': ('Закат', 'Sunset', '#2A0E1F', '#C2255C', '#FFF7ED', '#FBD5C0', '#FDBA74'),
            'electric': ('Электрик', 'Electric', '#04121F', '#0E7490', '#F0FDFF', '#B5E6F2', '#5EEAD4'),
            'lime': ('Лайм', 'Lime', '#0F0F0F', '#3F3F46', '#FAFAFA', '#C4C4C4', '#D9F99D'),
        },
    },
    'minimal': {
        'name': ('Минимал', 'Minimal'),
        'font': 'clean',
        'palettes': {
            'paper': ('Бумага', 'Paper', '#FFFFFF', '#EDEDF0', '#0A0A0A', '#6B6B6B', '#7C3AED'),
            'sand': ('Песок', 'Sand', '#F6F1EA', '#E6DACA', '#1F1A14', '#7B6F61', '#C2410C'),
            'graphite': ('Графит', 'Graphite', '#18181B', '#2E2E33', '#FAFAFA', '#A1A1AA', '#A78BFA'),
            'mint': ('Мята', 'Mint', '#F0FDF8', '#C9F3E1', '#06281C', '#4B6B5E', '#059669'),
        },
    },
    'kids': {
        'name': ('Детский', 'Kids'),
        'font': 'rounded',
        'palettes': {
            'candy': ('Конфета', 'Candy', '#FFF1F7', '#FFC9E0', '#3B1030', '#8E5A7E', '#EC4899'),
            'sky': ('Небо', 'Sky', '#EEF7FF', '#BFDDFF', '#0F2A4A', '#5A7593', '#3B82F6'),
            'sunny': ('Солнце', 'Sunny', '#FFFBEB', '#FDE68A', '#3A2A05', '#86703A', '#F59E0B'),
            'leaf': ('Листик', 'Leaf', '#ECFDF5', '#A7F3D0', '#073B2A', '#4E7A68', '#10B981'),
        },
    },
    'ticket': {
        'name': ('Билет', 'Ticket'),
        'font': 'clean',
        'palettes': {
            'grape': ('Виноград', 'Grape', '#F4F2F8', '#7C3AED', '#18122B', '#6B6880', '#7C3AED'),
            'night': ('Ночь', 'Night', '#0D0A17', '#7C3AED', '#F5F3FF', '#A09CB5', '#C4B5FD'),
            'coral': ('Коралл', 'Coral', '#FFF4F1', '#F97362', '#2A1410', '#86615A', '#E2553F'),
            'ocean': ('Океан', 'Ocean', '#EFF6FF', '#2563EB', '#0B1B3A', '#5B6B86', '#2563EB'),
        },
    },
}

# Пары шрифтов (все с кириллицей): ключ → (заголовки, текст, подпись ru, en)
FONTS = {
    'serif': ('Cormorant Garamond', 'Onest', 'Изящный', 'Elegant'),
    'script': ('Marck Script', 'Cormorant Garamond', 'Рукописный', 'Handwritten'),
    'grotesk': ('Unbounded', 'Onest', 'Смелый', 'Bold'),
    'clean': ('Onest', 'Onest', 'Чистый', 'Clean'),
    'rounded': ('Comfortaa', 'Nunito', 'Мягкий', 'Soft'),
}

GOOGLE_FONTS_URL = (
    'https://fonts.googleapis.com/css2'
    '?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500'
    '&family=Marck+Script'
    '&family=Unbounded:wght@500;700;800'
    '&family=Comfortaa:wght@500;700'
    '&family=Nunito:wght@500;700'
    '&family=Onest:wght@400;500;600;700;800'
    '&display=swap'
)

# Формат: (подпись ru, en, ширина, высота) — размеры «холста» в CSS-пикселях; PNG экспортируется в 2×
FORMATS = {
    'story': ('Сторис 9:16', 'Story 9:16', 540, 960),
    'square': ('Квадрат 1:1', 'Square 1:1', 640, 640),
    'a5': ('Открытка A5', 'Postcard A5', 560, 794),
}

BACKGROUNDS = {
    'decor': ('С украшениями', 'Decorated'),
    'plain': ('Без украшений', 'Plain'),
    'cover': ('Обложка мероприятия', 'Event cover'),
}

# Шаблон по умолчанию для типа мероприятия
DEFAULT_TEMPLATE = {
    'wedding': 'classic',
    'concert': 'party',
    'theater': 'classic',
    'cinema': 'party',
    'exhibition': 'minimal',
    'lecture': 'minimal',
    'other': 'ticket',
}

DEFAULT_MESSAGE = {
    'wedding': ('Будем счастливы разделить с вами этот день', 'We would be happy to share this day with you'),
    'concert': ('Приходи — будет громко!', "Come along — it's going to be loud!"),
    'lecture': ('Будем рады видеть вас', "We'd be glad to see you"),
    'exhibition': ('Будем рады видеть вас', "We'd be glad to see you"),
}
FALLBACK_MESSAGE = ('Приглашаем вас!', "You're invited!")

HEX_LEN = 7


def palette(template, slug):
    palettes = TEMPLATES.get(template, TEMPLATES['ticket'])['palettes']
    values = palettes.get(slug) or next(iter(palettes.values()))
    _ru, _en, bg, bg2, fg, muted, accent = values
    return {'bg': bg, 'bg2': bg2, 'fg': fg, 'muted': muted, 'accent': accent}


def first_palette(template):
    return next(iter(TEMPLATES[template]['palettes']))


def catalog_for_js(language='ru'):
    """Всё, что нужно редактору в браузере для живого превью."""
    def pick(ru, en):
        from Users.i18n import tr
        return tr(language, ru, en)

    return {
        'templates': {
            key: {
                'name': pick(*tpl['name']),
                'font': tpl['font'],
                'palettes': {
                    slug: {'name': pick(p[0], p[1]), **palette(key, slug)}
                    for slug, p in tpl['palettes'].items()
                },
            }
            for key, tpl in TEMPLATES.items()
        },
        'fonts': {key: {'display': f[0], 'body': f[1]} for key, f in FONTS.items()},
        'formats': {key: {'w': f[2], 'h': f[3]} for key, f in FORMATS.items()},
    }


WEEKDAYS = {
    'ru': ('понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье'),
    'en': ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'),
    'cs': ('pondělí', 'úterý', 'středa', 'čtvrtek', 'pátek', 'sobota', 'neděle'),
}


def when(event, language='ru'):
    """Части даты для вёрстки открытки: 14 / ноября / пятница / 18:30 / 2026."""
    from Users.templatetags.language_tags import MONTH_LABELS
    if not event.date:
        return None
    months = MONTH_LABELS.get(language, MONTH_LABELS['ru'])
    weekdays = WEEKDAYS.get(language, WEEKDAYS['ru'])
    return {
        'day': event.date.day,
        'month': months[event.date.month],
        'year': event.date.year,
        'weekday': weekdays[event.date.weekday()],
        'time': event.time.strftime('%H:%M') if event.time else '',
    }
