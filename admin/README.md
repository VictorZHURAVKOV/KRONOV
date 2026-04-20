# КРОНОВЪ Admin Panel — admin.kronov.by

Внутренний инструмент менеджера для подготовки визуализаций беседок на фото участка клиента через **Nano Banana API (Google Gemini 2.5 Flash Image)**.

**Цель:** сократить время подготовки 3D-визуализации с 1 рабочего дня (ручной 3D-дизайнер) до **≤15 минут**.

**ТЗ-источник:** `TZ_KRONOV_V2_FULL.md` → Блок 7, Задачи 7.1–7.8.

---

## Статус

🟡 **Scaffolding готов, реализация не начата.** Это отдельный подпроект на 2–4 недели.

Текущий репозиторий — только структура папок и документация. Ниже — план и API-контракты, по которым можно начать разработку параллельно с финализацией main-сайта.

---

## Технологический стек (согласно ТЗ 7.1)

| Слой | Технология |
|------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | Node.js 20 + Express (альтернативно — Python FastAPI) |
| База данных | PostgreSQL 16 |
| Хранилище файлов | S3-совместимое (AWS S3 / Yandex Object Storage / MinIO) |
| Авторизация | JWT (access 15 мин + refresh 7 дней) + bcrypt пароли |
| AI-композиция | Google Gemini 2.5 Flash Image API (Nano Banana) |
| PDF | Puppeteer (HTML → PDF) |
| Хостинг | admin.kronov.by — отдельный поддомен, CORS изолирован |

---

## Структура директорий (scaffold)

```
admin/
├── README.md                   ← этот файл
├── backend/                    ← Node.js + Express (или FastAPI)
│   ├── (package.json)
│   ├── (src/)
│   ├── (routes/)
│   └── (migrations/)
├── frontend/                   ← React + TS
│   ├── (package.json)
│   ├── src/
│   │   ├── pages/              ← LoginPage, ProjectsList, NewProject, EditProject, Dashboard, Settings
│   │   └── components/
└── renders/                    ← Библиотека PNG-рендеров беседок (Задача 7.2)
    └── (11 моделей × 6 ракурсов = 66 файлов)
```

---

## Роли (ТЗ 7.1)

- **admin** — владелец, видит всё, создаёт менеджеров
- **manager** — работает с клиентами, генерирует визуализации
- **viewer** — только просмотр (опционально, для партнёров)

---

## Экраны (ТЗ 7.4)

### 1. Login — `/login`
- Email + пароль, JWT issued
- Забыли пароль — через письмо на email

### 2. Projects List — `/projects`
- Таблица: дата / имя / телефон / статус (new/in_progress/sent/closed) / менеджер
- Фильтры: по статусу, по менеджеру, по дате
- Поиск: по имени и телефону

### 3. New Project — `/projects/new`
- Форма: имя, телефон, email, источник, модель, загрузка 10 фото участка, комментарий
- После save → переход на экран 3

### 4. Project Edit / Generation — `/projects/:id`
3 зоны:
- **слева:** переключатель загруженных фото участка
- **центр:** превью композита + кнопки «Сгенерировать», «Перегенерировать», «Поменять ракурс», «Click-to-place»
- **справа:** история всех генераций с галочкой «использовать»

### 5. Send to Client — `/projects/:id/send`
- Превью PDF с брендированным шаблоном
- Кнопки: Скачать PDF / Отправить на email / Отправить ссылку в WhatsApp/Viber

### 6. Dashboard — `/dashboard` (admin-only)
- Проектов за период, среднее время создание→отправка, количество генераций, топ моделей

### 7. Settings — `/settings` (admin-only)
- Управление менеджерами (создать/деактивировать)
- Rate-limit настройки

---

## API Endpoints (контракт)

Префикс: `/api/v1/`

### Auth
- `POST /auth/login` → { email, password } → { access, refresh, user }
- `POST /auth/refresh` → { refresh } → { access }
- `POST /auth/logout` → 204

### Projects
- `GET /projects` — список с фильтрами (status, manager_id, date_from, date_to, search)
- `POST /projects` — создание нового
- `GET /projects/:id` — детали
- `PATCH /projects/:id` — обновление (имя, телефон, статус, …)
- `POST /projects/:id/photos` — загрузка фото участка (multipart, до 10 файлов × 15 МБ)

### Renders (библиотека PNG)
- `GET /renders` — список моделей и ракурсов
- `GET /renders/:model/:angle` — конкретный рендер (PNG с альфой)

### AI Compose (Nano Banana integration)
- `POST /projects/:id/compose`
  - body: `{ photo_id, model, angle, placement: {x,y}? }`
  - отправляет в Google Gemini API, сохраняет результат в S3, возвращает `{ generation_id, url, status, cost_usd }`
- `GET /projects/:id/generations` — история всех попыток для проекта
- `PATCH /projects/:id/generations/:gid/select` — пометить как «финальный»

### PDF & Send
- `POST /projects/:id/pdf` — сборка брендированного PDF (Puppeteer), возвращает URL
- `POST /projects/:id/send/email` — { to } → отправка
- `POST /projects/:id/send/link` — возвращает короткую public-ссылку (для WhatsApp)

### Dashboard
- `GET /dashboard/summary?period=30d`

### Users (admin-only)
- `GET /users`, `POST /users`, `PATCH /users/:id`, `DELETE /users/:id`

---

## Схема базы данных (PostgreSQL)

```sql
CREATE TABLE users (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email        TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name    TEXT,
  role         TEXT NOT NULL CHECK (role IN ('admin','manager','viewer')),
  active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

CREATE TABLE projects (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manager_id    UUID NOT NULL REFERENCES users(id),
  client_name   TEXT NOT NULL,
  client_phone  TEXT NOT NULL,
  client_email  TEXT,
  source        TEXT NOT NULL,        -- site, call, messenger, referral
  model         TEXT,                 -- KR-001..KR-011
  status        TEXT NOT NULL DEFAULT 'new', -- new, in_progress, sent, closed
  notes         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at       TIMESTAMPTZ
);

CREATE TABLE project_photos (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  s3_key     TEXT NOT NULL,
  original_name TEXT,
  mime_type  TEXT,
  size_bytes INTEGER,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE generations (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id     UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  photo_id       UUID NOT NULL REFERENCES project_photos(id),
  model          TEXT NOT NULL,
  angle          TEXT NOT NULL,   -- front, 34-left, 34-right, back, birdeye, night
  placement_x    DECIMAL(5,2),    -- 0..1 (fraction of image width)
  placement_y    DECIMAL(5,2),
  result_s3_key  TEXT,
  prompt_used    TEXT,
  gemini_request_id TEXT,
  cost_usd       DECIMAL(6,4),
  is_selected    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by     UUID REFERENCES users(id)
);

CREATE INDEX idx_projects_manager ON projects(manager_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created ON projects(created_at DESC);
CREATE INDEX idx_generations_project ON generations(project_id, created_at DESC);
```

---

## Интеграция Nano Banana (ТЗ 7.3)

**Docs:** https://ai.google.dev/gemini-api/docs/image-generation

**Модель:** `gemini-2.5-flash-image` (Nano Banana)

**Flow:**
1. Менеджер загрузил фото участка → сохранено в S3 → `photo_id`
2. Выбрал модель (КР-001) и ракурс (front) → клиент отправляет `POST /projects/:id/compose`
3. Backend читает фото + берёт соответствующий PNG из `/renders/kr-001/front.png`
4. Отправляет в Gemini API с промптом:

```
Take the transparent PNG of the wooden gazebo and place it naturally on the grass area
of the lawn in the main photo. Match the lighting direction of the original photo
(light from [direction]). Add a realistic shadow under the gazebo. Keep the gazebo's
wooden texture, proportions, and architectural details exactly as in the PNG.
The gazebo should look like it's physically present on the lawn, not floating or pasted.
```

5. Возвращённое изображение сохраняется в S3 → запись в `generations`
6. Счётчик попыток ≤5 на проект (контроль бюджета: ~$0.039 × 5 = $0.20 / клиент)

**Errors & retry:**
- 429 (rate limit) → экспоненциальный backoff
- Невалидный результат (артефакты) → кнопка «Перегенерировать» без инкремента счётчика, если предыдущий был помечен как bad

---

## Библиотека рендеров (ТЗ 7.2)

Структура `renders/`:
```
renders/
  kr-001/ (front.png, 34-left.png, 34-right.png, back.png, birdeye.png, night.png)
  kr-002/ …
  ... kr-011/
```

Требования к PNG:
- Прозрачный фон (альфа-канал)
- ≥2000×2000 px
- Естественные тени (солнце в зените)
- Без окружения (травы, цветов)

⚠️ **Эту библиотеку должен подготовить 3D-дизайнер отдельно.** В репозитории — заглушки.

---

## PDF-шаблон (ТЗ 7.5)

Puppeteer рендерит HTML-шаблон в PDF A4:
- Стр. 1: титульная — логотип, имя клиента, дата
- Стр. 2: 4 ракурса (2×2)
- Стр. 3: описание модели + базовая смета
- Стр. 4: контакты менеджера + условия заказа

Шрифты: Playfair Display + Montserrat (встроенные в PDF).
Целевой размер: ≤8 МБ.

---

## Безопасность (ТЗ 7.6)

- bcrypt(10) для паролей
- JWT: access 15m + refresh 7d, rotation при refresh
- CSRF-защита для не-API роутов (если будет admin-cookie)
- HTTPS обязательно (Let's Encrypt + automated renewal)
- Rate limiting: 60 req/min на менеджера
- Полный аудит-лог входов и генераций
- IP-allowlist для /admin/* (опционально, через nginx)

---

## Аналитика (ТЗ 7.7)

Dashboard-метрики:
- Проекты за период
- Среднее время create → sent (цель: <15 мин)
- Количество генераций за период
- Топ 5 моделей
- Стоимость Gemini API за период

---

## Тестирование качества (ТЗ 7.8)

Перед продакшеном:
1. 20 реальных фото участков → 3 модели × 2 ракурса = 120 генераций
2. Оценка: сколько из 120 приемлемых без ручной правки
3. ≥70% → в прод. <70% → доработка промптов или fallback на ручной режим.

---

## Env-переменные (пример)

```bash
# backend/.env.example
DATABASE_URL=postgres://user:pass@localhost:5432/kronov_admin
JWT_SECRET=<random-32-bytes>
JWT_REFRESH_SECRET=<random-32-bytes>
S3_ENDPOINT=https://storage.yandexcloud.net
S3_BUCKET=kronov-admin
S3_ACCESS_KEY=<access_key>
S3_SECRET_KEY=<secret_key>
GEMINI_API_KEY=<google_ai_studio_key>
SMTP_HOST=smtp.yandex.ru
SMTP_USER=info@kronov.by
SMTP_PASS=<pass>
FRONTEND_URL=https://admin.kronov.by
```

---

## Оценка объёма работ

| Этап | Срок |
|------|------|
| Scaffolding (этот шаг) | ✅ сделано |
| Backend: auth + projects CRUD + S3 upload | 5–7 дней |
| Frontend: login + projects list + new project | 4–5 дней |
| Nano Banana integration + generation UI | 5–7 дней |
| PDF генерация + отправка email/WhatsApp | 3–4 дня |
| Dashboard + settings + users management | 3–4 дня |
| Тестирование качества API (ТЗ 7.8) + деплой | 3–5 дней |
| **Итого** | **3–4 рабочих недели** |

---

## Следующие шаги для разработчика

1. `cd admin/backend && npm init -y && npm install express pg bcrypt jsonwebtoken aws-sdk multer dotenv cors` (или аналог на FastAPI)
2. `cd admin/frontend && npm create vite@latest . -- --template react-ts && npm install tailwindcss @tanstack/react-query react-router-dom axios`
3. Создать миграции PostgreSQL (см. схему выше)
4. Реализовать endpoints из контракта
5. Связать с библиотекой рендеров в `admin/renders/` (заполнит 3D-дизайнер)
6. Получить Gemini API ключ в Google AI Studio
7. Провести тест качества на 20 реальных фото
