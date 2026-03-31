# Generated migration file for theme_preference field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Users', '0002_remove_user_image_user_birthdate'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='theme_preference',
            field=models.CharField(
                choices=[('light', 'Светлая тема'), ('dark', 'Темная тема'), ('auto', 'Автоматично')],
                default='auto',
                max_length=10,
                verbose_name='Предпочитаемая тема'
            ),
        ),
    ]
