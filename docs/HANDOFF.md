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

**Осталось:**
1. Обложка в карточке `Events/_event_card.html` и в шапке `eventDetail.html` (если `event.cover`, иначе как сейчас).
2. Аватар в шапке сайта (кнопка «Профиль») — по желанию.
3. Чат: `Chat/consumers.py` (AsyncJsonWebsocketConsumer: message / typing / read, presence через cache, лимит частоты),
   `Chat/routing.py` (`ws/chat/<id>/`, `ws/notify/`), `FE/asgi.py` (ProtocolTypeRouter + AuthMiddlewareStack + AllowedHostsOriginValidator).
4. Чат: views + urls (список чатов `/Chat/`, чат `/Chat/<id>/`, «написать» другу POST `/Chat/with/<username>/`, чат события `/Chat/event/<id>/`,
   JSON-история `?before=`), шаблоны, JS-клиент (переподключение, «печатает…», в сети), значок непрочитанных в шапке и нижней панели.
5. Кнопки «Написать» у друзей и «Чат участников» на странице события.
6. Переводы CS (скрипт: проверка покрытия как в Users/tests.py), тесты (Channels WebsocketCommunicator), проверка в браузере.
7. Для будущего деплоя (не сейчас): Redis на сервере, запуск через daphne/uvicorn вместо gunicorn, nginx `location /ws/` с Upgrade,
   `location /media/` → MEDIA_ROOT, бэкап media.
