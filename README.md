<div align="center">

# AI Manager

**Telegram-бот и веб-приложение, где ИИ распределяет задачи между сотрудниками, собирает статусы и пишет протоколы планёрок**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT-412991?style=for-the-badge&logo=openai&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

</div>

<!-- TODO: скриншот веб-интерфейса (чат) и бота -->

## 📖 О проекте

AI Manager помогает руководителю не раздавать поручения вручную. Руководитель пишет ИИ-ассистенту в чат (в вебе или в Telegram Mini App) «распредели задачи» — модель смотрит на список сотрудников и текущие задачи и возвращает готовый набор задач с исполнителями и дедлайнами. Сотрудники получают задачи в Telegram-боте и сами меняют статус, а руководитель — уведомление, когда задача выполнена.

## ✨ Возможности

- **Распределение задач ИИ** — по фразе «распредели задачи» модель возвращает JSON-массив задач (название, описание, дедлайн, исполнитель, статус).
- **Статусы и планёрки** — команды «статус по задачам», «статус по всем задачам», «начало пятиминутки» (доступны только руководителям).
- **Протокол пятиминутки** — загрузка аудио (`mp3` / `wav` / `m4a` / `ogg`), расшифровка Whisper и протокол по жёсткому шаблону; готовый протокол отправляется в Telegram-группу.
- **Чаты с ИИ** — история переписки, проекты, поиск по чатам и сообщениям, учёт токенов и стоимости за день.
- **Анализ файлов** — текст (`txt` / `csv` / `md`), `docx`, `pdf`, изображения и аудио добавляются в контекст запроса.
- **Telegram-бот для сотрудников** — регистрация (`/register`: ФИО и департамент), список «📈 Мои задачи», смена статуса, комментарии к задачам, вложенные файлы.
- **Уведомления** — исполнитель получает новую задачу, руководитель — сообщение «Задача выполнена».
- **Импорт чатов** — `/export_chats`: бот принимает `chat.html` (экспорт чатов ChatGPT, до 100 МБ) и сохраняет диалоги в БД.
- **Веб-интерфейс** — Jinja2-страницы с Telegram WebApp SDK (Mini App): чат, список и карточка задач, статистика токенов.

## 🧱 Стек

| Технология | Роль |
|---|---|
| FastAPI, Uvicorn | REST API и раздача веб-страниц |
| aiogram 3 | Telegram-бот (FSM, inline-клавиатуры, long polling) |
| OpenAI API (`gpt-4o`, `whisper-1`, модель из `CHAT_GPT_MODEL`) | диспетчеризация задач, ответы, расшифровка аудио |
| SQLAlchemy 2 (async), asyncpg, aiosqlite | ORM и драйверы БД |
| PostgreSQL 15 | основное хранилище (полнотекстовый индекс по задачам) |
| Alembic | миграции (конфигурация в `app/migration`) |
| Jinja2 + JS | веб-страницы, Telegram WebApp |
| PyPDF2, python-docx, pydub, tiktoken | обработка файлов и подсчёт токенов |
| Docker, Amvera | контейнеризация и деплой |

## 🗂 Структура проекта

```text
AI_manager/
├── app/
│   ├── main.py            # FastAPI + запуск бота (lifespan), /webhook
│   ├── config.py          # настройки из .env
│   ├── database.py        # async-движок, сессии, Base
│   ├── bot/               # aiogram: хендлеры, клавиатуры, уведомления
│   ├── chat_gpt/          # чаты, сообщения, OpenAI-логика, протоколы, токены
│   ├── tasks/             # задачи (модели, DAO, роуты, загрузка файлов)
│   ├── project/           # проекты
│   ├── users/             # сотрудники
│   ├── pages/             # HTML-страницы (Jinja2)
│   ├── templates/ static/ # шаблоны и статика
│   └── migration/         # окружение Alembic
├── Dockerfile
├── docker-compose.yml     # PostgreSQL + приложение
├── amvera.yml             # конфигурация деплоя на Amvera
└── requirements.txt
```

## 🚀 Быстрый старт

```bash
git clone https://github.com/Edvvard0/AI_manager.git
cd AI_manager

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# PostgreSQL 15 из docker-compose.yml
docker compose up -d db

# создайте .env в корне репозитория (переменные — в разделе «Конфигурация»)

uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Бот запускается вместе с приложением (long polling). Swagger: `http://localhost:8080/docs`, веб-интерфейс: `http://localhost:8080/pages/`.

> Для работы Telegram Mini App нужен публичный HTTPS-адрес (в коде есть пример запуска через ngrok).

## ⚙️ Конфигурация

Все настройки читаются из `.env` в корне репозитория (`app/config.py`).

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | токен Telegram-бота |
| `ADMIN_IDS` | Telegram ID администраторов (список), получают сообщения о запуске и остановке бота |
| `DB_URL` | строка подключения SQLAlchemy (`postgresql+asyncpg://...`) |
| `BASE_SITE` | публичный адрес сервиса |
| `CHAT_GPT_API_KEY` | ключ OpenAI API |
| `CHAT_GPT_MODEL` | модель для чатов и распределения задач |
| `FORMAT_LOG`, `LOG_ROTATION` | формат и ротация логов (необязательно) |

## 🔌 API / Команды

**Команды бота:** `/start`, `/register`, `/export_chats`, кнопка «📈 Мои задачи».

<details>
<summary>HTTP API (основные группы)</summary>

| Группа | Маршруты |
|---|---|
| `/chat_gpt` | `/chats/all`, `/chats/{tg_id}`, `/messages/{chat_id}`, `/message_all`, `/analyze` (протокол из аудио), `/search`, `/token_info/`, `/file/{path}` |
| `/tasks` | CRUD задач, `/upload_file/{task_id}`, `/filters/`, `/search/tasks`, `/user/{tg_id}` |
| `/projects` | CRUD проектов, `/by_tg/{tg_id}`, `/{project_id}/chats` |
| `/users` | CRUD сотрудников, `/tg/{tg_id}` |
| `/pages` | HTML-страницы веб-интерфейса |
| `/webhook` | приём апдейтов Telegram |

Полный список — в Swagger (`/docs`).

</details>

## 👤 Автор

**Эдвард Осипчук** — Python backend-разработчик

[![GitHub](https://img.shields.io/badge/GitHub-Edvvard0-181717?style=flat&logo=github)](https://github.com/Edvvard0)
[![Telegram](https://img.shields.io/badge/Telegram-Edward0076-26A5E4?style=flat&logo=telegram&logoColor=white)](https://t.me/Edward0076)
