# ⚡ Шпаргалка разработчика

Быстрые примеры кода и команды для повседневной разработки.

---

## 🌙 Темная тема

### CSS
```css
/* Использовать переменные */
.component {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
}

/* Специфичные стили для темной темы */
html.dark-mode .component {
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}
```

### JavaScript
```javascript
// Получить текущую тему
const isDark = document.documentElement.classList.contains('dark-mode');

// Получить сохранённую тему
const saved = localStorage.getItem('theme_preference');

// Переключить тему
window.themeToggle.toggle();

// Инициализировать
window.themeToggle.init();
```

### HTML
```html
<!-- Кнопка переключения (уже есть) -->
<button id="theme-toggle-btn" class="theme-toggle" 
        onclick="window.themeToggle.toggle()">🌙</button>

<!-- Слушать изменение системной темы -->
<script>
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    console.log(e.matches ? 'dark' : 'light');
  });
</script>
```

### Палитра
```
Light:  #f3f6fb | #ffffff | #1f2937 | #6b7280 | #2563eb
Dark:   #0f172a | #1e293b | #f1f5f9 | #cbd5e1 | #3b82f6
```

---

## 🔍 Поиск мероприятий

### Python (Django)
```python
from django.db.models import Q

# Фильтрация
search = request.GET.get('search', '')
if search:
    events = events.filter(
        Q(name__icontains=search) |
        Q(description__icontains=search) |
        Q(location__icontains=search)
    )

# Другие фильтры
iexact           # Точное, без учёта регистра
startswith       # Начинается с
contains         # Содержит (с учётом регистра)
gt, gte, lt, lte # Больше, меньше и т.д.
```

### HTML
```html
<form method="get">
    <input type="text" name="search" value="{{ search_query }}">
    <button type="submit">🔍</button>
    {% if search_query %}
        <a href="?">✕</a>
    {% endif %}
</form>
```

### URL
```
/meropriyatiya/?search=текст
/meropriyatiya/?search=текст&type=conference
/meropriyatiya/?search=москва&date=2026-03-30
```

---

## 🛠️ Командная строка

### Django
```bash
# Основное
python manage.py runserver              # Запустить сервер
python manage.py makemigrations         # Создать миграцию
python manage.py migrate                # Применить миграции
python manage.py migrate Users          # Только для Users

# Другое
python manage.py shell                  # Python консоль
python manage.py createsuperuser        # Создать админа
python manage.py collectstatic          # Собрать статику
python manage.py showmigrations         # Показать статус
python manage.py sqlmigrate Users 0003  # SQL миграции
```

---

## 📁 Файлы проекта

### Основные файлы (обновлены)
```
static/js/theme.js              ✨ Новый
static/css/base.css             ✏️ Темная тема + стили
static/css/event_list.css       ✏️ Поиск + темная тема

Users/models.py                 ✏️ theme_preference поле
Users/admin.py                  ✏️ Отображение в админке
Users/templates/base.html       ✏️ Кнопка темы
Users/migrations/0003_*.py      ✨ Новый

Events/views.py                 ✏️ Логика поиска
Events/templates/eventList.html ✏️ Форма поиска
```

---

## 🎨 CSS классы

### Темная тема
```css
.search-form           /* Контейнер поиска */
.search-container      /* Flex контейнер */
.search-input          /* Input поиск */
.search-btn            /* Кнопка поиска */
.search-clear          /* Кнопка очистки */
.search-results-info   /* Информация о результатах */

.theme-toggle          /* Кнопка переключения темы */
.nav-pill--ghost       /* Прозрачные кнопки */
```

### Существующие классы (работают с темой)
```css
var(--bg)              /* Фон страницы */
var(--surface)         /* Карточки, контейнеры */
var(--text)            /* Текст */
var(--primary)         /* Кнопки, ссылки */
var(--border)          /* Границы */
```

---

## 🔄 Процесс развёртывания

```bash
# 1. Применить миграции
python manage.py migrate Users

# 2. Собрать статику (для продакшна)
python manage.py collectstatic --noinput

# 3. Перезагрузить веб-сервер
systemctl restart django    # Или gunicorn
systemctl restart nginx     # Если используешь Nginx

# 4. Проверить логи
tail -f /var/log/django/error.log
```

---

## 🧪 Тестирование

### Проверка темной темы
```bash
# В консоли браузера (F12)
localStorage.getItem('theme_preference')  # 'light', 'dark', или null
document.documentElement.classList       # Содержит ли dark-mode?
```

### Проверка поиска
```python
# В Django shell
python manage.py shell

from Events.models import Event
from django.db.models import Q

# Создать событие
e = Event.objects.create(name='Футбол', location='Москва')

# Искать
Event.objects.filter(Q(name__icontains='фут') | Q(location__icontains='msk'))
```

---

## 🐛 Частые ошибки

### Темная тема не работает
```bash
# ❌ Проблема: script в неправильном месте
<link rel="stylesheet" href="base.css">
<script src="theme.js"></script>

# ✅ Решение: script перед стилями
<script src="theme.js"></script>
<link rel="stylesheet" href="base.css">
```

### Поиск не фильтрует
```python
# ❌ Проблема: Забыли импортировать Q
events = events.filter(name__icontains=search)  # Только AND

# ✅ Решение: Используй Q для OR
from django.db.models import Q
events = events.filter(
    Q(name__icontains=search) | 
    Q(description__icontains=search)
)
```

### localStorage не сохраняется
```javascript
// ❌ Проблема: Приватное окно или отключено
localStorage.setItem('test', '1')  // Ошибка!

// ✅ Решение: Проверить можно ли писать
try {
    localStorage.setItem('test', '1');
    localStorage.removeItem('test');
} catch(e) {
    console.log('localStorage недоступен');
}
```

---

## 📚 Полезные примеры

### Расширить поиск
```python
# В Events/views.py
if search_query:
    events = events.filter(
        Q(name__icontains=search_query) |
        Q(description__icontains=search_query) |
        Q(location__icontains=search_query) |
        Q(event_type__icontains=search_query) |  # ← Новое
        Q(creator__email__icontains=search_query)  # ← Новое
    )
```

### Добавить новый цвет
```css
/* В base.css */
:root {
    --success: #10b981;
}

html.dark-mode {
    --success: #34d399;
}

/* Использовать */
.success { background: var(--success); }
```

### Сохранить тему на сервер
```python
# В Users/models.py - уже есть!
theme_preference = models.CharField(
    choices=[('light', 'Светлая'), ('dark', 'Темная'), ('auto', 'Авто')],
    default='auto'
)

# Использовать
user.theme_preference = 'dark'
user.save()
```

---

## 🎯 Шпаргалка URL

| Path | Файл |
|------|------|
| `/` | Users/templates/base.html |
| `/meropriyatiya/` | Events/templates/eventList.html |
| `/meropriyatiya/?search=текст` | Фильтр в EventList |
| `/admin/` | Django Admin |
| `/static/css/base.css` | Основной CSS файл |
| `/static/js/theme.js` | Скрипт темы |

---

## 💡 Советы

1. **Используй CSS переменные** — не hardcode цвета
2. **Тестируй в обоих режимах** — светлом и темном
3. **Проверяй контрастность** — текст должен читаться
4. **Используй Q объекты** — для сложных фильтров
5. **Кэшируй поиск** — для больших БД используй elasticsearch
6. **Сохраняй на сервер** — для авторизованных пользователей

---

**Happy coding! 🚀**
