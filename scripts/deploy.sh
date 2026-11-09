#!/usr/bin/env bash
# Выкладка FastEvent на прод.
# Запускать от пользователя ubuntu в папке проекта:
#   cd /home/ubuntu/FE && bash scripts/deploy.sh feat/redesign-violet
# Скрипт останавливается на первой ошибке и ничего не перезапускает, пока всё не прошло.
set -euo pipefail

BRANCH="${1:-main}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE="${SERVICE:-fe}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"

cd "$PROJECT_DIR"
say() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }

say "Проект: $PROJECT_DIR, ветка: $BRANCH, сервис: $SERVICE"

# 1. Локальные правки на сервере (часто это settings.py) — сохраняем, а не теряем
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    say "На сервере есть незакоммиченные правки:"
    git status --short --untracked-files=no
    git diff > "$BACKUP_DIR/server-local-changes-$STAMP.diff" 2>/dev/null || {
        mkdir -p "$BACKUP_DIR"; git diff > "$BACKUP_DIR/server-local-changes-$STAMP.diff"; }
    git stash push -m "server-local-$STAMP"
    echo "Правки сохранены в git stash и в $BACKUP_DIR/server-local-changes-$STAMP.diff"
    echo "Настройки вроде ALLOWED_HOSTS теперь задаются в .env.local (см. docs/DEPLOY.md)."
fi

# 2. Бэкап базы
mkdir -p "$BACKUP_DIR"
if [ -f .env.local ]; then
    set -a; . ./.env.local; set +a
fi
if [ -n "${POSTGRES_DB:-}" ]; then
    say "Бэкап PostgreSQL ($POSTGRES_DB)"
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
        -h "${POSTGRES_HOST:-127.0.0.1}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-postgres}" \
        -Fc "$POSTGRES_DB" > "$BACKUP_DIR/db-$STAMP.dump"
    echo "Бэкап: $BACKUP_DIR/db-$STAMP.dump"
else
    say "POSTGRES_DB не задан — копирую db.sqlite3"
    [ -f db.sqlite3 ] && cp db.sqlite3 "$BACKUP_DIR/db-$STAMP.sqlite3"
fi

# 3. Проверка обязательных переменных
missing=()
for var in SECRET_KEY ALLOWED_HOSTS CSRF_TRUSTED_ORIGINS SITE_URL; do
    [ -n "${!var:-}" ] || missing+=("$var")
done
if [ ${#missing[@]} -gt 0 ]; then
    say "В .env.local не хватает: ${missing[*]}"
    echo "Добавьте их (пример — в .env.example) и запустите скрипт снова."
    exit 1
fi

# 4. Код
say "Обновляю код"
PREVIOUS="$(git rev-parse HEAD)"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"
echo "Было: $PREVIOUS → стало: $(git rev-parse HEAD)"

# 5. Зависимости, миграции, статика
VENV="${VENV:-$PROJECT_DIR/venv}"
[ -d "$VENV" ] || VENV="$PROJECT_DIR/.venv"
# shellcheck disable=SC1091
. "$VENV/bin/activate"
say "Зависимости"
pip install -q -r requirements.txt
say "Проверка Django"
python manage.py check
say "Миграции"
python manage.py migrate --noinput
say "Статика"
python manage.py collectstatic --noinput

# 6. Перезапуск
say "Перезапуск $SERVICE"
sudo systemctl restart "$SERVICE"
sleep 2
sudo systemctl --no-pager --lines=5 status "$SERVICE" | head -n 12

# 7. Быстрая проверка
URL="${SITE_URL%/}/"
say "Проверяю $URL"
code="$(curl -s -o /dev/null -w '%{http_code}' "$URL" || true)"
echo "HTTP $code"
if [ "$code" != "200" ]; then
    echo "Сайт ответил не 200. Откат: git checkout $PREVIOUS && python manage.py collectstatic --noinput && sudo systemctl restart $SERVICE"
    exit 1
fi

say "Готово. Откат при необходимости: git checkout $PREVIOUS (миграции обратно совместимы)."
