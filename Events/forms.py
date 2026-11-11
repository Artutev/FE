from django import forms
from django.utils import timezone
from Events.models import Event, EventType
from Users.i18n import CS, SUPPORTED_LANGUAGES, tr
from Users.images import process_image, replace_image

PLACEHOLDERS = {
    'ru': {
        'name': 'Введите название',
        'event_type': 'Выберите тип события',
        'date': 'ДД.MM.ГГГГ',
        'time': 'ЧЧ:ММ',
        'location': 'Начните вводить адрес',
        'venue_name': 'Например, лофт «Крыша» или кафе «Пушкин»',
        'directions': 'Подъезд, этаж, код домофона, где оставить машину',
        'bride_name': 'Имя невесты (для свадеб)',
        'groom_name': 'Имя жениха (для свадеб)',
        'wedding_theme': 'Тема свадьбы (например, винтаж, рустик и т.п.)',
        'guest_count': 'Число гостей',
        'description': 'Введите описание',
    },
    'en': {
        'name': 'Enter the name',
        'event_type': 'Select event type',
        'date': 'DD.MM.YYYY',
        'time': 'HH:MM',
        'location': 'Start typing the address',
        'venue_name': 'e.g. Rooftop Loft or Café Pushkin',
        'directions': 'Entrance, floor, door code, where to park',
        'bride_name': 'Bride name (for weddings)',
        'groom_name': 'Groom name (for weddings)',
        'wedding_theme': 'Wedding theme (e.g. vintage, rustic, etc.)',
        'guest_count': 'Number of guests',
        'description': 'Enter the description',
    },
}

LABELS = {
    'ru': {
        'name': 'Название',
        'event_type': 'Тип мероприятия',
        'date': 'Дата',
        'time': 'Время',
        'location': 'Адрес',
        'venue_name': 'Название места',
        'directions': 'Как найти',
        'is_private': 'Приватное мероприятие',
        'bride_name': 'Имя невесты',
        'groom_name': 'Имя жениха',
        'wedding_theme': 'Тема свадьбы',
        'guest_count': 'Ожидаемое количество гостей',
        'description': 'Описание',
    },
    'en': {
        'name': 'Name',
        'event_type': 'Event type',
        'date': 'Date',
        'time': 'Time',
        'location': 'Address',
        'venue_name': 'Venue name',
        'directions': 'How to find it',
        'is_private': 'Private event',
        'bride_name': 'Bride name',
        'groom_name': 'Groom name',
        'wedding_theme': 'Wedding theme',
        'guest_count': 'Expected guests',
        'description': 'Description',
    },
}

PLACEHOLDERS['cs'] = {key: CS.get(value, value) for key, value in PLACEHOLDERS['en'].items()}
LABELS['cs'] = {key: CS.get(value, value) for key, value in LABELS['en'].items()}


class EventForm(forms.ModelForm):
    cover_upload = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp', 'class': 'photo-input'}),
    )
    remove_cover = forms.BooleanField(required=False)
    date = forms.DateField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control date-picker-input',
                'autocomplete': 'off',
                'placeholder': PLACEHOLDERS['ru']['date'],
                'readonly': True,
            }
        ),
        input_formats=['%Y-%m-%d', '%d.%m.%Y']
    )

    time = forms.TimeField(
        required=True,
        # TimeInput с форматом — при редактировании в поле «16:00», а не «16:00:00»:
        # раньше такое значение не проходило проверку, и форма редактирования (вместе с обложкой) не сохранялась.
        widget=forms.TimeInput(
            format='%H:%M',
            attrs={
                'class': 'form-control time-picker-input',
                'autocomplete': 'off',
                'placeholder': PLACEHOLDERS['ru']['time'],
                'readonly': True,
            }
        ),
        input_formats=['%H:%M', '%H:%M:%S']
    )

    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    # Город и страну подставляет скрипт карты из подсказки адреса — для фильтра афиши по городу
    city = forms.CharField(required=False, max_length=100, widget=forms.HiddenInput())
    country = forms.CharField(required=False, max_length=100, widget=forms.HiddenInput())

    class Meta:
        model = Event
        fields = [
            'name',
            'event_type',
            'date',
            'time',
            'latitude',
            'longitude',
            'venue_name',
            'location',
            'directions',
            'city',
            'country',
            'is_online',
            'online_url',
            'is_private',
            'bride_name',
            'groom_name',
            'wedding_theme',
            'guest_count',
            'description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['name']
            }),
            'event_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['location']
            }),
            'venue_name': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 120}),
            'directions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'maxlength': 500}),
            'is_online': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'online_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://zoom.us/j/…'}),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'bride_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['bride_name']
            }),
            'groom_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['groom_name']
            }),
            'wedding_theme': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['wedding_theme']
            }),
            'guest_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['guest_count']
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': PLACEHOLDERS['ru']['description']
            }),
        }

    def __init__(self, *args, language='ru', **kwargs):
        kwargs.setdefault('label_suffix', '')
        self.language = language if language in SUPPORTED_LANGUAGES else 'ru'
        super().__init__(*args, **kwargs)

        lang = self.language
        self.fields['name'].label = LABELS[lang]['name']
        self.fields['event_type'].label = LABELS[lang]['event_type']
        self.fields['date'].label = LABELS[lang]['date']
        self.fields['time'].label = LABELS[lang]['time']
        self.fields['location'].label = LABELS[lang]['location']
        self.fields['is_online'].label = tr(lang, 'Онлайн-мероприятие', 'Online event')
        self.fields['online_url'].label = tr(lang, 'Ссылка на трансляцию или звонок', 'Stream or call link')
        self.fields['online_url'].required = False
        self.fields['online_url'].error_messages['invalid'] = tr(
            lang, 'Введите ссылку целиком, начиная с https://', 'Enter the full link, starting with https://')
        for name in ('venue_name', 'directions'):
            self.fields[name].label = LABELS[lang][name]
            self.fields[name].required = False
            self.fields[name].widget.attrs.update({'placeholder': PLACEHOLDERS[lang][name]})
        self.fields['is_private'].label = LABELS[lang]['is_private']
        self.fields['bride_name'].label = LABELS[lang]['bride_name']
        self.fields['groom_name'].label = LABELS[lang]['groom_name']
        self.fields['wedding_theme'].label = LABELS[lang]['wedding_theme']
        self.fields['guest_count'].label = LABELS[lang]['guest_count']
        self.fields['description'].label = LABELS[lang]['description']

        self.fields['name'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['name']})
        self.fields['event_type'].choices = EventType.localized_choices(lang)
        self.fields['location'].required = False
        self.fields['description'].required = False
        self.fields['date'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['date']})
        self.fields['time'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['time']})
        self.fields['location'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['location']})
        self.fields['bride_name'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['bride_name']})
        self.fields['groom_name'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['groom_name']})
        self.fields['wedding_theme'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['wedding_theme']})
        self.fields['guest_count'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['guest_count']})
        self.fields['description'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['description']})

    def clean_cover_upload(self):
        upload = self.cleaned_data.get('cover_upload')
        if not upload:
            return None
        return process_image(upload, 'cover', self.language)

    def save(self, commit=True):
        event = super().save(commit=False)
        new_cover = self.cleaned_data.get('cover_upload')
        if new_cover is not None:
            replace_image(event, 'cover', new_cover)
        elif self.cleaned_data.get('remove_cover') and event.cover:
            replace_image(event, 'cover', None)
        if commit:
            event.save()
        return event

    def clean(self):
        cleaned_data = super().clean()
        event_date = cleaned_data.get('date')
        event_time = cleaned_data.get('time')
        event_type = cleaned_data.get('event_type')
        location = cleaned_data.get('location')

        if cleaned_data.get('is_online'):
            # Онлайн: адрес и карта не нужны — чистим, чтобы на странице не висело старое место
            for name in ('location', 'venue_name', 'directions', 'city', 'country'):
                cleaned_data[name] = ''
            cleaned_data['latitude'] = cleaned_data['longitude'] = None
            location = 'online'
        else:
            cleaned_data['online_url'] = ''

        if event_type != 'other' and not location and not cleaned_data.get('venue_name'):
            message = tr(self.language, 'Укажите место проведения.', 'Please enter a location.')
            self.add_error('location', message)

        if event_date and event_time:
            event_datetime = timezone.make_aware(
                timezone.datetime.combine(event_date, event_time),
                timezone.get_current_timezone()
            )
            if event_datetime < timezone.now():
                raise forms.ValidationError(tr(
                    self.language,
                    'Нельзя создать мероприятие в прошлом. Выберите дату и время в будущем.',
                    'You can’t create an event in the past. Choose a future date and time.',
                ))

        return cleaned_data



class InvitationCardForm(forms.ModelForm):
    """Конструктор пригласительного: все значения проверяются по каталогу Events/card_designs.py."""
    # Картинку проверяем сами в Users/images.py — с понятным текстом ошибки на нужном языке
    photo_upload = forms.FileField(required=False)
    remove_photo = forms.BooleanField(required=False)

    class Meta:
        from Events.models import InvitationCard
        model = InvitationCard
        fields = ['template', 'palette', 'font', 'accent', 'background', 'format', 'title', 'subtitle', 'message']

    def __init__(self, *args, event=None, language='ru', **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event or self.instance.event
        self.language = language
        self.fields['title'].max_length = 120
        self.fields['message'].max_length = 300

    def clean_photo_upload(self):
        upload = self.cleaned_data.get('photo_upload')
        if not upload:
            return None
        return process_image(upload, 'card', self.language)

    def clean(self):
        import re
        from Events import card_designs as designs
        data = super().clean()
        template = data.get('template')
        if template not in designs.TEMPLATES:
            self.add_error('template', 'Unknown template')
            return data
        if data.get('palette') not in designs.TEMPLATES[template]['palettes']:
            data['palette'] = designs.first_palette(template)
        if data.get('font') not in designs.FONTS:
            data['font'] = designs.TEMPLATES[template]['font']
        if data.get('format') not in designs.FORMATS:
            data['format'] = 'story'
        has_photo = bool(data.get('photo_upload')) or (bool(self.instance.photo) and not data.get('remove_photo'))
        background = data.get('background')
        if (background not in designs.BACKGROUNDS
                or (background == 'cover' and not self.event.cover)
                or (background == 'photo' and not has_photo)):
            data['background'] = 'decor'
        accent = (data.get('accent') or '').strip()
        data['accent'] = accent.upper() if re.fullmatch(r'#[0-9a-fA-F]{6}', accent) else ''
        return data

    def save(self, commit=True):
        card = super().save(commit=False)
        new_photo = self.cleaned_data.get('photo_upload')
        if new_photo is not None:
            replace_image(card, 'photo', new_photo)
        elif self.cleaned_data.get('remove_photo') and card.photo:
            replace_image(card, 'photo', None)
        if commit:
            card.save()
        return card
