# 👨‍💻 Техническое руководство для разработчиков

## 1. Темная тема — Система CSS переменных

### Архитектура

```
html
├── :root { --bg, --surface, --text, ... }  (Светлая тема)
└── html.dark-mode { --bg, --surface, ... } (Тёмная тема)
    └── javascript добавляет/удаляет класс dark-mode
```

### CSS переменные (static/css/base.css)

```css
:root {
    /* Светлая тема - по умолчанию */
    --bg: #f3f6fb;
    --surface: #ffffff;
    --surface-soft: #f8fbff;
    --text: #1f2937;
    --muted: #6b7280;
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --danger: #dc2626;
    --warning: #d97706;
    --border: #dbe4f0;
    --shadow: 0 18px 45px rgba(37, 99, 235, 0.08);
}

html.dark-mode {
    /* Тёмная тема */
    --bg: #0f172a;
    --surface: #1e293b;
    --surface-soft: #334155;
    --text: #f1f5f9;
    --muted: #cbd5e1;
    --primary: #3b82f6;
    --primary-dark: #1e40af;
    --danger: #ef4444;
    --warning: #f59e0b;
    --border: #475569;
    --shadow: 0 18px 45px rgba(15, 23, 42, 0.5);
}
```

### Как использовать переменные

#### ✅ Правильно:
```css
.card {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
}
/* Автоматически переключится при смене темы */
```

#### ❌ Неправильно:
```css
.card {
    background: #ffffff;
    color: #1f2937;
    border: 1px solid #dbe4f0;
}
/* Не переключится в темном режиме */
```

### Для специфичных стилей в тёмном режиме:

```css
html.dark-mode .my-component {
    background: rgba(59, 130, 246, 0.2);
    /* Специальный стиль только для темной темы */
}
```

---

## 2. JavaScript — Логика переключения темы (static/js/theme.js)

### Функции и API

```javascript
// Инициализация при загрузке
window.themeToggle.init()
// - Читает localStorage или системные настройки
// - Применяет класс dark-mode к <html>

// Переключение темы
window.themeToggle.toggle()
// - Переключает класс dark-mode
// - Сохраняет выбор в localStorage
// - Обновляет иконку кнопки

// Обновление иконки
window.themeToggle.updateIcon()
// - 🌙 для светлой темы
// - ☀️ для тёмной темы
```

### Поток выполнения

1. **Скрипт загружается** в `<head>` до загрузки CSS
2. **Проверяются источники темы** по приоритету:
   - `localStorage.theme_preference` (сохранённый выбор)
   - `prefers-color-scheme: dark` (система)
   - По умолчанию: `light`
3. **Применяется класс** на `<html>` элемент
4. **Загружается CSS** с уже применённой темой → нет мерцания
5. **Слушатель на системные изменения** — если система изменит тему, обновляется

### Как это помогает избежать мерцания

```html
<!-- Неправильный порядок - будет мерцание -->
<link rel="stylesheet" href="base.css">
<script src="theme.js"></script>

<!-- ✅ Правильный порядок (используется в проекте) -->
<script src="theme.js"></script>
<link rel="stylesheet" href="base.css">
```

Когда скрипт загружается **в head ПЕРЕД CSS**, класс `dark-mode` уже есть на `<html>` когда CSS применяется.

---

## 3. Backend — Модель и миграция

### Модель User (Users/models.py)

```python
class User(AbstractUser):
    THEME_CHOICES = (
        ('light', 'Светлая тема'),
        ('dark', 'Темная тема'),
        ('auto', 'Автоматично'),
    )
    
    birthDate = models.DateField(null=True, blank=True)
    theme_preference = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default='auto',
        verbose_name='Предпочитаемая тема'
    )
```

### Использование в коде

```python
# В view или шаблоне
if request.user.is_authenticated:
    user_theme = request.user.theme_preference
    # 'light', 'dark' или 'auto'

# В фильтре
light_mode_users = User.objects.filter(theme_preference='light')
```

### Миграция (Users/migrations/0003_user_theme_preference.py)

```bash
python manage.py makemigrations       # Создать миграцию
python manage.py migrate Users         # Применить миграцию
python manage.py showmigrations Users  # Показать статус
```

---

## 4. Поиск мероприятий

### Backend логика (Events/views.py)

```python
from django.db.models import Q

def event_list(request):
    events = Event.objects.all().order_by('date', 'time')
    
    # Получить параметр search из URL
    search_query = request.GET.get('search', '')
    
    # Фильтрация если есть поиск
    if search_query:
        events = events.filter(
            Q(name__icontains=search_query) |           # Или название
            Q(description__icontains=search_query) |    # Или описание
            Q(location__icontains=search_query)         # Или место
        )
    
    context = {
        'events': events,
        'search_query': search_query
    }
    return render(request, 'Events/eventList.html', context)
```

### Фильтры Django ORM

| Фильтр | Описание |
|--------|---------|
| `exact` | Точное совпадение (по умолчанию) |
| `iexact` | Точное, но без учёта регистра |
| `contains` | Содержит подстроку, с учётом регистра |
| **`icontains`** | Содержит, БЕЗ учёта регистра ✅ |
| `startswith` | Начинается с |
| `endswith` | Заканчивается на |
| `gt`, `gte`, `lt`, `lte` | Больше, больше_или_равно, меньше, меньше_или_равно |

### Q объекты для сложных запросов

```python
# OR логика (хотя бы одно условие)
Q(field1__icontains='text') | Q(field2__icontains='text')  # OR

# AND логика (все условия)
Q(field1__icontains='text') & Q(field2__icontains='text')  # AND

# NOT логика (инверсия)
~Q(field1__icontains='text')  # NOT

# Комбинирование
Q(name__icontains='текст') & (Q(date=today) | Q(date=tomorrow))
```

### Frontend (Events/templates/eventList.html)

```html
<!-- Форма поиска -->
<form method="get" class="search-form">
    <div class="search-container">
        <input 
            type="text" 
            name="search" 
            value="{{ search_query }}"
            placeholder="Поиск мероприятий..."
        >
        <button type="submit" class="search-btn">🔍</button>
        {% if search_query %}
            <a href="{% url 'Event:event_list' %}" class="search-clear">✕</a>
        {% endif %}
    </div>
</form>

<!-- Параметры отправляются как GET запрос -->
<!-- Результат: /meropriyatiya/?search=текст -->
```

### CSS стили для поиска

```css
.search-form {
    margin-bottom: 28px;
}

.search-container {
    display: flex;
    gap: 8px;
}

.search-input {
    flex: 1;
    min-height: 48px;
    padding: 0 16px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--surface);
    color: var(--text);
}

.search-btn {
    width: 48px;
    height: 48px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--surface);
    cursor: pointer;
}

.search-btn:hover {
    background: var(--surface-soft);
    border-color: var(--primary);
}

/* Тёмный режим */
html.dark-mode .search-btn:hover {
    background: rgba(59, 130, 246, 0.2);
}
```

---

## 5. Расширение функциональности

### Добавить новый цвет в CSS переменные

```css
:root {
    --success: #10b981;
    /* ... остальные переменные */
}

html.dark-mode {
    --success: #34d399;
}

/* Использовать */
.success-badge {
    background: var(--success);
}
```

### Добавить новое поле в поиск

```python
# Events/views.py
events = events.filter(
    Q(name__icontains=search_query) |
    Q(description__icontains=search_query) |
    Q(location__icontains=search_query) |
    Q(creator__username__icontains=search_query) |  # ← Новое
    Q(event_type__icontains=search_query) |         # ← Новое
)
```

### Добавить фильтры к поиску

```python
# Поиск + фильтр по типу
event_type = request.GET.get('type', '')
if event_type:
    events = events.filter(event_type=event_type)
```

```html
<!-- Добавить селект -->
<select name="type">
    <option value="">Все типы</option>
    <option value="conference">Конференция</option>
    <option value="workshop">Воркшоп</option>
</select>
```

### Сохранить предпочтение темы на сервер

```python
# Когда пользователь переключит тему, отправить AJAX запрос
fetch('/api/theme-preference/', {
    method: 'POST',
    body: JSON.stringify({ theme: 'dark' }),
    headers: { 'Content-Type': 'application/json' }
})
```

```python
# В urls.py добавить view
path('api/theme-preference/', save_theme_preference, name='save_theme')

# В views.py
@login_required
def save_theme_preference(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        request.user.theme_preference = data.get('theme')
        request.user.save()
        return JsonResponse({'status': 'ok'})
```

---

## 6. Тестирование

### Проверка темной темы

```python
# tests.py
from django.test import Client
from django.contrib.auth.models import User

def test_dark_theme_toggle():
    client = Client()
    response = client.get('/')
    assert response.status_code == 200
    # Проверить что скрипт theme.js загружен
    assert 'theme.js' in str(response.content)
```

### Проверка поиска

```python
def test_event_search():
    client = Client()
    
    # Создать тестовое событие
    event = Event.objects.create(
        name='Футбольный матч',
        description='Дружеский матч',
        location='Москва'
    )
    
    # Тест поиска
    response = client.get('/meropriyatiya/?search=футбол')
    assert response.status_code == 200
    assert event in response.context['events']
    
    # Тест поиска без результатов
    response = client.get('/meropriyatiya/?search=никакойтекст')
    assert len(response.context['events']) == 0
```

---

## 7. Оптимизация

### Query оптимизация

```python
# Неоптимально - N+1 проблема
for event in events:
    print(event.creator.username)  # N запросов!

# Оптимально
events = events.select_related('creator')
for event in events:
    print(event.creator.username)  # 1 запрос!
```

### Поиск с индексами БД

```python
# models.py
class Event(models.Model):
    name = models.CharField(max_length=255, db_index=True)  # Индекс!
    description = models.TextField(db_index=True)
```

### CSS оптимизация

```css
/* ❌ Неправильно - переполнение переменных */
html.dark-mode .btn-primary,
html.dark-mode .btn-secondary,
html.dark-mode .btn-tertiary,
html.dark-mode .btn-danger {
    color: #f1f5f9;
}

/* ✅ Правильно - используй наследование */
html.dark-mode {
    --button-text: #f1f5f9;
}
.btn {
    color: var(--button-text);
}
```

---

## 📚 Дополнительные ресурсы

- [Django QuerySet API](https://docs.djangoproject.com/en/3.2/ref/models/querysets/)
- [CSS Variables](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
- [prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
- [localStorage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)

---

**Удачи в разработке!** 🚀
