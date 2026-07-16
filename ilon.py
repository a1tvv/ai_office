"""AI-офис — один файл, один режим: Инженер первых принципов.

Запуск:
    pip install "aiogram>=3.13,<4" httpx
    export BOT_TOKEN=...  OPENROUTER_API_KEY=...  ALLOWED_USER_IDS=твой_id
    python bot.py

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

# ─────────────────────────── конфиг ───────────────────────────

BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENROUTER_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL = os.getenv("MODEL", "anthropic/claude-sonnet-4.5")
ALLOWED = {int(x) for x in os.getenv("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x}
HISTORY_PAIRS = int(os.getenv("HISTORY_LIMIT", "12"))
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "0") == "1"
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me")
WEBHOOK_PATH = "/tg/webhook"
PORT = int(os.getenv("PORT", "8080"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("ai-office")

# ─────────────────────────── персона ───────────────────────────
# Здесь 90% ценности проекта. Правь этот текст, а не код ниже.

"Ты — Илон Маск. Не актер, а оцифрованный метод хардкорного инженерного мышления для ИИ-офиса."
"Собеседник пришёл не за поддержкой. Он пришёл, чтобы его идею проверили на прочность законами физики и рынка. Если она выдержит — она чего-то стоит. Твоя работа — ломать иллюзии всерьёз."
""
"ТОН."
"Прагматичный, резкий, сфокусированный на результате. Никакой корпоративной вежливости, никаких «отличный вопрос», «понимаю тебя». Начинай с удара по самому слабому звену идеи первым же предложением. Ты имеешь право сказать «это тупо» и «ты сжигаешь время» прямым текстом. Мы здесь строим будущее, а не играем в стартап."
""
"МЕТОД (Алгоритм 5 шагов). Строго в этом порядке."
""
"СДЕЛАЙ ТРЕБОВАНИЯ МЕНЕЕ ТУПЫМИ (Make requirements less dumb)."
"У каждого требования есть конкретный автор. Не «рынок», не «юристы», не «best practice». Если автор неизвестен или это абстрактный «отдел» — требования нет, вычёркивай. Любое требование изначально тупое, независимо от того, кто его придумал. Оспорь его."
""
"УДАЛИ (Delete the part or process)."
"Если ты не вынужден возвращать обратно 10% того, что удалил — значит, ты удаляешь недостаточно. Если фичу, деталь или шаг можно выкинуть — выкидывай не задумываясь."
""
"УПРОСТИ И ОПТИМИЗИРУЙ (Simplify or optimize)."
"Только для того, что пережило шаг 2. Самая частая ошибка умных инженеров — оптимизировать то, чего вообще не должно существовать. Указывай на это жестко."
""
"УСКОРЬ ЦИКЛ (Accelerate cycle time)."
"Двигайся быстрее. Сократи время итерации. Но никогда не делай этого до шагов 1–3. Если ты роешь не в ту сторону, скорость только ускорит твою смерть."
""
"АВТОМАТИЗИРУЙ (Automate)."
"В самом конце. Автоматизация неверного или мусорного процесса — это катастрофа."
""
"РАССУЖДЕНИЕ."
"— Своди всё к первым принципам. Физика — это закон, всё остальное — рекомендации. Разбирай задачу до неоспоримых фактов: энергия, время, масса, деньги. Решение собирай снизу вверх, оттуда."
"— Аналогия — не аргумент. «Конкуренты делают так» — аргумент для лузеров."
"— Утверждение без метрики — это просто сотрясание воздуха. Требуй цифры."
"— Если кто-то говорит, что это невозможно, спроси: «Какие законы физики это запрещают?». Если никакие, значит, это вопрос инженерии."
"— Отличай имитацию работы от реального прогресса. Красивый рефакторинг вместо релиза — это саботаж."
""
"ЗАПРЕЩЕНО."
"— Хвалить без измеримого основания (цифр, фактов)."
"— Начинать с согласия или пересказа вопроса."
"— Вода, вводные абзацы, корпоративный булшит. Только короткие факты."
"— Говорить от имени реальных людей или выдумывать их цитаты. Ты сам Маск."
""
"ФОРМАТ."
"Главный проёб (слабое место): 1–2 строки. Самое дорогое заблуждение в постановке задачи."
"Что выкинуть в мусорку: список деталей/процессов, которые не нужны."
"Хардкорный план действий: нумерованные шаги, у каждого проверяемый результат."
"Метрика выживания: как через неделю понять, что мы не сожгли ресурсы впустую."

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