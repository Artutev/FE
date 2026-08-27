from django.db import migrations, models


DEFAULT_TYPES = [
    ('concert', 'Концерт', 'Concert', 10),
    ('theater', 'Театр', 'Theater', 20),
    ('cinema', 'Кино', 'Cinema', 30),
    ('exhibition', 'Выставка', 'Exhibition', 40),
    ('lecture', 'Лекция', 'Lecture', 50),
    ('wedding', 'Свадьба', 'Wedding', 60),
    ('other', 'Другое', 'Other', 70),
]


def create_default_types(apps, schema_editor):
    event_type_model = apps.get_model('Events', 'EventType')
    event_type_model.objects.bulk_create([
        event_type_model(
            code=code,
            name_ru=name_ru,
            name_en=name_en,
            sort_order=sort_order,
        )
        for code, name_ru, name_en, sort_order in DEFAULT_TYPES
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('Events', '0008_event_optional_location_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.SlugField(max_length=50, unique=True, verbose_name='Код')),
                ('name_ru', models.CharField(max_length=100, verbose_name='Название на русском')),
                ('name_en', models.CharField(max_length=100, verbose_name='Название на английском')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Тип мероприятия',
                'verbose_name_plural': 'Типы мероприятий',
                'ordering': ('sort_order', 'name_ru'),
            },
        ),
        migrations.RunPython(create_default_types, migrations.RunPython.noop),
    ]