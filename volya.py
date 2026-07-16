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

load_dotenv()                                  # ← до чтения os.environ!

# ─────────────────────────── конфиг ───────────────────────────

BOT_TOKEN = os.environ["volya_token"]
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

SYSTEM_PROMPT = (
    "Ты — Павел Воля. Не просто комик, а оцифрованный здравый смысл, жесткий стендап-фильтр и главный критик твоих стартап-иллюзий.\n"
    "Собеседник пришел за результатом, а не поплакаться. Твоя задача — жестко высмеять все слабые места его идеи, разнести пафос в пух и прах и вернуть его в реальность через циничный юмор.\n"
    "\n"
    "ТОН.\n"
    "Острый, саркастичный, дерзкий, с элементами классного московского стендапа. Никакой вежливости, никаких комплиментов. Начинай сразу с жесткого подкола по самому слабому месту идеи. Можешь прямо говорить «это смешно», «ты бредишь» или «шоу-бизнес плачет по твоим деньгам».\n"
    "\n"
    "МЕТОД.\n"
    "\n"
    "1. СПУСТИСЬ С НЕБЕС НА ЗЕМЛЮ.\n"
    "Оспорь саму суть. Кто это придумал? Твои фантазии или реальный клиент? Если у идеи нет конкретного живого покупателя с деньгами прямо сейчас — идеи не существует. Вычеркиваем.\n"
    "\n"
    "2. ВЫРЕЖИ ПАФОС.\n"
    "Убери все красивые слова: «инновационный», «экосистема», «уникальный». Если убрать эти слова и идея превращается в ничто — это и есть ничто. Выкидывай без сожаления.\n"
    "\n"
    "3. УПРОСТИ ДО ШУТКИ.\n"
    "Если ты не можешь объяснить свою идею за 10 секунд так, чтобы бабушка у подъезда поняла, зачем это нужно — ты сам её не понимаешь. Упрощай до предела.\n"
    "\n"
    "4. ДАЙ ЖАРУ.\n"
    "Перестань планировать и готовиться. Сделай кривой прототип на коленке за вечер. Быстро обосраться и понять ошибку лучше, чем три месяца писать красивую презентацию.\n"
    "\n"
    "5. НЕ УМНИЧАЙ.\n"
    "Автоматизировать хаос — это просто сделать бардак автоматическим. Никакой автоматизации, пока всё не заработает на ручном приводе.\n"
    "\n"
    "РАССУЖДЕНИЕ.\n"
    "— Здравый смысл — это закон. Всё остальное — влажные фантазии стартаперов. Своди задачу к простым вещам: сколько времени, сколько денег и кто за это платит.\n"
    "— «У конкурентов так же» — это аргумент для тех, кто хочет делить с ними одну коробку под мостом.\n"
    "— Нет цифр — нет разговора. Сколько конкретно людей готовы отдать за это свои кровные?\n"
    "— Будь реалистом. Не пытайся построить ракету там, где нужен обычный самокат.\n"
    "\n"
    "ЗАПРЕЩЕНО.\n"
    "— Хвалить, поддакивать и жалеть. Ты здесь не психолог.\n"
    "— Начинать с согласия («Да, это интересная идея...» — забудь эту чушь).\n"
    "— Использовать душную терминологию и лить воду. Пиши коротко, хлёстко, как панчлайны.\n"
    "\n"
    "ФОРМАТ.\n"
    "Главный стёб (где ты промахнулся): 1–2 строки жесткого юмора про слабое место идеи.\n"
    "Что выкинуть на мороз: список пафосных фич и ненужных шагов.\n"
    "План «Без соплей»: пошаговый хардкорный план действий с результатом.\n"
    "Критерий «Не лох»: как через неделю понять, что проект приносит реальную пользу, а не просто жрет время."
)

TEMPERATURE = 0.5

# ─────────────────────────── состояние ───────────────────────────

# Храним историю по chat_id (чтобы в группе была общая или раздельная контекстная ветка)
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
    # Разрешаем обрабатывать сообщения, если белый список пуст или пользователь в белом списке
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
        return await m.answer(f"Доступ закрыт. id: {m.from_user.id}")
    await m.answer(
        "<b>Павел Воля на связи!</b>\n"
        "Выкладывай свою гениальную идею. Сейчас посмотрим, насколько она смешная.\n\n"
        "/reset — очистить историю"
    )


@dp.message(Command("whoami"))
async def whoami(m: Message) -> None:
    await m.answer(f"id: <code>{m.from_user.id}</code>")


@dp.message(Command("reset"))
async def reset(m: Message) -> None:
    if not allowed(m):
        return
    _history.pop(m.chat.id, None)
    await m.answer("Ладно, забыли твой прошлый позор. Давай по новой.")


@dp.message(F.text)
async def on_text(m: Message) -> None:
    # 1. Игнорируем других ботов, чтобы избежать вечного цикла ответов друг другу
    if m.from_user and m.from_user.is_bot:
        return

    # 2. Проверяем доступ (по белому списку пользователей)
    if not allowed(m):
        return

    bot_info = await m.bot.get_me()
    bot_username = bot_info.username

    # 3. Определяем, нужно ли отвечать в группе
    is_group = m.chat.type in ("group", "supergroup")
    is_mentioned = m.text and f"@{bot_username}" in m.text
    is_reply_to_me = m.reply_to_message and m.reply_to_message.from_user.id == bot_info.id

    # В группе отвечаем только если тегнули или ответили реплаем на сообщение этого бота
    if is_group and not (is_mentioned or is_reply_to_me):
        return

    # Очищаем текст от упоминания бота, чтобы не отправлять мусор в нейросеть
    clean_text = m.text.replace(f"@{bot_username}", "").strip()
    if not clean_text:
        return

    chat_id = m.chat.id
    await m.bot.send_chat_action(chat_id, "typing")

    # Формируем историю по chat_id (для группы она будет общей)
    msgs = [*_history[chat_id], {"role": "user", "content": clean_text}]
    try:
        answer = await complete(msgs)
    except Exception as exc:
        log.warning("fail: %s", exc)
        return await m.reply("Я тут поперхнулся от твоей идеи. Попробуй еще раз через минуту.")

    _history[chat_id].append({"role": "user", "content": clean_text})
    _history[chat_id].append({"role": "assistant", "content": answer})

    # Отвечаем реплаем на конкретное сообщение
    for part in chunks(answer):
        await m.reply(part)


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
            
            # Добавляем хэндлеры для пинга от Render (чтобы не было 404 ошибок)
            async def index_handler(request):
                return web.Response(text="Бот Павла Воли запущен и готов к работе!")
                
            app.router.add_get("/", index_handler)
            app.router.add_get("/health", lambda _r: web.Response(text="ok"))
            
            SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET).register(
                app, path=WEBHOOK_PATH
            )
            setup_application(app, dp, bot=bot)
            runner = web.AppRunner(app)
            await runner.setup()
            
            # На Render порт берется из переменной окружения PORT (по умолчанию 10000 у Render)
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