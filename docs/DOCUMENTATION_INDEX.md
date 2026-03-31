# 📖 Индекс документации — 30 марта 2026

Полная документация всех изменений и новых фич добавленных в проект FastEvent.

---

## 📚 Документы по порядку чтения

### 1️⃣ Для пользователей и менеджеров

**[README_NEW_FEATURES.md](README_NEW_FEATURES.md)** — Быстрый старт  
✅ Как использовать темную тему  
✅ Как использовать поиск мероприятий  
✅ Примеры и FAQ  
⏱ Чтение: 5 минут

---

### 2️⃣ Для разработчиков

**[CHANGELOG_2026_03_30.md](CHANGELOG_2026_03_30.md)** — Полный список изменений  
✅ Всё что изменилось в коде  
✅ Какие файлы были добавлены/обновлены  
✅ Структура проекта  
✅ Миграции БД  
⏱ Чтение: 15 минут

**[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** — Техническое руководство  
✅ Как работает система CSS переменных  
✅ JavaScript API для темной темы  
✅ Backend логика поиска  
✅ Примеры расширения функциональности  
✅ Оптимизация и тестирование  
⏱ Чтение: 20 минут

**[DARK_THEME_DOCS.md](DARK_THEME_DOCS.md)** — Подробное руководство по теме  
✅ Установка и миграция  
✅ Как работает система  
✅ Палитра цветов  
✅ Инструкции для расширения  
⏱ Чтение: 10 минут

---

## 📋 Быстрая навигация

### По темам

**Темная тема 🌙**
- Как работает: [DEVELOPER_GUIDE.md#1-темная-тема](DEVELOPER_GUIDE.md#1-темная-тема--система-css-переменных)
- Цветовая палитра: [CHANGELOG_2026_03_30.md#-цветовая-палитра](CHANGELOG_2026_03_30.md#-цветовая-палитра-тёмной-темы)
- Использование: [DARK_THEME_DOCS.md](DARK_THEME_DOCS.md)
- Быстрый старт: [README_NEW_FEATURES.md#-темная-тема](README_NEW_FEATURES.md#-темная-тема)

**Поиск мероприятий 🔍**
- Как работает: [DEVELOPER_GUIDE.md#4-поиск-мероприятий](DEVELOPER_GUIDE.md#4-поиск-мероприятий)
- Примеры: [CHANGELOG_2026_03_30.md#-примеры-запросов](CHANGELOG_2026_03_30.md#-примеры-запросов)
- Использование: [README_NEW_FEATURES.md#-поиск-мероприятий](README_NEW_FEATURES.md#-поиск-мероприятий)
- Расширение: [DEVELOPER_GUIDE.md#добавить-новое-поле-в-поиск](DEVELOPER_GUIDE.md#добавить-новое-поле-в-поиск)

**Файлы и архитектура 📁**
- Структура: [CHANGELOG_2026_03_30.md#-структура-проекта-обновлённая](CHANGELOG_2026_03_30.md#-структура-проекта-обновлённая)
- Новые файлы: [CHANGELOG_2026_03_30.md#-измененные-файлы-1](CHANGELOG_2026_03_30.md#-измененные-файлы)
- Изменения: [CHANGELOG_2026_03_30.md#-измененные-файлы](CHANGELOG_2026_03_30.md#-измененные-файлы)

**Разработка и расширение 👨‍💻**
- CSS переменные: [DEVELOPER_GUIDE.md#css-переменные-staticcssbasecss](DEVELOPER_GUIDE.md#css-переменные-staticcssbasecss)
- JavaScript API: [DEVELOPER_GUIDE.md#функции-и-api](DEVELOPER_GUIDE.md#функции-и-api)
- Django ORM: [DEVELOPER_GUIDE.md#фильтры-django-orm](DEVELOPER_GUIDE.md#фильтры-django-orm)
- Примеры расширения: [DEVELOPER_GUIDE.md#5-расширение-функциональности](DEVELOPER_GUIDE.md#5-расширение-функциональности)

---

## 🗂️ Структура документации

```
📖 Documentation/
├── README_NEW_FEATURES.md        ← Для пользователей и быстрого старта
├── CHANGELOG_2026_03_30.md       ← Полный список изменений
├── DEVELOPER_GUIDE.md            ← Техническое руководство
├── DARK_THEME_DOCS.md            ← Подробное руководство по теме
└── DOCUMENTATION_INDEX.md        ← Этот файл
```

---

## 🚀 Чек-лист для DevOps/QA

### Перед деплоем в продакшн

- [ ] Применить миграции: `python manage.py migrate Users`
- [ ] Собрать статику: `python manage.py collectstatic --noinput`
- [ ] Проверить темную тему в браузере (Ctrl+Shift+R)
- [ ] Проверить поиск на странице "Мероприятия"
- [ ] Проверить в Firefox, Chrome, Safari
- [ ] Проверить на мобильных устройствах
- [ ] Проверить в Django Admin (Users → theme_preference)

### Проверка совместимости

| Браузер | Темная тема | Поиск | Примечание |
|---------|------|-------|-----------|
| Chrome 90+ | ✅ | ✅ | OK |
| Firefox 88+ | ✅ | ✅ | OK |
| Safari 14+ | ✅ | ✅ | OK |
| Edge 90+ | ✅ | ✅ | OK |
| IE 11 | ❌ | ✅ | localStorage могут быть проблемы |

---

## ❓ FAQ

### Как найти нужную информацию?

**Q: Как использовать темную тему?**  
A: Смотри [README_NEW_FEATURES.md#-темная-тема](README_NEW_FEATURES.md#-темная-тема)

**Q: Где хранится выбор темы?**  
A: В `localStorage` браузера. Подробно: [DEVELOPER_GUIDE.md#javascript--логика-переключения-темы](DEVELOPER_GUIDE.md#2-javascript--логика-переключения-темы-staticjsthemejs)

**Q: Как расширить поиск?**  
A: [DEVELOPER_GUIDE.md#добавить-новое-поле-в-поиск](DEVELOPER_GUIDE.md#добавить-новое-поле-в-поиск)

**Q: Какие файлы изменились?**  
A: [CHANGELOG_2026_03_30.md#-структура-проекта-обновлённая](CHANGELOG_2026_03_30.md#-структура-проекта-обновлённая)

**Q: Как добавить свой цвет?**  
A: [DEVELOPER_GUIDE.md#добавить-новый-цвет-в-css-переменные](DEVELOPER_GUIDE.md#добавить-новый-цвет-в-css-переменные)

**Q: Как избежать мерцания при загрузке?**  
A: [DEVELOPER_GUIDE.md#как-это-помогает-избежать-мерцания](DEVELOPER_GUIDE.md#как-это-помогает-избежать-мерцания)

---

## 📊 Статистика изменений

| Метрика | Значение |
|---------|----------|
| Новых файлов | 4 |
| Обновленных файлов | 9 |
| Строк кода добавлено | ~500 |
| CSS переменных | 19 |
| Новых классов CSS | 8 |
| Функций JavaScript | 3 |
| Миграций БД | 1 |

---

## 🔗 Полезные ссылки

### Документация Django
- [Models](https://docs.djangoproject.com/en/3.2/topics/db/models/)
- [Views](https://docs.djangoproject.com/en/3.2/topics/http/views/)
- [Templates](https://docs.djangoproject.com/en/3.2/topics/templates/)
- [QuerySet API](https://docs.djangoproject.com/en/3.2/ref/models/querysets/)

### MDN Web Docs
- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
- [localStorage API](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)
- [prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
- [Form Controls](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input)

### Инструменты
- [Django Documentation](https://docs.djangoproject.com/)
- [MDN Web Docs](https://developer.mozilla.org/)
- [CSS Tricks](https://css-tricks.com/)

---

## 📝 История изменений

| Дата | Версия | Изменения |
|------|--------|----------|
| 30.03.2026 | 1.0 | Первый релиз темной темы и поиска |

---

## 👤 Автор и лицензия

- **Автор:** GitHub Copilot
- **Дата:** 30 марта 2026
- **Версия:** 1.0

---

## 💡 Рекомендованный путь изучения

### Для новичков:
1. Прочитать [README_NEW_FEATURES.md](README_NEW_FEATURES.md) — что это и как пользоваться
2. Посмотреть в браузере как работает
3. Прочитать [CHANGELOG_2026_03_30.md](CHANGELOG_2026_03_30.md) — какие файлы изменились

### Для опытных разработчиков:
1. Начать с [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — полное техническое описание
2. Посмотреть исходный код в файлах
3. Использовать [DARK_THEME_DOCS.md](DARK_THEME_DOCS.md) для справки

### Для DevOps:
1. Посмотреть [CHANGELOG_2026_03_30.md#развертывание](CHANGELOG_2026_03_30.md#развертывание) — как деплоить
2. Применить миграции
3. Собрать статику

---

**Всё готово для использования! Спасибо за внимание! 🎉**
