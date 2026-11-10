# Шифрует текст сообщений в базе. Существующие сообщения шифруются этой же миграцией.

import Chat.fields
from django.db import migrations

BATCH = 500


def encrypt_existing(apps, schema_editor):
    """Поле уже шифрующее: чтение отдаёт открытый текст (старые строки как есть), запись шифрует."""
    Message = apps.get_model('Chat', 'Message')
    batch = []
    for message in Message.objects.only('pk', 'text').iterator(chunk_size=BATCH):
        batch.append(message)
        if len(batch) >= BATCH:
            Message.objects.bulk_update(batch, ['text'])
            batch = []
    if batch:
        Message.objects.bulk_update(batch, ['text'])


def decrypt_existing(apps, schema_editor):
    """Откат: записать открытый текст напрямую, минуя шифрующее поле."""
    Message = apps.get_model('Chat', 'Message')
    connection = schema_editor.connection
    table = connection.ops.quote_name(Message._meta.db_table)
    column = connection.ops.quote_name(Message._meta.get_field('text').column)
    pk = connection.ops.quote_name(Message._meta.pk.column)
    rows = [(m.text, m.pk) for m in Message.objects.only('pk', 'text').iterator(chunk_size=BATCH)]
    with connection.cursor() as cursor:
        cursor.executemany(f'UPDATE {table} SET {column} = %s WHERE {pk} = %s', rows)


class Migration(migrations.Migration):

    dependencies = [
        ('Chat', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='text',
            field=Chat.fields.EncryptedTextField(max_length=2000, verbose_name='Текст'),
        ),
        migrations.RunPython(encrypt_existing, decrypt_existing),
    ]
