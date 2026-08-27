from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Events', '0007_auto_20260806_1619'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='location',
            field=models.CharField(blank=True, max_length=200, verbose_name='Место проведения'),
        ),
        migrations.AlterField(
            model_name='event',
            name='description',
            field=models.TextField(blank=True, verbose_name='Описание'),
        ),
    ]