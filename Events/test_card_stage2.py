"""Конструктор пригласительных, этап 2: своё фото на фон и «Приду / Не смогу» с открытки."""
import os
import shutil
import tempfile
from datetime import date, timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from Events import card_designs as designs
from Events.models import Event, EventDecline, EventRegistration, InvitationCard
from Users.models import User
from Users.test_photos import jpeg_bytes

MEDIA = tempfile.mkdtemp(prefix='fe-test-card-')


@override_settings(MEDIA_ROOT=MEDIA)
class CardPhotoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.owner = User.objects.create_user('host', 'host@example.test', 'Pass12345!x')
        self.event = Event.objects.create(name='Свадьба', event_type='wedding',
                                          date=date.today() + timedelta(days=10), creator=self.owner)
        self.url = reverse('Events:card_editor', args=[self.event.id])
        self.client.force_login(self.owner)

    def post(self, **overrides):
        data = {'template': 'classic', 'palette': designs.first_palette('classic'),
                'font': designs.TEMPLATES['classic']['font'], 'accent': '', 'background': 'photo',
                'format': 'story', 'title': 'Свадьба', 'subtitle': '', 'message': ''}
        data.update(overrides)
        return self.client.post(self.url, data)

    def card(self):
        return InvitationCard.objects.get(event=self.event)

    def test_upload_photo_sets_background(self):
        response = self.post(photo_upload=SimpleUploadedFile('me.jpg', jpeg_bytes((3000, 4000)), 'image/jpeg'))
        self.assertEqual(response.status_code, 302)
        card = self.card()
        self.assertEqual(card.background, 'photo')
        self.assertTrue(card.photo.name.endswith('.webp'))
        self.assertLessEqual(max(card.photo.width, card.photo.height), 1920)
        page = self.client.get(reverse('invite_card', args=[card.code]))
        self.assertContains(page, 'ic-bg--photo')
        self.assertContains(page, card.photo.url)

    def test_photo_background_without_photo_falls_back(self):
        self.post()
        self.assertEqual(self.card().background, 'decor')

    def test_remove_photo_deletes_file(self):
        self.post(photo_upload=SimpleUploadedFile('me.jpg', jpeg_bytes(), 'image/jpeg'))
        path = self.card().photo.path
        self.assertTrue(os.path.exists(path))
        self.post(remove_photo='on')
        card = self.card()
        self.assertFalse(card.photo)
        self.assertEqual(card.background, 'decor')
        self.assertFalse(os.path.exists(path))

    def test_replacing_photo_deletes_old_file(self):
        self.post(photo_upload=SimpleUploadedFile('a.jpg', jpeg_bytes(), 'image/jpeg'))
        old = self.card().photo.path
        self.post(photo_upload=SimpleUploadedFile('b.jpg', jpeg_bytes(), 'image/jpeg'))
        self.assertFalse(os.path.exists(old))

    def test_fake_image_shows_error(self):
        response = self.post(photo_upload=SimpleUploadedFile('x.jpg', b'not an image', 'image/jpeg'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Это не похоже на картинку')
        self.assertFalse(InvitationCard.objects.exists())


class CardRsvpTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('host', 'host@example.test', 'Pass12345!x')
        self.guest = User.objects.create_user('guest', 'guest@example.test', 'Pass12345!x')
        self.event = Event.objects.create(name='Свадьба', event_type='wedding', is_private=True,
                                          access_token='tok', date=date.today() + timedelta(days=10),
                                          creator=self.owner)
        self.card = InvitationCard.initial_for(self.event)
        self.card.save()
        self.page = reverse('invite_card', args=[self.card.code])
        self.rsvp = reverse('invite_card_rsvp', args=[self.card.code])

    def answer(self, value):
        return self.client.post(self.rsvp, {'answer': value})

    def test_anonymous_sees_login_and_signup_with_return(self):
        page = self.client.get(self.page)
        self.assertContains(page, '?next=' + self.page)
        self.assertContains(page, reverse('Users:registration'))
        response = self.answer('yes')
        self.assertTrue(response['Location'].startswith(reverse('Users:login')))
        self.assertFalse(EventRegistration.objects.exists())

    def test_yes_registers_private_event_and_emails(self):
        self.client.force_login(self.guest)
        with mock.patch('Events.views.in_background') as background:
            self.assertRedirects(self.answer('yes'), self.page, fetch_redirect_response=False)
        self.assertTrue(EventRegistration.objects.filter(user=self.guest, event=self.event).exists())
        background.assert_called_once()
        self.assertContains(self.client.get(self.page), 'Вы идёте')

    def test_change_mind_both_ways(self):
        self.client.force_login(self.guest)
        with mock.patch('Events.views.in_background'):
            self.answer('yes')
            self.answer('no')
            self.assertFalse(EventRegistration.objects.exists())
            self.assertTrue(EventDecline.objects.filter(user=self.guest, event=self.event).exists())
            page = self.client.get(self.page)
            self.assertContains(page, 'Вы отказались')
            self.assertContains(page, 'Всё-таки приду')
            self.answer('yes')
        self.assertFalse(EventDecline.objects.exists())
        self.assertTrue(EventRegistration.objects.exists())

    def test_past_event_has_no_buttons_and_rejects_answers(self):
        self.event.date = date.today() - timedelta(days=1)
        self.event.save()
        self.client.force_login(self.guest)
        self.assertNotContains(self.client.get(self.page), 'cp-rsvp')
        self.answer('yes')
        self.assertFalse(EventRegistration.objects.exists())

    def test_organizer_sees_replies(self):
        other = User.objects.create_user('nope', 'nope@example.test', 'Pass12345!x')
        EventRegistration.objects.create(user=self.guest, event=self.event)
        EventDecline.objects.create(user=other, event=self.event)
        self.client.force_login(self.owner)
        page = self.client.get(reverse('Events:event_detail', args=[self.event.id]))
        self.assertContains(page, 'Ответы гостей')
        self.assertEqual([r.user for r in page.context['guests_going']], [self.guest])
        self.assertEqual([d.user for d in page.context['guests_declined']], [other])
        self.assertNotContains(self.client.get(self.page), 'cp-rsvp')  # организатору кнопки не нужны

    def test_guest_does_not_see_replies(self):
        self.client.force_login(self.guest)
        page = self.client.get(reverse('Events:event_detail', args=[self.event.id]) + '?token=tok')
        self.assertNotContains(page, 'Ответы гостей')

    def test_signup_from_card_returns_to_card_after_login(self):
        self.client.get(reverse('Users:registration') + '?next=' + self.page)
        login_page = self.client.get(reverse('Users:login'))
        self.assertEqual(login_page.context['next'], self.page)
        response = self.client.post(reverse('Users:login'), {
            'username': 'guest', 'password': 'Pass12345!x', 'next': self.page,
        })
        self.assertEqual(response['Location'], self.page)
