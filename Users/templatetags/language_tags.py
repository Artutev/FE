from django import template
from Events.models import Event, EventType
from Users.i18n import tr

register = template.Library()

MONTH_LABELS = {
    'ru': (
        '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ),
    'en': (
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ),
    'cs': (
        '', 'ledna', 'února', 'března', 'dubna', 'května', 'června',
        'července', 'srpna', 'září', 'října', 'listopadu', 'prosince'
    ),
}

MONTH_SHORT_LABELS = {
    'ru': ('', 'янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'),
    'en': ('', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'),
    'cs': ('', 'led', 'úno', 'bře', 'dub', 'kvě', 'čvn', 'čvc', 'srp', 'zář', 'říj', 'lis', 'pro'),
}

FRIEND_REQUEST_STATUS_LABELS = {
    'ru': {
        'pending': 'Ожидает ответа',
        'accepted': 'Принята',
        'declined': 'Отклонена',
    },
    'en': {
        'pending': 'Pending',
        'accepted': 'Accepted',
        'declined': 'Declined',
    },
    'cs': {
        'pending': 'Čeká na odpověď',
        'accepted': 'Přijato',
        'declined': 'Odmítnuto',
    },
}


def _language(context):
    return context.get('LANGUAGE_CODE', 'ru')


@register.simple_tag(takes_context=True)
def lang(context, ru_text, en_text):
    return tr(_language(context), ru_text, en_text)


@register.simple_tag(takes_context=True)
def event_type_label(context, event_type_code):
    return EventType.label_for(event_type_code, _language(context))


@register.simple_tag(takes_context=True)
def event_date(context, value):
    if not value:
        return ''
    language = _language(context)
    months = MONTH_LABELS.get(language, MONTH_LABELS['ru'])
    if language == 'cs':
        return f'{value.day}. {months[value.month]} {value.year}'
    return f'{value.day} {months[value.month]} {value.year}'


@register.simple_tag(takes_context=True)
def month_short(context, value):
    if not value:
        return ''
    months = MONTH_SHORT_LABELS.get(_language(context), MONTH_SHORT_LABELS['ru'])
    return months[value.month]


@register.simple_tag(takes_context=True)
def friend_request_status(context, status):
    labels = FRIEND_REQUEST_STATUS_LABELS.get(_language(context), FRIEND_REQUEST_STATUS_LABELS['ru'])
    return labels.get(status, status)


@register.simple_tag(takes_context=True)
def place_label(context, event):
    """«Название места, адрес» или «Онлайн» на языке страницы / письма."""
    if getattr(event, 'is_online', False):
        return tr(_language(context), 'Онлайн', 'Online')
    return event.place_title
