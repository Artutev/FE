import io
import shutil
import tempfile
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from Events.models import Event
from Users.images import process_image
from Users.models import User

MEDIA = tempfile.mkdtemp(prefix='fe-test-media-')


def jpeg_bytes(size=(2400, 1600), with_gps=True):
    image = Image.new('RGB', size, (124, 58, 237))
    out = io.BytesIO()
    exif = Image.Exif()
    if with_gps:
        exif[0x8825] = {2: (43.0, 14.0, 20.0), 4: (76.0, 53.0, 22.0)}  # GPSInfo
    exif[0x0110] = 'Phone 15 Pro'  # Model
    image.save(out, 'JPEG', exif=exif)
    return out.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class PhotoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def test_process_cover_resizes_and_strips_metadata(self):
        result = process_image(SimpleUploadedFile('a.jpg', jpeg_bytes()), 'cover')
        image = Image.open(io.BytesIO(result.read()))
        self.assertEqual(image.format, 'WEBP')
        self.assertLessEqual(image.width, 1600)
        self.assertLessEqual(image.height, 1000)
        self.assertEqual(len(image.getexif()), 0)

    def test_avatar_is_square(self):
        result = process_image(SimpleUploadedFile('a.jpg', jpeg_bytes()), 'avatar')
        image = Image.open(io.BytesIO(result.read()))
        self.assertEqual(image.size, (400, 400))

    def test_rejects_fake_image(self):
        with self.assertRaises(ValidationError):
            process_image(SimpleUploadedFile('evil.jpg', b'<?php echo 1; ?>'), 'cover')

    def test_rejects_large_file(self):
        big = SimpleUploadedFile('big.jpg', b'0' * (5 * 1024 * 1024 + 1))
        with self.assertRaises(ValidationError):
            process_image(big, 'cover')

    def test_avatar_upload_and_remove(self):
        user = User.objects.create_user('pic', 'pic@example.test', 'Pass12345!x')
        self.client.force_login(user)
        self.client.post(reverse('Users:update_avatar'), {'avatar': SimpleUploadedFile('me.jpg', jpeg_bytes())})
        user.refresh_from_db()
        self.assertTrue(user.avatar.name.startswith('avatars/'))
        self.assertTrue(user.avatar.name.endswith('.webp'))
        path = user.avatar.path
        self.client.post(reverse('Users:update_avatar'), {'remove_avatar': '1'})
        user.refresh_from_db()
        self.assertFalse(user.avatar)
        import os
        self.assertFalse(os.path.exists(path))

    def test_event_cover_upload_shows_on_card(self):
        user = User.objects.create_user('host', 'host@example.test', 'Pass12345!x')
        self.client.force_login(user)
        when = date.today() + timedelta(days=5)
        response = self.client.post(reverse('Events:create_event'), {
            'name': 'Photo party', 'event_type': 'other', 'date': when.strftime('%d.%m.%Y'), 'time': '19:00',
            'location': '', 'description': '', 'cover_upload': SimpleUploadedFile('c.jpg', jpeg_bytes()),
        })
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(name='Photo party')
        self.assertTrue(event.cover.name.startswith('covers/'))
        self.assertIn(event.cover.url, self.client.get(reverse('Events:event_list')).content.decode())
