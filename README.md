# Business Manager System

MVP система управления командами и задачами, построенная на FastAPI с поддержкой аутентификации, управления пользователями, командами, задачами и встречами.

## 🚀 Возможности

- **Управление пользователями**: Регистрация, аутентификация, JWT токены
- **Команды**: Создание команд, управление участниками
- **Задачи**: Система задач с оценками и отслеживанием прогресса
- **Встречи**: Планирование и управление встречами
- **Календарь**: Интеграция календарных событий
- **API Documentation**: Автоматическая генерация документации с Swagger/OpenAPI

## 🛠 Технологический стек

- **Backend**: FastAPI 0.115.12
- **База данных**: PostgreSQL 17.2 с SQLAlchemy (async)
- **Аутентификация**: JWT с PyJWT
- **Валидация**: Pydantic v2
- **Миграции**: Alembic
- **Хеширование паролей**: bcrypt
- **Тестирование**: pytest с поддержкой async
- **Управление зависимостями**: Poetry

## 📋 Требования

- Python 3.12+
- PostgreSQL 17.2+
- Poetry (для управления зависимостями)

## 🔧 Установка и настройка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd business_manager_ci
```

### 2. Установка зависимостей

```bash
# Установка Poetry (если не установлен)
curl -sSL https://install.python-poetry.org | python3 -

# Установка зависимостей проекта
poetry install
```

### 3. Настройка окружения

Скопируйте шаблон конфигурации и заполните необходимые переменные:

```bash
cp src/.env.template src/.env
```

Отредактируйте файл `src/.env`:

```env
# Основная база данных
DB_CONFIG__DB_NAME=your_db_name
DB_CONFIG__DB_USER=your_db_user
DB_CONFIG__DB_PASSWORD=your_db_password
DB_CONFIG__DB_PORT=5432

# Тестовая база данных
TEST_DB_CONFIG__DB_NAME=test_db_name
TEST_DB_CONFIG__DB_USER=test_db_user
TEST_DB_CONFIG__DB_PASSWORD=test_db_password
TEST_DB_CONFIG__DB_PORT=5433

# JWT настройки
AUTH__SECRET_KEY=your-super-secret-key-here
AUTH__ALGORITHM=HS256
AUTH__ACCESS_TOKEN_EXPIRE_MINUTES=30
AUTH__REFRESH_TOKEN_EXPIRE_DAYS=7

# Настройки приложения
APP_CONFIG__HOST=0.0.0.0
APP_CONFIG__PORT=8000
APP_CONFIG__RELOAD_MODE=true

# Bcrypt настройки
BCRYPT_SETTINGS__DEFAULT_ROUNDS_VALUE=12
```

### 4. Запуск с Docker Compose

Для быстрого старта используйте Docker Compose:

```bash
# Запуск баз данных
docker-compose up -d

# Или запуск всех сервисов
docker-compose up
```

### 5. Миграции базы данных

```bash
# Переход в директорию проекта
cd src

# Применение миграций
poetry run alembic upgrade head
```

## 🚀 Запуск приложения

### Режим разработки

```bash
cd src
poetry run python main.py
```

### Продакшен режим

```bash
cd src
poetry run uvicorn main:app --host 0.0.0.0 --port 8000
```

Приложение будет доступно по адресу:
- **API**: http://localhost:8000
- **Документация**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Тестирование

Проект настроен с полным покрытием тестами и CI/CD pipeline.

### Запуск всех тестов

```bash
cd src
poetry run pytest -v
```

### Запуск unit тестов

```bash
cd src
poetry run pytest tests/unit/ -v
```

### Запуск тестов с покрытием

```bash
cd src
poetry run pytest --cov=. --cov-report=html
```

### Типы тестов

- `unit`: Юнит тесты
- `integration`: Интеграционные тесты  
- `api`: API тесты
- `slow`: Медленные тесты

Пример запуска определенного типа тестов:

```bash
poetry run pytest -m "unit" -v
```

## 🔄 CI/CD

Проект использует GitHub Actions для автоматического тестирования:

### Workflow стратегии:

- **quick-check**: Проверка форматирования (black, flake8) для feature веток
- **develop-check**: Unit тесты для ветки develop
- **full-check**: Полное тестирование с PostgreSQL для main/master веток и PR

### Переменные окружения для CI:

Настройте следующие секреты в GitHub:

```
DB_CONFIG__DB_PASSWORD
TEST_DB_CONFIG__DB_PASSWORD
AUTH__SECRET_KEY
```

## 📁 Структура проекта

```
business_manager_ci/
├── .github/workflows/       # CI/CD конфигурации
├── src/                    # Исходный код
│   ├── core/              # Основные настройки и конфигурация
│   ├── users/             # Модуль пользователей
│   ├── teams/             # Модуль команд
│   ├── tasks/             # Модуль задач
│   ├── meetings/          # Модуль встреч
│   ├── calendars/         # Модуль календаря
│   ├── evaluations/       # Модуль оценок
│   ├── tests/             # Тесты
│   ├── static/            # Статические файлы
│   ├── main.py            # Точка входа приложения
│   └── .env.template      # Шаблон переменных окружения
├── compose.yaml           # Docker Compose конфигурация
├── pyproject.toml         # Poetry конфигурация и зависимости
└── README.md             # Документация проекта
```

## 📚 API Endpoints

### Аутентификация (`/api/auth`)
- Регистрация и авторизация пользователей
- JWT токены (access и refresh)

### Пользователи (`/api/users`)
- CRUD операции с пользователями
- Профили пользователей

### Команды (`/api/teams`)
- Управление командами
- Участники команд

### Задачи (`/api/tasks`)
- CRUD задач
- Назначение исполнителей

### Встречи (`/api/meetings`)
- Планирование встреч
- Управление участниками

### Календарь (`/api/calendar`)
- Календарные события
- Интеграция с задачами и встречами

### Оценки (`/api/evaluations`)
- Система оценок задач
- Метрики производительности

## 🔧 Разработка

### Форматирование кода

```bash
# Форматирование с black
poetry run black src/

# Проверка с flake8
poetry run flake8 src/
```

### Создание миграций

```bash
cd src
poetry run alembic revision --autogenerate -m "Description of changes"
poetry run alembic upgrade head
```

## 🤝 Участие в разработке

1. Создайте форк репозитория
2. Создайте feature ветку (`git checkout -b feature/AmazingFeature`)
3. Зафиксируйте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Отправьте в ветку (`git push origin feature/AmazingFeature`)
5. Создайте Pull Request

### Правила коммитов

Следуйте conventional commits format:
- `feat:` - новая функциональность
- `fix:` - исправление багов
- `docs:` - изменения в документации
- `test:` - добавление или изменение тестов
- `refactor:` - рефакторинг кода

## 📝 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для подробностей.

## 👤 Автор

**AleksGin** - [alexanderginin@icloud.com](mailto:alexanderginin@icloud.com)

## 🆘 Поддержка

Если у вас возникли вопросы или проблемы, создайте [Issue](../../issues) в репозитории.