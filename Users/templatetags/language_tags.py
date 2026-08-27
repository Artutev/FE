from django import template
from Events.models import Event, EventType

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
}

@register.simple_tag(takes_context=True)
def lang(context, ru_text, en_text):
    language = context.get('LANGUAGE_CODE', 'ru')
    return en_text if language == 'en' else ru_text

@register.simple_tag(takes_context=True)
def event_type_label(context, event_type_code):
    language = context.get('LANGUAGE_CODE', 'ru')
    event_type = EventType.objects.filter(code=event_type_code).first()
    if event_type:
        return event_type.name_en if language == 'en' else event_type.name_ru
    labels = Event.EVENT_TYPE_LABELS.get(language, Event.EVENT_TYPE_LABELS['ru'])
    return labels.get(event_type_code, event_type_code)

@register.simple_tag(takes_context=True)
def event_date(context, value):
    if not value:
        return ''
    language = context.get('LANGUAGE_CODE', 'ru')
    months = MONTH_LABELS.get(language, MONTH_LABELS['ru'])
    return f'{value.day} {months[value.month]} {value.year}'
