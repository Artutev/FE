from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Users', '0003_user_theme_preference'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_confirmation_code_hash',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]