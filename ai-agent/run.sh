#!/bin/bash
# Управление сервисами AI-агента КРОНОВЪ.
#
# ./run.sh setup        — создать venv, поставить зависимости
# ./run.sh server       — запустить FastAPI (виджет на сайте + webhooks)
# ./run.sh tg           — запустить Telegram-бот (long polling)
# ./run.sh all          — server в фоне + tg в фоне
# ./run.sh stop         — остановить все запущенные процессы
# ./run.sh status       — кто запущен
# ./run.sh logs         — последние строки логов

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/.venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"
PID_DIR="$SCRIPT_DIR/data/pids"
LOG_DIR="$SCRIPT_DIR/data/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

cmd_setup() {
    if [ ! -d "$VENV" ]; then
        python3 -m venv "$VENV"
    fi
    "$PIP" install --upgrade pip
    "$PIP" install -r requirements.txt
    if [ ! -f .env ]; then
        cp .env.example .env
        echo ""
        echo "==> Создал .env из шаблона. ОТКРОЙ его и впиши: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, ALENA_TELEGRAM_CHAT_ID."
    fi
    echo "Готово."
}

start_bg() {
    local name="$1"; shift
    local pid_file="$PID_DIR/$name.pid"
    local log_file="$LOG_DIR/$name.log"
    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo "$name уже работает (PID $(cat "$pid_file"))"
        return
    fi
    nohup "$@" >> "$log_file" 2>&1 &
    echo $! > "$pid_file"
    echo "$name запущен (PID $!), лог: $log_file"
}

cmd_server()  { start_bg server "$PY" -m uvicorn server:app --host 0.0.0.0 --port 8000; }
cmd_tg()      { start_bg tg     "$PY" tg_bot.py; }
cmd_all()     { cmd_server; cmd_tg; }

cmd_stop() {
    for f in "$PID_DIR"/*.pid; do
        [ -f "$f" ] || continue
        local name=$(basename "$f" .pid)
        local pid=$(cat "$f")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" && echo "$name остановлен (был PID $pid)"
        fi
        rm -f "$f"
    done
}

cmd_status() {
    for name in server tg; do
        local f="$PID_DIR/$name.pid"
        if [ -f "$f" ] && kill -0 "$(cat "$f")" 2>/dev/null; then
            echo "$name: ✓ работает (PID $(cat "$f"))"
        else
            echo "$name: ✗ не запущен"
        fi
    done
}

cmd_logs() {
    for name in server tg; do
        echo "===== $name ====="
        tail -n 30 "$LOG_DIR/$name.log" 2>/dev/null || echo "(логов нет)"
        echo ""
    done
}

case "${1:-status}" in
    setup) cmd_setup ;;
    server) cmd_server ;;
    tg) cmd_tg ;;
    all) cmd_all ;;
    stop) cmd_stop ;;
    status) cmd_status ;;
    logs) cmd_logs ;;
    *) echo "Использование: $0 {setup|server|tg|all|stop|status|logs}"; exit 1 ;;
esac
