# TaskFlow 🚀

![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)
![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)
![Redis 7](https://img.shields.io/badge/Redis-7-DC382D.svg)

**TaskFlow** — многопользовательский таск-трекер с таймлайнами проектов, трекером привычек, личными и командными заметками, учётом времени и системой уведомлений в реальном времени.

Проект разработан в рамках учебного курса «Объектно-ориентированное программирование» (2 семестр). Backend предоставляет строго типизированный REST API контракт для независимой frontend-команды.

---

## 📋 Особенности и архитектура

- **Доменная модель (18 таблиц / 9+ объектов реального мира):**
  - Пользователи (`User`, `RefreshToken`, `NotificationSetting`)
  - Организация (`Workspace`, `WorkspaceMember`, `Project`, `Milestone`, `Label`, `TaskLabel`)
  - Задачи и коммуникация (`Task`, `Comment`, `Attachment`)
  - Учёт времени и привычки (`TimeEntry`, `Habit`, `HabitCheckin`)
  - Заметки и аудит (`Note`, `Notification`, `ActivityLog`)
- **Безопасность и аутентификация:**
  - Argon2id для хеширования паролей (устойчив к GPU-атакам)
  - JWT access-токены (15 мин) + непрозрачные (opaque) refresh-токены с автоматической ротацией
  - Черный список отозванных токенов в Redis (мгновенный logout и выход со всех устройств)
- **Использование Redis:**
  - Кэш сущностей и списков задач
  - Rate limiting (скользящее окно на основе `INCR + EXPIRE`)
  - Брокер очередей и планировщик для фонового воркера **ARQ**
  - Pub/Sub для трансляции WebSocket-уведомлений
- **Надёжность и целостность данных:**
  - Оптимистичные блокировки (`version`) для предотвращения конфликтов конкурентного редактирования
  - Полнотекстовый поиск (PostgreSQL FTS с русским стеммингом `tsvector` + GIN индексы)
  - Мягкое удаление (`SoftDeleteMixin`) с сохранением истории
  - Ограничение на 1 активный таймер на уровне БД (`partial UNIQUE index`)
- **Ограничения ресурсов (Arch Linux, 8 ГБ ОЗУ):**
  - Суммарный лимит всех сервисов в compose < 1.5 ГБ (app: 512MB, postgres: 512MB, redis: 256MB, worker: 256MB)
  - Отсутствие тяжёлых JVM-компонентов (никаких Kafka / Elasticsearch)

---

## 🛠 Быстрый старт (Docker Compose)

### 1. Клонирование и настройка переменных окружения

```bash
cp .env.example .env
```

### 2. Запуск одной командой

```bash
docker compose up --build -d
```

### 3. Применение миграций и загрузка демо-данных

```bash
make migrate
make seed
```

После этого API доступно:
- **Swagger / OpenAPI:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **ReDoc:** [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)
- **Health check:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

### Демо-пользователи (создаются через seed):
| Email | Пароль | Роль в демо-workspace |
|---|---|---|
| `alice@example.com` | `Password123` | **Owner** |
| `bob@example.com` | `Password123` | **Member** |
| `charlie@example.com` | `Password123` | **Viewer** |

---

## 💻 Локальная разработка без Docker

### Требования
- Python 3.12+
- PostgreSQL 16
- Redis 7

```bash
# Установка виртуального окружения и зависимостей разработки
make install
make pre-commit-install

# Запуск тестов
make test

# Проверка качества кода (линтер + типы)
make check
```

---

## 🗂 Структура проекта

```
.
├── alembic/                 # Миграции базы данных (версии, конфигурация)
├── app/
│   ├── api/v1/              # Роутеры, эндпоинты, зависимости FastAPI
│   │   ├── endpoints/       # auth, health, workspaces, tasks...
│   │   ├── deps.py          # Dependency injection (DB, Redis, Auth, RBAC)
│   │   └── router.py        # Агрегация маршрутов /api/v1
│   ├── core/                # Конфигурация (pydantic-settings), security, errors, logging
│   ├── db/                  # Сессии SQLAlchemy, async engine, redis, seed-скрипты
│   ├── models/              # 18 моделей SQLAlchemy (миксины, связи, индексы)
│   ├── repositories/        # Слой абстракции доступа к данным (Generic CRUD)
│   ├── schemas/             # Pydantic v2 схемы валидации (Request/Response)
│   ├── services/            # Бизнес-логика приложения
│   ├── workers/             # Фоновые задачи arq (streak, дедлайны, очистка)
│   └── main.py              # Фабрика FastAPI приложения, lifespan, CORS
├── docker/                  # Dockerfile (multi-stage)
├── tests/                   # Автотесты (pytest-asyncio, fixtures)
├── API_CONTRACT.md          # Контракт взаимодействия с фронтендом
├── docker-compose.yml       # Спецификация сервисов с лимитами памяти
├── Makefile                 # Команды управления проектом
└── pyproject.toml           # Зависимости и конфигурации инструментов
```

---

## 🧪 Запуск тестов

```bash
# Обычный прогон
make test

# С формированием отчета о покрытии
make test-cov
```

---

## 📖 Документация и материалы проекта
- [Материалы для защиты проекта (сценарий демо + Q&A)](DEFENSE_MATERIALS.md)
- [Стратегия масштабирования и ограничения архитектуры](SCALING_AND_LIMITS.md)
- [Контракт REST API для Frontend-команды](API_CONTRACT.md)
- [OpenAPI 3.1 спецификация (JSON)](openapi.json)
- [Дизайн и проектирование системы (Этап 0)](/home/opium/.gemini/antigravity-cli/brain/16863016-0103-4821-a1ef-34c97bbfcabf/STAGE_0_DESIGN.md)
