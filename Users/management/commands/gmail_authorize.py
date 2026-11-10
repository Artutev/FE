"""Получить GMAIL_REFRESH_TOKEN для отправки писем через Gmail API.

Запускать на своём компьютере (нужен браузер):
    python manage.py gmail_authorize --client-file путь/к/client_secret_XXX.json

Откроется страница Google: войти под ящиком-отправителем (fastevent.123@gmail.com),
разрешить «Отправка писем от вашего имени». Команда напечатает три строки для .env.local.
"""
import base64
import hashlib
import http.server
import json
import secrets
import threading
import urllib.parse
import webbrowser

from django.core.management.base import BaseCommand, CommandError

from Users.gmail_backend import SCOPE, TOKEN_URL, _post

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    result = {}

    def do_GET(self):  # noqa: N802 (http.server API)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CallbackHandler.result = {key: values[0] for key, values in query.items()}
        ok = 'code' in query
        self.send_response(200 if ok else 400)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        text = ('Готово! Можно закрыть вкладку и вернуться в терминал.' if ok
                else 'Авторизация не удалась. Вернитесь в терминал.')
        self.wfile.write(f'<h2 style="font-family:sans-serif">{text}</h2>'.encode('utf-8'))

    def log_message(self, *args):
        pass


class Command(BaseCommand):
    help = 'Получить refresh token Gmail API (scope gmail.send) через браузер.'

    def add_arguments(self, parser):
        parser.add_argument('--client-file', help='JSON OAuth-клиента типа «Desktop app» из Google Cloud Console')
        parser.add_argument('--client-id')
        parser.add_argument('--client-secret')
        parser.add_argument('--no-browser', action='store_true', help='Не открывать браузер, только показать ссылку')

    def handle(self, *args, **options):
        client_id, client_secret = options['client_id'], options['client_secret']
        if options['client_file']:
            try:
                with open(options['client_file'], encoding='utf-8') as fh:
                    data = json.load(fh)
            except (OSError, ValueError) as exc:
                raise CommandError(f'Не удалось прочитать {options["client_file"]}: {exc}')
            section = data.get('installed') or data.get('web') or {}
            client_id = client_id or section.get('client_id')
            client_secret = client_secret or section.get('client_secret')
        if not client_id or not client_secret:
            raise CommandError('Укажите --client-file или --client-id и --client-secret.')

        server = http.server.HTTPServer(('127.0.0.1', 0), _CallbackHandler)
        redirect_uri = f'http://127.0.0.1:{server.server_port}/'
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        state = secrets.token_urlsafe(16)
        url = AUTH_URL + '?' + urllib.parse.urlencode({
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': SCOPE,
            'access_type': 'offline',
            'prompt': 'consent',
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'state': state,
        })

        self.stdout.write('\nОткройте ссылку и войдите под ящиком-отправителем (fastevent.123@gmail.com):\n')
        self.stdout.write(url + '\n')
        if not options['no_browser']:
            webbrowser.open(url)
        self.stdout.write('\nЖду ответа от Google…')

        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        thread.join(timeout=300)
        server.server_close()
        result = _CallbackHandler.result
        if not result:
            raise CommandError('Не дождался ответа за 5 минут. Запустите команду ещё раз.')
        if result.get('state') != state:
            raise CommandError('Неверный state в ответе — запустите команду ещё раз.')
        if 'code' not in result:
            raise CommandError(f'Google вернул ошибку: {result.get("error", "unknown")}')

        token = _post(TOKEN_URL, urllib.parse.urlencode({
            'client_id': client_id,
            'client_secret': client_secret,
            'code': result['code'],
            'code_verifier': verifier,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }).encode(), {'Content-Type': 'application/x-www-form-urlencoded'}, timeout=20)

        refresh = token.get('refresh_token')
        if not refresh:
            raise CommandError('Google не выдал refresh_token. Удалите доступ приложения в '
                               'https://myaccount.google.com/permissions и повторите.')

        self.stdout.write(self.style.SUCCESS('\nГотово. Добавьте в .env.local на сервере (это секреты, никому не пересылайте):\n'))
        self.stdout.write(f'GMAIL_CLIENT_ID={client_id}')
        self.stdout.write(f'GMAIL_CLIENT_SECRET={client_secret}')
        self.stdout.write(f'GMAIL_REFRESH_TOKEN={refresh}')
        self.stdout.write('GMAIL_SENDER=fastevent.123@gmail.com\n')
