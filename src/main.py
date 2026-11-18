"""Entry point: loads the settings, sets up the bot, and returns the web app gunicorn serves.

Where things live:
- handlers/command_menu.py: every command and the function that handles it
- handlers/routes.py: the /webhook endpoint and the scheduled-job endpoints
- state/: everything saved in the bucket
See "Code Layout" in docs/development.md for the rest.
"""
import logging
import os

import telebot
from dotenv import load_dotenv

from handlers.command_menu import register_commands
from handlers.routes import create_app
from handlers.schedules import sync_scheduler_jobs
from state import poll_state
from state.cloud_storage import load_json_file_from_gcs
from state.config import CONFIG_FILE, get_schedule
from state.messages import MESSAGES_FILE
from utils.tg_logging import send_log_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


def load_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        logger.error(f"{name} is not set. Set the {name} environment variable.")
        raise ValueError(f"{name} is not set. Set the {name} environment variable.")
    return value


def main():
    api_key = load_required_env("TELEGRAM_API_KEY")
    webhook_url = load_required_env("WEBHOOK_URL")
    webhook_secret = load_required_env("WEBHOOK_SECRET")
    load_required_env("SCHEDULER_SECRET")  # read by handlers/schedules.py; checked here so a missing one stops startup

    # No fallback to empty settings if these can't be read: running with an empty config
    # and later saving it (e.g. on /register_super_user) would overwrite the real one.
    config = load_json_file_from_gcs(CONFIG_FILE)
    messages = load_json_file_from_gcs(MESSAGES_FILE)
    # The keep-alive ping was removed (min_instances: 1 keeps the bot running instead).
    # Dropping it here also removes it from config.json the next time config is saved.
    get_schedule(config).pop("ping", None)

    # threaded=False: handlers run inside the webhook request, under state_lock.
    # A threaded bot would hand them to a pool and return before they've run.
    bot = telebot.TeleBot(api_key, threaded=False)

    # Votes, payments, started users and the last update ID (see state/poll_state.py)
    poll_state.load()
    poll_state.start(bot)

    register_commands(bot, messages, config)

    # Telegram sends webhook_secret with every update (checked in handlers/routes.py).
    # max_connections=1: one update at a time and in order, which handlers/dedupe.py relies on.
    bot.set_webhook(url=webhook_url, secret_token=webhook_secret, max_connections=1)
    sync_scheduler_jobs(config)

    send_log_message(bot, "Bot started", config)
    logger.info("Bot started.")
    return create_app(bot, messages, config, webhook_secret)


# Module-level so gunicorn can import `app` (see entrypoint in app.yaml).
# Running this file directly uses Flask's development server instead.
app = main()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
