import re
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from Events.models import Event
from Users.i18n import CS, tr
from Users.models import User


class LanguageTests(TestCase):
    def test_switch_to_czech(self):
        self.client.get(reverse('Users:set_language', args=['cs']))
        content = self.client.get(reverse('Events:event_list')).content.decode()
        self.assertIn('Nadcházející akce', content)

    def test_unknown_language_falls_back_to_russian(self):
        self.client.get(reverse('Users:set_language', args=['xx']))
        self.assertEqual(self.client.session['language'], 'ru')

    def test_language_switch_blocks_open_redirect(self):
        response = self.client.get(
            reverse('Users:set_language', args=['en']) + '?next=https://evil.example.com/'
        )
        self.assertEqual(response['Location'], '/')

    def test_tr_helper(self):
        self.assertEqual(tr('ru', 'Да', 'Yes'), 'Да')
        self.assertEqual(tr('en', 'Да', 'Yes'), 'Yes')
        self.assertEqual(tr('cs', 'Сохранить', 'Save'), 'Uložit')
        self.assertEqual(tr('cs', 'Нет перевода', 'No translation yet'), 'No translation yet')

    def test_every_template_string_has_czech_translation(self):
        pattern = re.compile(r'\{%\s*lang\s+(".*?"|\'.*?\')\s+(".*?"|\'.*?\')(\s+as\s+\w+)?\s*%\}')
        missing = set()
        for path in Path(settings.BASE_DIR).glob('*/templates/**/*.*'):
            for _ru, en, _as in pattern.findall(path.read_text(encoding='utf-8')):
                if en[1:-1] not in CS:
                    missing.add(en[1:-1])
        self.assertEqual(missing, set())


class AuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('alice', 'alice@example.test', 'Pass12345!x')

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('Users:logout')).status_code, 405)
        self.assertEqual(self.client.post(reverse('Users:logout')).status_code, 302)

    def test_login_redirects_to_safe_next(self):
        response = self.client.post(reverse('Users:login'), {
            'username': 'alice', 'password': 'Pass12345!x', 'next': '/Event/create/',
        })
        self.assertEqual(response['Location'], '/Event/create/')

    def test_login_ignores_external_next(self):
        response = self.client.post(reverse('Users:login'), {
            'username': 'alice', 'password': 'Pass12345!x', 'next': 'https://evil.example.com/',
        })
        self.assertEqual(response['Location'], reverse('base'))

    def _login(self, username, password, **extra):
        return self.client.post(reverse('Users:login'), {'username': username, 'password': password, **extra})

    def test_login_ignores_case_and_surrounding_spaces(self):
        response = self._login('  ALICE ', 'Pass12345!x')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_wrong_password_shows_error(self):
        response = self._login('alice', 'wrong-pass')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Неверное имя пользователя или пароль.')

    def test_wrong_password_error_in_czech(self):
        self.client.get(reverse('Users:set_language', args=['cs']))
        self.assertContains(self._login('alice', 'nope'), 'Zadejte správné uživatelské jméno a heslo.')

    def test_password_is_not_trimmed(self):
        self.assertEqual(self._login('alice', ' Pass12345!x ').status_code, 200)

    def test_unconfirmed_email_gets_explained(self):
        self.user.is_active = False
        self.user.save()
        response = self._login('alice', 'Pass12345!x')
        self.assertContains(response, 'Email ещё не подтверждён')
        self.assertContains(response, reverse('Users:confirm_email_code') + '?email=alice%40example.test')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_unconfirmed_hint_needs_right_password(self):
        self.user.is_active = False
        self.user.save()
        self.assertNotContains(self._login('alice', 'wrong'), 'Email ещё не подтверждён')

    def test_case_twins_are_told_apart_by_password(self):
        twin = User.objects.create_user('Alice', 'twin@example.test', 'Other12345!y')
        self._login('alice', 'Other12345!y')
        self.assertEqual(int(self.client.session['_auth_user_id']), twin.pk)

    def test_login_is_rate_limited(self):
        for _ in range(10):
            self._login('alice', 'wrong')
        response = self._login('ALICE', 'Pass12345!x')
        self.assertContains(response, 'Слишком много попыток входа')
        self.assertNotIn('_auth_user_id', self.client.session)

    def _register(self, **overrides):
        data = {
            'username': 'bob', 'email': 'bob@example.test', 'birthDate': '01.01.1990',
            'password1': 'Strong12345!z', 'password2': 'Strong12345!z', **overrides,
        }
        return self.client.post(reverse('Users:registration'), data)

    def test_registration_trims_username(self):
        self.assertEqual(self._register(username='  bob  ').status_code, 302)
        self.assertTrue(User.objects.filter(username='bob').exists())

    def test_registration_rejects_case_duplicate(self):
        response = self._register(username='ALICE')
        self.assertContains(response, 'Пользователь с таким именем уже существует.')

    def test_registration_allows_cyrillic_username(self):
        self.assertEqual(self._register(username='Борис').status_code, 302)

    def test_registration_rejects_non_latin_password(self):
        for bad in ('Пароль12345!', 'Strong 12345!', 'Strong12345! '):
            response = self._register(password1=bad, password2=bad)
            self.assertContains(response, 'только латинские буквы', msg_prefix=repr(bad))
        self.assertFalse(User.objects.filter(username='bob').exists())

    def test_registration_password_error_in_english(self):
        self.client.get(reverse('Users:set_language', args=['en']))
        bad = 'Пароль12345!'
        self.assertContains(self._register(password1=bad, password2=bad), 'only contain Latin letters')

    def test_confirmation_code_is_rate_limited(self):
        url = reverse('Users:confirm_email_code')
        statuses = [
            self.client.post(url, {'email': 'nobody@example.test', 'code': '000000'}).status_code
            for _ in range(6)
        ]
        self.assertEqual(statuses[:5], [200] * 5)
        self.assertEqual(statuses[5], 429)


class ProfileTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@example.test', 'Pass12345!x')
        self.other = User.objects.create_user('other', 'other@example.test', 'Pass12345!x')
        future = date.today() + timedelta(days=3)
        Event.objects.create(name='Open party', date=future, creator=self.owner)
        Event.objects.create(name='Hidden party', date=future, creator=self.owner, is_private=True)

    def test_public_profile_hides_private_events(self):
        self.client.force_login(self.other)
        content = self.client.get(reverse('Users:public_profile', args=['owner'])).content.decode()
        self.assertIn('Open party', content)
        self.assertNotIn('Hidden party', content)

    def test_owner_sees_own_private_events(self):
        self.client.force_login(self.owner)
        content = self.client.get(reverse('Users:public_profile', args=['owner'])).content.decode()
        self.assertIn('Hidden party', content)

    def test_profile_page_renders(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('Users:profile')).status_code, 200)

    def test_friends_hides_inactive_users(self):
        User.objects.create_user('ghost', 'ghost@example.test', 'Pass12345!x', is_active=False)
        self.client.force_login(self.owner)
        content = self.client.get(reverse('Users:friends')).content.decode()
        self.assertNotIn('/Users/User/ghost/', content)
        self.assertIn('/Users/User/other/', content)
