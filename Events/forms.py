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
        'location': 'Введите место проведения',
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
        'location': 'Enter the location',
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
        'location': 'Место проведения',
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
        'location': 'Location',
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
        widget=forms.TextInput(
            attrs={
                'class': 'form-control time-picker-input',
                'autocomplete': 'off',
                'placeholder': PLACEHOLDERS['ru']['time'],
                'readonly': True,
            }
        ),
        input_formats=['%H:%M']
    )

    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Event
        fields = [
            'name',
            'event_type',
            'date',
            'time',
            'latitude',
            'longitude',
            'location',
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

        if event_type != 'other' and not location:
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

    class Meta:
        from Events.models import InvitationCard
        model = InvitationCard
        fields = ['template', 'palette', 'font', 'accent', 'background', 'format', 'title', 'subtitle', 'message']

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event or self.instance.event
        self.fields['title'].max_length = 120
        self.fields['message'].max_length = 300

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
        background = data.get('background')
        if background not in designs.BACKGROUNDS or (background == 'cover' and not self.event.cover):
            data['background'] = 'decor'
        accent = (data.get('accent') or '').strip()
        data['accent'] = accent.upper() if re.fullmatch(r'#[0-9a-fA-F]{6}', accent) else ''
        return data
