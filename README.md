**English** | [Русский](README.ru.md)

# ai_office

A Telegram "AI office": each bot is a different AI character. You can talk to the bots about your startup ideas.

<!-- TODO: add a short screen recording of a chat as docs/demo.gif -->

## Features

- `ilon.py` — an engineer who thinks from first principles: breaks an idea down to the basics and helps make it better
- `volya.py` — a critic in the style of a stand-up comedian: tests ideas with sharp, direct jokes
- Any LLM through OpenRouter — you choose it with `MODEL`
- Each user has their own chat memory (the last N questions and answers); `/reset` clears it, `/whoami` shows your Telegram ID
- Only Telegram users from a list can use the bots
- Long polling to run on your computer, webhooks for hosting (for example, Render)

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

The settings come from `.env` (see [`.env.example`](.env.example)):

| Variable | What it does |
|---|---|
| `ilon_token`, `volya_token` | Telegram bot tokens from @BotFather, one for each bot |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `ALLOWED_USER_IDS` | Telegram user IDs that can talk to the bots, separated by commas |
| `MODEL` | OpenRouter model ID; each bot has its own default model |
| `HISTORY_LIMIT` | How many recent questions and answers each bot remembers (default `12`) |
| `USE_WEBHOOK`, `WEBHOOK_BASE`, `WEBHOOK_SECRET`, `PORT` | Webhook mode for hosting: set `USE_WEBHOOK=1` and the public base URL |

## License

[MIT](LICENSE)
