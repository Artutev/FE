# Handoff: текущее состояние проекта

Обновлено: 2026-11-09. Django-проект FastEvent / EventTown (приложения `Events`, `Users`, проект `FE`).

## Ветка `feat/redesign-violet`
- **Редизайн** всех страниц: палитра «Виноград» (фиолетовая), шрифт Onest, логотип-билет, светлая/тёмная тема,
  общая карточка мероприятия (`Events/templates/Events/_event_card.html`), мобильная нижняя навигация.
- **Языки**: ru / en / cs. Строки в шаблонах — `{% lang "рус" "eng" %}`, чешский перевод ищется по английской
  строке в словаре `Users/i18n.py`. Новый язык = новый словарь там же. Тест проверяет, что у всех строк есть перевод.
- **Карты**: адрес мероприятия открывает выбор приложения (Яндекс, 2ГИС, Google, Apple, Waze, OSM, Mapy.cz) —
  `Events/templatetags/map_tags.py`. Выбор места в форме — `static/js/location-map.js` (Nominatim, подсказки, метка).
- **Безопасность**: приватные события скрыты из публичных профилей, приглашение только по токену,
  регистрация/отмена/выход — POST, лимит попыток кода подтверждения, безопасные редиректы.
- **Деплой**: `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `STATIC_ROOT`, secure-cookies — из env. См. `docs/DEPLOY.md`.

## Локальный запуск
```
python manage.py runserver   # http://127.0.0.1:8000/
python manage.py test        # 25 тестов
```
- Настройки читаются из `.env.local` (см. `.env.example`).
- Если задан `POSTGRES_DB` — PostgreSQL (локально `postgresql-x64-17`, БД `fastevent`), иначе SQLite.

## Сервер
- Хост 193.123.88.237 (Oracle Cloud, Ubuntu), dev-копия: `/home/fastdev/FE-dev`.
- Доступ через сессию Claude «Проверка подключения к серверу» (SSH-подключение «FastEvent Dev» в приложении).

## Тестовые данные (локально)
- Мероприятия с префиксом `[demo]` и пользователь `demo_ui` — для проверки вёрстки. Удалить:
  `Event.objects.filter(name__startswith='[demo]').delete(); User.objects.filter(username='demo_ui').delete()`.

## Дальше
- Выкатить ветку на сервер (сначала FE-dev), смержить в `main`.
- Свои HTML-письма подтверждения + «Отправить код ещё раз» + сброс пароля.
- PWA (манифест, иконки), позже REST API под мобильное приложение.
- Фото-обложки мероприятий (`ImageField`), пагинация афиши, лимит участников.


## В работе: ветка `feat/chat-photos` (НЕ выкатывать на прод без команды Шефа)

Шеф попросил: чат на WebSockets (вариант 2) + фото мероприятий и аватары. Только локально.

**Сделано (WIP-коммит):**
- Зависимости: `channels==4.1.0`, `daphne==4.1.2`, `channels-redis==4.2.0` (в requirements.txt, локально установлены).
- Settings: `daphne` и `channels` в INSTALLED_APPS, `ASGI_APPLICATION`, `CHANNEL_LAYERS` (Redis при `REDIS_URL`, иначе InMemory), `MEDIA_URL/MEDIA_ROOT`; media отдаётся Django только при DEBUG.
- Фото: `Users/images.py` (проверка, EXIF transpose + удаление метаданных, WebP, cover 1600x1000, avatar 400x400 crop).
  Поля `Event.cover`, `User.avatar` (миграции Events.0012_photos, Users.0008_photos, применены локально).
  Форма события: поле `cover_upload` + `remove_cover`, блок выбора с предпросмотром (`static/js/photo-input.js`).
  Аватар: view `Users:update_avatar` (POST, загрузка/удаление), в шапке профиля кликабельный аватар.
  Партиал `Users/_avatar.html` (u=..., size=xs|sm|lg) уже стоит в друзьях, профиле, публичном профиле, странице события.
- Чат: приложение `Chat` — модели Conversation (direct/event), Membership (last_read_at), Message; миграция Chat.0001;
  `Chat/services.py` (доступ: личный — только друзья; чат события — участники и организатор; непрочитанные; сериализация).

**Готово (проверено локально, 62 теста):**
- Обложки в карточках и шапке страницы события; аватары по всему сайту.
- Чат на WebSockets: `Chat/consumers.py` (сообщения, «печатает…», кто в чате, прочитано, лимит 15 сообщений / 10 с),
  `ws/notify/` — живой значок непрочитанных в шапке и нижней панели; HTTP-запасной путь отправки; подгрузка истории.
- Страницы: `/Chat/` (список + «написать другу»), `/Chat/<id>/`, кнопки «Написать» (друзья, профиль, публичный профиль)
  и «Чат участников» на странице события.
- Локальные тестовые пользователи для проверки чата: `.claude/dev_test_users.txt` (в git не попадает).

**Перед выкладкой на прод (когда Шеф скажет):**
1. Сервер: `sudo apt install redis-server`; в `.env.local` добавить `REDIS_URL=redis://127.0.0.1:6379/0`.
2. `fe.service`: заменить gunicorn на ASGI — `daphne -b 127.0.0.1 -p 8000 FE.asgi:application`
   (или `gunicorn -k uvicorn.workers.UvicornWorker FE.asgi:application`).
3. nginx: `location /ws/ { proxy_pass http://127.0.0.1:8000; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade"; proxy_set_header Host $host; proxy_read_timeout 1h; }`
   и `location /media/ { alias /home/ubuntu/FE/media/; }`, `client_max_body_size 6m;`.
4. `pip install -r requirements.txt`, `migrate` (Events.0012, Users.0008, Chat.0001), `collectstatic`, бэкап `media/`.
