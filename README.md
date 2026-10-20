# ai_office

A Telegram "AI office": every bot is a separate AI persona you can bounce startup ideas off.

![demo](docs/demo.gif)
<!-- TODO: add a short screen recording of a chat as docs/demo.gif -->

## Features

- `ilon.py` — a first-principles engineer: strips an idea down to fundamentals and helps optimise it
- `volya.py` — a stand-up-comic critic that stress-tests ideas with blunt humour
- Any LLM through OpenRouter, chosen with `MODEL`
- Per-user conversation memory (last N exchanges); `/reset` clears it, `/whoami` shows your Telegram ID
- Access limited to a list of Telegram user IDs
- Long polling for local runs, webhooks for hosting (e.g. Render)

## Tech stack

Python · aiogram 3 · httpx · OpenRouter API · python-dotenv

## Quick start

```bash
git clone https://github.com/a1tvv/ai_office.git && cd ai_office
pip install -r requirements.txt
cp .env.example .env    # fill in the values
python ilon.py          # or: python volya.py
```

## Configuration

Settings are read from `.env` (see [`.env.example`](.env.example)):

| Variable | Purpose |
|---|---|
| `ilon_token`, `volya_token` | Telegram bot tokens from @BotFather, one per bot |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `ALLOWED_USER_IDS` | Comma-separated Telegram user IDs allowed to chat with the bots |
| `MODEL` | OpenRouter model ID; each bot has its own default |
| `HISTORY_LIMIT` | How many recent exchanges each bot remembers (default `12`) |
| `USE_WEBHOOK`, `WEBHOOK_BASE`, `WEBHOOK_SECRET`, `PORT` | Webhook mode for hosting: set `USE_WEBHOOK=1` and the public base URL |

## License

[MIT](LICENSE)
