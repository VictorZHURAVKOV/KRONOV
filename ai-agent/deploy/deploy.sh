#!/bin/bash
# КРОНОВЪ AI-agent — полная установка на Ubuntu 24.04 VPS.
# Запуск с локальной машины:
#   ssh -i ~/.ssh/kronov_agent root@<IP> 'bash -s' < deploy.sh
#
# Скрипт:
# - ставит Python 3.12, Node, nginx, certbot
# - создаёт пользователя kronov (без sudo root-доступа)
# - клонирует репо в /srv/kronov
# - ставит зависимости в venv
# - кладёт .env (ключи прокидываются через ENV-переменные при запуске)
# - настраивает systemd для uvicorn
# - настраивает nginx + Let's Encrypt для agent.kronov.by
# - открывает 80/443 в ufw, закрывает 8000

set -euo pipefail
set -x

DOMAIN="${DOMAIN:-agent.kronov.by}"
REPO="https://github.com/VictorZHURAVKOV/KRONOV.git"
USER_NAME="kronov"
APP_DIR="/srv/kronov"
AGENT_DIR="$APP_DIR/ai-agent"

# === 1. Системные пакеты ===
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  python3.12 python3.12-venv python3-pip git curl \
  nginx certbot python3-certbot-nginx \
  libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libffi-dev \
  ufw build-essential

# === 2. Пользователь ===
if ! id -u "$USER_NAME" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$USER_NAME"
fi
mkdir -p "$APP_DIR"
chown -R "$USER_NAME:$USER_NAME" "$APP_DIR"

# === 3. Клон репозитория ===
if [ ! -d "$APP_DIR/.git" ]; then
  sudo -u "$USER_NAME" git clone "$REPO" "$APP_DIR"
else
  sudo -u "$USER_NAME" git -C "$APP_DIR" pull
fi

# === 4. Python venv + зависимости ===
sudo -u "$USER_NAME" bash -c "
  cd '$AGENT_DIR'
  python3.12 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
"

# === 5. .env (передаём из окружения установщика) ===
cat > "$AGENT_DIR/.env" <<EOF
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
CLAUDE_MODEL=${CLAUDE_MODEL:-claude-sonnet-4-6}
OPENAI_API_KEY=${OPENAI_API_KEY}

TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
ALENA_TELEGRAM_CHAT_ID=${ALENA_TELEGRAM_CHAT_ID}
ALENA_PHONE=${ALENA_PHONE:-+375296888629}
ALENA_NAME=${ALENA_NAME:-Алёна}

SITE_URL=https://kronov.by
SITE_ORIGIN=https://kronov.by

HOST=127.0.0.1
PORT=8000

CORS_ORIGINS=https://kronov.by,https://${DOMAIN}

WAZZUP_ACCOUNT_ID=${WAZZUP_ACCOUNT_ID:-7746-6178}
WAZZUP_API_KEY=${WAZZUP_API_KEY}
WAZZUP_WEBHOOK_TOKEN=${WAZZUP_WEBHOOK_TOKEN}

CHAT_RATE_LIMIT=${CHAT_RATE_LIMIT:-20}
CHAT_RATE_WINDOW=${CHAT_RATE_WINDOW:-60}
EOF
chown "$USER_NAME:$USER_NAME" "$AGENT_DIR/.env"
chmod 600 "$AGENT_DIR/.env"

# === 6. systemd unit ===
cat > /etc/systemd/system/kronov-agent.service <<EOF
[Unit]
Description=KRONOV AI agent
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$AGENT_DIR
Environment="PATH=$AGENT_DIR/.venv/bin"
ExecStart=$AGENT_DIR/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
StandardOutput=append:/var/log/kronov-agent.log
StandardError=append:/var/log/kronov-agent.log

[Install]
WantedBy=multi-user.target
EOF

touch /var/log/kronov-agent.log
chown "$USER_NAME:$USER_NAME" /var/log/kronov-agent.log

systemctl daemon-reload
systemctl enable kronov-agent
systemctl restart kronov-agent

# === 7. nginx (HTTP → временно, потом certbot сделает HTTPS) ===
cat > /etc/nginx/sites-available/kronov-agent <<EOF
server {
  listen 80;
  server_name $DOMAIN;

  # Let's Encrypt ACME challenge
  location /.well-known/acme-challenge/ { root /var/www/html; }

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header Connection "";
    proxy_buffering off;           # критично для SSE
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;
  }
}
EOF
ln -sf /etc/nginx/sites-available/kronov-agent /etc/nginx/sites-enabled/kronov-agent
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# === 8. Let's Encrypt ===
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
  -m "ontoritmi@gmail.com" --redirect

# === 9. firewall ===
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# === 10. проверка ===
sleep 3
curl -sS "https://$DOMAIN/healthz" || echo "(healthz пока не отвечает — проверьте логи: journalctl -u kronov-agent -n 50)"

echo ""
echo "=== УСТАНОВКА ЗАВЕРШЕНА ==="
echo "Сервис:   systemctl status kronov-agent"
echo "Логи:     journalctl -u kronov-agent -f"
echo "URL:      https://$DOMAIN"
echo "Health:   https://$DOMAIN/healthz"
