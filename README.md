# Журнал силовых тренировок

Мобильный веб-журнал на Django: тренировки и подходы, отдельный вес каждого подхода, упражнения со своим весом, каталог упражнений, история веса тела и личные показатели.

## Возможности

- регистрация и вход по email, восстановление пароля через SMTP;
- живые тренировки и внесение занятий задним числом;
- нагрузка на каждый подход: обычный вес либо `+/-` корректировка собственного веса;
- повтор любой тренировки новым черновиком;
- общий каталог из 1324 упражнений, личные названия и собственные упражнения;
- профиль с датой рождения, ростом и полной историей веса тела;
- строгая изоляция данных разных пользователей.

## Локальный запуск

```powershell
uv sync --all-groups
uv run python manage.py migrate
uv run python manage.py runserver
```

Без импортированного датасета каталог будет пуст. Для его загрузки:

```powershell
uv run python scripts/fetch_dataset.py
uv run python scripts/fetch_frontend_assets.py
uv run python manage.py import_exercises
```

## Docker Compose

Скопируйте `.env.example` в `.env`, замените секреты и домен, затем выполните. Если пароль или `DJANGO_SECRET_KEY` содержит символ `$`, заключите все значение в одинарные кавычки, например `POSTGRES_PASSWORD='a$b'`; иначе Compose воспримет часть секрета как имя переменной.

```bash
docker compose up --build -d
docker compose ps
```

Приложение доступно только на `127.0.0.1:8000`; внешний Nginx должен проксировать домен на этот адрес. Пример находится в `deploy/nginx.conf.example`. Миграции, импорт каталога и сборка статики выполняются при старте контейнера. Импорт идемпотентен.

Резервная копия и восстановление PostgreSQL:

```bash
docker compose exec -T db pg_dump -U gym -d gym -Fc > backups/gym.dump
docker compose exec -T db pg_restore -U gym -d gym --clean --if-exists < backups/gym.dump
```

## Медиа и лицензия

Текстовые данные исходного [exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) опубликованы по MIT. Изображения и GIF принадлежат Gym visual, требуют сохранения атрибуции и могут требовать отдельной лицензии. Docker-сборка загружает их из зафиксированной ревизии `118e4bd`; владелец развертывания обязан проверить право использования до публикации. Клонирование датасета не предоставляет лицензию на медиа — см. [NOTICE](https://github.com/hasaneyldrm/exercises-dataset/blob/main/NOTICE.md).

## Проверки

```bash
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check
uv run pytest
```
