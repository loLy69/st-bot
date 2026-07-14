# MindSpark

Готовый шаблон Telegram-бота для школы, учебного центра или команды репетиторов.

## Возможности

- роли ученика, родителя, преподавателя и администратора;
- каталог групповых и индивидуальных курсов;
- расписание, ограничение мест, запись и отмена;
- разовые платежи и абонементы через загрузку чека;
- ручная проверка платежей и автоматическая активация курса;
- кабинеты участников, связь родителей с учениками;
- домашние задания, объявления и массовая рассылка;
- админ-панель со статистикой, курсами, занятиями и пользователями;
- SQLite с внешними ключами и постоянным Docker-томом;
- healthcheck и автоматический перезапуск контейнера.

## Быстрый локальный запуск

Требуется Python 3.11+.

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
copy mindspark_bot/.env.example .env
```

Заполните `.env`, затем:

```bash
cd mindspark_bot
python main.py
```

## Настройка Telegram

1. Создайте нового бота через `@BotFather` командой `/newbot`.
2. Узнайте свой числовой Telegram ID через специального информационного бота.
3. Скопируйте `mindspark_bot/.env.example` в `.env` в корне проекта.
4. Запишите новый токен в `BOT_TOKEN`, а свой ID — в `ADMIN_IDS`.
5. Никогда не добавляйте `.env` в Git.

## Развёртывание на Ubuntu VPS

Установите Git и Docker Engine с Compose plugin, затем:

```bash
git clone https://github.com/loLy69/st-bot.git mindspark
cd mindspark
cp mindspark_bot/.env.example .env
nano .env
docker compose up -d --build
docker compose logs -f bot
```

Проверка состояния на сервере:

```bash
curl http://127.0.0.1:8080/health
```

Обновление:

```bash
git pull --ff-only
docker compose up -d --build
```

База хранится в Docker volume `mindspark_data`. Для резервной копии остановите контейнер или используйте SQLite backup API; не копируйте активный файл базы обычной командой без проверки целостности.

На VPS скрипт `scripts/backup.sh` создаёт согласованную SQLite-копию и хранит архивы 14 дней. Его можно запускать ежедневно через cron.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | Новый токен от BotFather |
| `ADMIN_IDS` | Telegram ID администраторов через запятую |
| `DB_PATH` | Путь к SQLite; в Docker `/app/data/mindspark.db` |
| `SCHOOL_NAME` | Название школы |
| `SUPPORT_USERNAME` | Username поддержки без `@` |
| `PAYMENT_DETAILS` | Инструкция и реквизиты оплаты |
| `TIMEZONE` | Часовой пояс |
| `PORT` | Порт healthcheck |

## Команды

- `/start` — регистрация или главное меню;
- `/menu` — главное меню;
- `/cancel` — отменить текущий сценарий.

Администратор определяется только по `ADMIN_IDS`. Заявки преподавателей требуют одобрения в админ-панели.
