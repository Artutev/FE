#!/usr/bin/env bash
# Выкладка FastEvent на прод.
# Запуск (от пользователя с правом записи в проект). Скрипт лучше брать из нужной ветки
# во временный файл, чтобы не трогать рабочее дерево до проверок:
#   cd /home/ubuntu/FE && git fetch origin
#   git show origin/feat/redesign-violet:scripts/deploy.sh > /tmp/fe-deploy.sh
#   PROJECT_DIR=/home/ubuntu/FE bash /tmp/fe-deploy.sh feat/redesign-violet
# Скрипт останавливается на первой ошибке и ничего не перезапускает, пока всё не прошло.
set -euo pipefail

BRANCH="${1:-main}"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
SERVICE="${SERVICE:-fe}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"

cd "$PROJECT_DIR"
say() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }

say "Проект: $PROJECT_DIR, ветка: $BRANCH, сервис: $SERVICE"

# Читаем .env.local так же, как FE/settings.py: KEY=VALUE без подстановок bash
# (в паролях бывают $, ` и т.п.), внешние кавычки снимаются.
load_env() {
    local file="$1" line key value
    [ -f "$file" ] || return 0
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%$'\r'}"
        [[ -z "${line//[[:space:]]/}" || "${line#"${line%%[![:space:]]*}"}" == \#* || "$line" != *=* ]] && continue
        key="${line%%=*}"; value="${line#*=}"
        key="$(printf '%s' "$key" | tr -d '[:space:]')"
        value="${value#"${value%%[![:space:]]*}"}"; value="${value%"${value##*[![:space:]]}"}"
        if [[ ${#value} -ge 2 && ( ( "${value:0:1}" == '"' && "${value: -1}" == '"' ) || ( "${value:0:1}" == "'" && "${value: -1}" == "'" ) ) ]]; then
            value="${value:1:${#value}-2}"
        fi
        [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
        export "$key=$value"
    done < "$file"
}

# 1. Переменные окружения — проверяем ДО любых изменений
load_env .env.local
missing=()
for var in SECRET_KEY ALLOWED_HOSTS CSRF_TRUSTED_ORIGINS SITE_URL; do
    [ -n "${!var:-}" ] || missing+=("$var")
done
if [ ${#missing[@]} -gt 0 ]; then
    say "В .env.local не хватает: ${missing[*]}"
    echo "Добавьте их (пример — в .env.example) и запустите скрипт снова. Ничего не изменено."
    exit 1
fi

# Если что-то упадёт до переключения кода — вернуть ручные правки на место
STASHED=0
CODE_SWITCHED=0
restore_on_error() {
    if [ "$STASHED" = 1 ] && [ "$CODE_SWITCHED" = 0 ]; then
        echo "Ошибка до обновления кода — возвращаю ручные правки (git stash pop)"
        git stash pop || echo "Не удалось вернуть автоматически: git stash list"
    fi
}
trap restore_on_error ERR

# 2. Локальные правки на сервере (часто это settings.py) — сохраняем, а не теряем
mkdir -p "$BACKUP_DIR"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    say "На сервере есть незакоммиченные правки:"
    git status --short --untracked-files=no
    git diff HEAD > "$BACKUP_DIR/server-local-changes-$STAMP.diff"
    git stash push -m "server-local-$STAMP"
    STASHED=1
    echo "Правки сохранены в git stash и в $BACKUP_DIR/server-local-changes-$STAMP.diff"
    echo "Настройки вроде ALLOWED_HOSTS теперь задаются в .env.local (см. docs/DEPLOY.md)."
fi

# 3. Бэкап базы
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

# 4. Код
say "Обновляю код"
PREVIOUS="$(git rev-parse HEAD)"
git fetch origin
CODE_SWITCHED=1
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
sudo systemctl status "$SERVICE" --no-pager --lines=5 || true

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
