"""AI-офис — Инженер первых принципов.

Запуск:
    pip install "aiogram>=3.13,<4" httpx python-dotenv
    # .env: ilon_token=... OPENROUTER_API_KEY=... ALLOWED_USER_IDS=... MODEL=deepseek/deepseek-v4-flash
    python ilon.py

На Render: USE_WEBHOOK=1, WEBHOOK_BASE=https://<service>.onrender.com
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections import defaultdict, deque

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

# ─────────────────────────── конфиг ───────────────────────────

load_dotenv()

BOT_TOKEN      = os.environ["ilon_token"]
OPENROUTER_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL          = os.getenv("MODEL", "deepseek/deepseek-v4-flash")
ALLOWED        = {int(x) for x in os.getenv("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x}
HISTORY_PAIRS  = int(os.getenv("HISTORY_LIMIT", "12"))
USE_WEBHOOK    = os.getenv("USE_WEBHOOK", "0") == "1"
WEBHOOK_BASE   = os.getenv("WEBHOOK_BASE", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me")
WEBHOOK_PATH   = "/tg/webhook"
PORT           = int(os.getenv("PORT", "8080"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("ilon")

# ─────────────────────────── персона ───────────────────────────

SYSTEM_PROMPT = ("""Ты — Илон Маск Инженер первых принципов, мыслящий по методологии Илона Маска. Твоя цель — не раскритиковать ради критики, а помочь собеседнику очистить идею от шелухи, оптимизировать её до атомов и запустить в космос. Вы в одной лодке, и твоя честность — это забота о том, чтобы проект не разбился о реальность.

            ТОН
            Увлеченный, прагматичный, открытый и интеллектуально честный. Никакого дежурного «отличный вопрос» или «крутая идея» — вместо этого сразу переходи к сути с огоньком и любопытством инженера. Ты не грубишь и не называешь идеи «тупыми», но прямо и аргументированно указываешь на слабые места, руководствуясь логикой и цифрами. Ты общаешься на равных, как главный инженер с ведущим конструктором.

            МЕТОД (Пятишаговый алгоритм Маска)
            Применяй его строго последовательно к любой задаче или идее:

            1. Сделай требования менее глупыми. 
            Любое требование изначально ошибочно, особенно если оно исходит от «умного человека» или «рыночных стандартов». Спроси: кто конкретно автор этого ограничения/требования? Если автора нет или это абстрактный «рынок» — подвергни требование сомнению.
            2. Удали всё, что возможно. 
            Не пытайся улучшить то, чего не должно существовать. Предложи вырезать функции, шаги, процессы, экраны или детали. Если в процессе работы нам не придется возвращать обратно хотя бы 10% удаленного — значит, мы удалили слишком мало.
            3. Упрости и оптимизируй. 
            Применяй этот шаг только к тому, что выжило после шага 2. Жестко пресекай попытки оптимизировать мусорные процессы или функции.
            4. Ускорь цикл (итерации). 
            Как сделать так, чтобы проверить эту идею или выпустить MVP в 5 раз быстрее? Сокращай время доставки ценности, но только после того, как требования упрощены.
            5. Автоматизируй. 
            Делай это в самую последнюю очередь. Автоматизация неэффективного процесса — это умножение хаоса.

            ПРАВИЛА МЫШЛЕНИЯ
            — Своди всё к первым принципам: законам физики (гравитация, термодинамика, прочность материалов) и фундаментальной экономике (себестоимость материалов, человеко-часы, юнит-экономика).
            — Аналогии — под запретом. Аргументы в стиле «так делает Apple/Tesla/конкуренты» не принимаются. Важно только то, как это работает на уровне базовых элементов.
            — Требуй метрики и физические величины. Переводи абстрактные рассуждения в конкретные цифры (кг, секунды, рубли/доллары, конверсии).
            — Если говорят «это невозможно», разложи задачу: какие законы природы это запрещают? Если физика не против — значит, это просто вопрос бюджета, инженерии и времени.

            ФОРМАТ ОТВЕТА
            1. Главный барьер: Сфокусированный разбор самого уязвимого места идеи (физического или экономического).
            2. Оптимизация по алгоритму: Пошаговый разбор (Шаги 1–5), где ты предлагаешь, что убрать, что упростить и как ускориться.
            3. Быстрый тест (Тест на 72 часа): Конкретный, дешевый эксперимент, который покажет жизнеспособность идеи на практике без огромных вложений.
            4. Один сильный, направляющий вопрос на подумать."""
)

TEMPERATURE = 0.4

# ─────────────────────────── состояние ───────────────────────────

_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_PAIRS * 2))

# ─────────────────────────── LLM ───────────────────────────

_http = httpx.AsyncClient(
    timeout=90.0,
    headers={
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "X-Title": "ai-office",
    },
)


async def complete(messages: list[dict]) -> str:
    resp = await _http.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={
            "model": MODEL,
            "temperature": TEMPERATURE,
            "max_tokens": 1200,
            "provider": {"sort": "price"},
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        },
    )
    if resp.status_code != 200:
        log.error("OpenRouter %s: %s", resp.status_code, resp.text[:400])
        raise RuntimeError(resp.status_code)
    return resp.json()["choices"][0]["message"]["content"].strip()


# ─────────────────────────── бот ───────────────────────────

dp = Dispatcher()
TG_LIMIT = 4000


def allowed(m: Message) -> bool:
    return not ALLOWED or (m.from_user and m.from_user.id in ALLOWED)


def chunks(text: str) -> list[str]:
    out, buf = [], ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > TG_LIMIT:
            out.append(buf)
            buf = ""
        buf += line + "\n"
    if buf.strip():
        out.append(buf)
    return out or [text]


@dp.message(CommandStart())
async def start(m: Message) -> None:
    if not allowed(m):
        return await m.answer(f"Доступ закрыт. id: <code>{m.from_user.id}</code>")
    await m.answer(
        "<b>Инженер первых принципов</b>\n"
        "Опиши задачу или решение — получишь разбор, а не одобрение.\n\n"
        "/reset — очистить историю"
    )


@dp.message(Command("whoami"))
async def whoami(m: Message) -> None:
    await m.answer(f"id: <code>{m.from_user.id}</code>")


@dp.message(Command("reset"))
async def reset(m: Message) -> None:
    if not allowed(m):
        return
    _history.pop(m.from_user.id, None)
    await m.answer("История очищена.")


@dp.message(F.text)
async def on_text(m: Message) -> None:
    if not allowed(m):
        return await m.answer(f"Доступ закрыт. id: <code>{m.from_user.id}</code>")

    uid = m.from_user.id
    await m.bot.send_chat_action(m.chat.id, "typing")

    msgs = [*_history[uid], {"role": "user", "content": m.text}]
    try:
        answer = await complete(msgs)
    except Exception as exc:
        log.warning("fail: %s", exc)
        return await m.answer("Модель не ответила. Повтори через минуту.")

    _history[uid].append({"role": "user", "content": m.text})
    _history[uid].append({"role": "assistant", "content": answer})

    for part in chunks(answer):
        await m.answer(part)


# ─────────────────────────── запуск ───────────────────────────

async def main() -> None:
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        if USE_WEBHOOK:
            from aiohttp import web
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

            url = WEBHOOK_BASE.rstrip("/") + WEBHOOK_PATH
            await bot.set_webhook(url, secret_token=WEBHOOK_SECRET, drop_pending_updates=True)
            app = web.Application()
            app.router.add_get("/health", lambda _r: web.Response(text="ok"))
            SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET).register(
                app, path=WEBHOOK_PATH
            )
            setup_application(app, dp, bot=bot)
            runner = web.AppRunner(app)
            await runner.setup()
            await web.TCPSite(runner, "0.0.0.0", PORT).start()
            log.info("webhook: %s", url)
            await asyncio.Event().wait()
        else:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
    finally:
        await _http.aclose()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)