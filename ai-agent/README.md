# КРОНОВЪ — AI-менеджер «Андрей»

AI-агент на Claude Sonnet 4.6 — ведёт клиента от первого сообщения до готовности к договору, после чего передаёт **Алёне** (живой менеджер, +375 29 688-86-29) с краткой сводкой в Telegram.

## Что умеет

- **Один агент** на всех каналах: сайт kronov/kronov.by, Telegram, WhatsApp, Viber.
- **Считает цену** по той же формуле что в калькуляторе сайта (+20% за нестандартный размер автоматом).
- **Подбирает модель** из 11 артикулов (КР-001 … КР-011).
- **Формирует PDF**: коммерческое предложение и договор-заявку.
- **CRM = Telegram-канал**: каждое значимое событие летит Алёне в реальном времени.
- **Передача живому менеджеру** с указанием срочности (сейчас / утром / по окну).
- **Никогда не называет сроки** (это работа Алёны), не упоминает Кверкус, не использует эмодзи.
- **Работает 24/7** в чате; ночью предупреждает что звонок будет утром.

## Архитектура (одна картинка словами)

```
[Сайт kronov.by] ───┐
[Telegram бот]   ───┤
[WhatsApp]       ───┼──► FastAPI (server.py) ──► agent.py (Claude + tools) ──► SQLite
[Viber]          ───┘                                  │
                                                       ├──► calculator (BYN)
                                                       ├──► PDF (КП, договор)
                                                       └──► Telegram-CRM Алёны
```

## Файлы

| Файл | Назначение |
|---|---|
| `prompts/system.md` | Системный промпт «Андрея». Здесь живёт характер и правила. |
| `prompts/kp_template.html` | Фирменный шаблон PDF коммерческого предложения. |
| `prompts/contract_template.html` | Шаблон PDF договора-заявки. |
| `tools/catalog.py` | Каталог 11 моделей беседок. |
| `tools/calculator.py` | Точная формула цены (с +20% за нестандарт). |
| `tools/crm.py` | Сохранение контактов, лог в Telegram, передача Алёне. |
| `tools/pdf_gen.py` | Генерация PDF через WeasyPrint. |
| `agent.py` | Цикл tool-use, prompt caching. |
| `server.py` | FastAPI + SSE стриминг + webhooks. |
| `tg_bot.py` | Telegram-канал в режиме long polling. |
| `db.py` | SQLite — диалоги, события, контакты. |
| `static/widget.js` | Чат-виджет для встраивания на сайт (Shadow DOM). |
| `run.sh` | Управление сервисами. |

## Шаг 1. Что предоставить (что нужно от вас)

В файл `.env` (создаётся из `.env.example` командой `./run.sh setup`):

| Переменная | Где взять |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys → Create Key. ~$30–80/мес на 100 диалогов в день. |
| `TELEGRAM_BOT_TOKEN` | В Telegram → @BotFather → `/newbot` → имя `Кронов Андрей`, юзернейм `KronovAndreyBot`. Скопируйте токен. |
| `ALENA_TELEGRAM_CHAT_ID` | В Telegram → @userinfobot → отправьте боту любое сообщение, получите свой `id`. **Алёна должна сделать это сама со своего аккаунта.** Это число — chat_id куда полетят уведомления. |
| `ALENA_PHONE` | Уже стоит `+375296888629`, можно оставить. |

Опционально:
- `SITE_URL` — основной домен (например `https://kronov.by`).
- `CORS_ORIGINS` — список через запятую — какие домены могут обращаться к `/chat`.

## Шаг 2. Запуск (локально, для теста)

```bash
cd ai-agent
./run.sh setup            # создаст venv, поставит зависимости, создаст .env
nano .env                 # вписать ключи (как минимум ANTHROPIC_API_KEY)
./run.sh server           # запустит FastAPI на :8000
```

Откройте `index.html` сайта в браузере — справа снизу появится бордовая кнопка чата. Кликните → пишите Андрею.

Telegram-бот:
```bash
./run.sh tg               # запустит long-poll
```

Всё разом:
```bash
./run.sh all              # сервер + телеграм
./run.sh status           # кто работает
./run.sh logs             # последние логи
./run.sh stop             # остановить всё
```

## Шаг 3. Деплой на продакшен (hoster.by или любой VPS)

1. **Backend AI-агента.** Нужен сервер с Python 3.11+, доменом и HTTPS.
   Рекомендую поддомен `agent.kronov.by`. На hoster.by закажите VPS (от ~10 USD/мес), поставьте Nginx + Let's Encrypt + Python.
2. **Системные пакеты для PDF** (WeasyPrint требует):
   ```
   apt install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libffi-dev
   ```
3. **Запуск как systemd-сервис.** Пример unit-файла в конце README.
4. **Виджет на сайте.** В `index.html` (и `thank-you.html`, `gazebo/*.html`, `calculator.html`, `palette.html`) уже подключена строка:
   ```html
   <script src="http://localhost:8000/widget.js" data-api="http://localhost:8000" defer></script>
   ```
   На продакшене замените `http://localhost:8000` на `https://agent.kronov.by`. Один глобальный поиск-замена.
5. **Telegram webhook.** Если есть HTTPS-домен — лучше webhook вместо long-poll:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://agent.kronov.by/webhook/telegram"
   ```
   Тогда `tg_bot.py` запускать не нужно.
6. **WhatsApp Business API.** На вашем номере уже подключён WhatsApp Business — нужно понять через какого провайдера: Meta Cloud API напрямую, или через Twilio / 360dialog / Wazzup24. Webhook поднят на `/webhook/whatsapp` (заглушка под Meta Cloud API). При подключении — нужно дописать вызов их API для отправки ответа клиенту (помечено `TODO`).
7. **Viber.** Реализован каркас на `/webhook/viber`. Нужен `auth_token` от Viber Bot Account и регистрация webhook. Отправка ответа — тоже `TODO`.

### Пример systemd-юнита

```ini
# /etc/systemd/system/kronov-agent.service
[Unit]
Description=KRONOV AI agent
After=network.target

[Service]
Type=simple
User=kronov
WorkingDirectory=/srv/kronov/ai-agent
Environment="PATH=/srv/kronov/ai-agent/.venv/bin"
ExecStart=/srv/kronov/ai-agent/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```nginx
# /etc/nginx/sites-available/agent.kronov.by
server {
  server_name agent.kronov.by;
  listen 443 ssl http2;
  # ssl_certificate ... (Let's Encrypt)

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_buffering off;          # КРИТИЧНО для SSE
    proxy_read_timeout 600s;
  }
}
```

## Как обучать агента дальше

Все знания агента — в **двух** местах:

1. **`prompts/system.md`** — характер, тон, воронка, возражения, правила. Это редактируется в любой текстовый редактор; перезапуск сервера сбросит кеш промпта (5-минутный TTL).
2. **`tools/catalog.py`** — описания моделей. Менять описания → перезапуск.

Когда пришлёте реальные переписки менеджеров с клиентами (из Кверкуса / quercus.by) — добавим раздел «Образцы фраз» в `system.md`. Когда пришлёте свой шаблон коммерческого — заменим `prompts/kp_template.html`.

## Безопасность

- `.env` в `.gitignore` — не попадёт в репозиторий.
- SQLite-БД и сгенерированные PDF тоже игнорируются.
- На продакшене — TLS обязательно (без него WhatsApp/Viber webhooks не подключатся).
- CORS ограничивайте через `CORS_ORIGINS` — не оставляйте `*`.

## Сколько стоит

Грубая оценка при Sonnet 4.6 + prompt caching:
- 1 диалог ≈ 5–15 коротких сообщений ≈ 8 000–25 000 токенов суммарно.
- Cache hit: $3 / млн input + $15 / млн output → ~$0.10–0.30 за диалог.
- 100 диалогов в день → **$10–30 в день**, $300–900/мес.
- При меньшем потоке (10–20 диалогов в день) — $30–60/мес.

Калькулятор Anthropic: https://www.anthropic.com/api → Pricing.

## Что осталось сделать (с моей стороны и с вашей)

**С моей:**
- Подключить ваш фирменный шаблон КП (когда пришлёте Word/PDF — конвертирую в HTML).
- Подключить ваш шаблон договора (юридический), сейчас — типовой.
- Залить «учебник» из переписок Кверкуса в систему — отдельным разделом промпта.
- Дописать отправку через WhatsApp Cloud API / Viber Bot API после уточнения провайдера.

**С вашей:**
- API-ключ Anthropic.
- Создать Telegram-бота через BotFather.
- Алёне открыть @userinfobot и прислать chat_id.
- Уточнить провайдера WhatsApp Business (Meta / 360dialog / Twilio / Wazzup).
- Прислать примеры реальных переписок и фирменное КП.
