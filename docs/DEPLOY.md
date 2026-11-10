# Деплой FastEvent

Чек-лист выкладки новой версии на сервер (Ubuntu, nginx + gunicorn/systemd).
Конкретные пути и имена сервисов уточняются по серверу.

## 1. Переменные окружения

Начиная с ветки `feat/redesign-violet` настройки берутся из env (`.env.local` или systemd `EnvironmentFile`).
Обязательные:

| Переменная | Пример | Зачем |
|---|---|---|
| `SECRET_KEY` | длинная случайная строка | подпись сессий и токенов |
| `DEBUG` | `False` | на сервере всегда `False` |
| `ALLOWED_HOSTS` | `example.com,www.example.com` | без этого Django отвечает 400 |
| `CSRF_TRUSTED_ORIGINS` | `https://example.com` | формы по HTTPS |
| `BEHIND_HTTPS_PROXY` | `True`, если HTTPS на nginx | корректные secure-cookies |
| `SECURE_COOKIES` | `True` (или `False`, если сайт пока по HTTP) | иначе на HTTP не будет работать вход |
| `STATIC_ROOT` | `/var/www/fastevent/static` | куда кладёт `collectstatic` |
| `POSTGRES_*` | см. `.env.example` | база |
| `RESEND_API_KEY`, `DEFAULT_FROM_EMAIL` | `noreply@твойдомен` | все письма (адрес должен быть подтверждён в Resend) |
| `SITE_URL` | `https://example.com` | ссылки в напоминаниях, которые шлёт cron |

Сгенерировать `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 2. Выкладка

Проще всего скриптом (бэкап базы, сохранение ручных правок, миграции, статика, перезапуск, проверка):

```bash
cd /home/ubuntu/FE && git fetch origin
git show origin/feat/redesign-violet:scripts/deploy.sh > /tmp/fe-deploy.sh
PROJECT_DIR=/home/ubuntu/FE bash /tmp/fe-deploy.sh feat/redesign-violet
```

Вручную:

```bash
cd /path/to/project
git fetch origin
git checkout feat/redesign-violet        # или main после мержа
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
sudo systemctl restart <gunicorn-service>
```

## 3. Напоминания по cron

Раз в день (например, в 10:00) отправляются письма «Завтра мероприятие»:

```cron
0 10 * * * cd /path/to/project && venv/bin/python manage.py send_event_reminders >> /var/log/fastevent-reminders.log 2>&1
```

Проверить без отправки: `python manage.py send_event_reminders --dry-run`.

## 4. Почта (Gmail API)

SMTP-вход в Gmail с облачного IP сервера блокируется, поэтому письма от **fastevent.123@gmail.com**
отправляются через **Gmail API** по HTTPS (`Users/gmail_backend.py`).

Разовая настройка:
1. https://console.cloud.google.com/ под fastevent.123@gmail.com → создать проект `EventTown`.
2. Включить Gmail API: https://console.cloud.google.com/apis/library/gmail.googleapis.com
3. Google Auth Platform → Branding: название `EventTown`, почта поддержки; Audience: External,
   затем **Publish app** (статус «In production» — иначе refresh token умирает через 7 дней).
4. Clients → Create client → тип **Desktop app** → скачать JSON.
5. На своём компьютере: `python manage.py gmail_authorize --client-file путь\к\client_secret.json`,
   войти под fastevent.123@gmail.com, «Дополнительно → Перейти на сайт EventTown» → «Разрешить».
6. Команда напечатает строки `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `GMAIL_SENDER`
   — добавить их в `/home/ubuntu/FE/.env.local`, затем `sudo systemctl restart fe`.

Gmail API важнее остальных способов (SMTP/Resend/Brevo). Лимит ~500 писем в сутки.
Проверка: `python manage.py sendtestemail you@example.com`.

## 5. nginx

`/static/` должен отдаваться из `STATIC_ROOT`:

```nginx
location /static/ {
    alias /var/www/fastevent/static/;
    expires 30d;
}
```

CSS/JS подключаются с `?v=N`, поэтому долгий кэш безопасен: при изменении файлов номер версии в шаблонах увеличивается.

## 6. Проверка после выкладки

- главная, афиша, страница мероприятия открываются;
- переключение языка RU / EN / CS;
- вход/выход (выход теперь POST-формой);
- создание мероприятия с выбором места на карте;
- `python manage.py test` на сервере (нужна роль Postgres с правом CREATEDB или запуск на SQLite).

## Откат

```bash
git checkout <предыдущий коммит или ветка>
python manage.py collectstatic --noinput
sudo systemctl restart <gunicorn-service>
```

Миграции `Users.0007_user_email_settings` и `Events.0011_event_reminder_sent` только добавляют столбцы со значениями по умолчанию — старый код с ними работает, поэтому откат кода безопасен без отката базы.
