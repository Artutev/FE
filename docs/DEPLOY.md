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

## 4. Почта (Resend)

- В Resend добавить домен и прописать у регистратора DNS-записи, которые он покажет (SPF, DKIM, по желанию DMARC) — без этого письма уходят в спам.
- `DEFAULT_FROM_EMAIL` — адрес на подтверждённом домене, например `EventTown <noreply@домен>`.
- Проверка с сервера: `python manage.py sendtestemail you@example.com`.

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
