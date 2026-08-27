from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('Users', '0005_friendrequest')]
    operations = [
        migrations.AddField(
            model_name='user',
            name='is_profile_private',
            field=models.BooleanField(default=False, verbose_name='Закрытый профиль'),
        ),
    ]