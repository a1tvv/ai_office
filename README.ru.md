[English](README.md) | **Русский**

# ai_office

«ИИ-офис» в Telegram: каждый бот — отдельная ИИ-личность, с которой можно обсудить идеи для стартапа.

![demo](docs/demo.gif)
<!-- TODO: добавить короткую запись чата как docs/demo.gif -->

## Возможности

- `ilon.py` — инженер, который мыслит от первых принципов: разбирает идею до самой основы и помогает её улучшить
- `volya.py` — критик в стиле стендап-комика: проверяет идеи на прочность острым и прямым юмором
- Любая LLM через OpenRouter — выбирается через `MODEL`
- У каждого пользователя своя память диалога (последние N обменов сообщениями); `/reset` очищает её, `/whoami` показывает твой Telegram ID
- Доступ только для Telegram-пользователей из списка
- Long polling для локального запуска, вебхуки для хостинга (например, Render)

## Стек

Python · aiogram 3 · httpx · OpenRouter API · python-dotenv

## Быстрый старт

```bash
git clone https://github.com/a1tvv/ai_office.git && cd ai_office
pip install -r requirements.txt
cp .env.example .env    # впиши значения
python ilon.py          # или: python volya.py
```

## Настройки

Настройки берутся из `.env` (см. [`.env.example`](.env.example)):

| Переменная | Для чего |
|---|---|
| `ilon_token`, `volya_token` | Токены Telegram-ботов от @BotFather, по одному на бота |
| `OPENROUTER_API_KEY` | API-ключ OpenRouter |
| `ALLOWED_USER_IDS` | Telegram ID пользователей через запятую, которым можно писать ботам |
| `MODEL` | ID модели в OpenRouter; у каждого бота своя модель по умолчанию |
| `HISTORY_LIMIT` | Сколько последних обменов сообщениями помнит каждый бот (по умолчанию `12`) |
| `USE_WEBHOOK`, `WEBHOOK_BASE`, `WEBHOOK_SECRET`, `PORT` | Режим вебхуков для хостинга: поставь `USE_WEBHOOK=1` и укажи публичный базовый URL |

## Лицензия

[MIT](LICENSE)
