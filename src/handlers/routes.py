"""The web endpoints: /webhook for Telegram, and /prepoll, /poll and /end for Cloud Scheduler."""
import hmac
import logging
from functools import wraps

import telebot
from flask import Flask, abort, jsonify, request

from handlers.dedupe import update_with_cache
from handlers.schedules import SCHEDULER_HEADER, SCHEDULER_SECRET
from polling.poll import send_prepoll, open_poll, close_poll
from state import poll_state
from state.config import get_recre_id
from state.poll_state import LIVE
from utils.tg_logging import send_log_message

logger = logging.getLogger(__name__)


def secret_matches(provided, expected) -> bool:
    # compare_digest takes the same time whether or not the strings match,
    # so the secret can't be guessed by timing responses
    return provided is not None and hmac.compare_digest(provided.encode(), expected.encode())


def create_app(bot: telebot.TeleBot, messages: dict, config: dict, webhook_secret: str) -> Flask:
    app = Flask(__name__)

    def scheduler_only(route):
        """Reject requests without Cloud Scheduler's secret header; run the rest under state_lock."""
        @wraps(route)  # keeps each route's own name; Flask needs unique endpoint names
        def wrapper(*args, **kwargs):
            if not secret_matches(request.headers.get(SCHEDULER_HEADER), SCHEDULER_SECRET):
                abort(403)
            with poll_state.state_lock:
                return route(*args, **kwargs)
        return wrapper

    def run_job(name, job):
        try:
            job()
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Scheduled {name} failed: {e}")
            send_log_message(bot, f"Scheduled {name} failed: {e}", config)
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/webhook', methods=['POST'])
    def webhook():
        # Checked outside the try: abort() works by raising, and the except below would swallow it
        if not secret_matches(request.headers.get('X-Telegram-Bot-Api-Secret-Token'), webhook_secret):
            abort(403)
        if request.headers.get('content-type') != 'application/json':
            abort(403)
        try:
            update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
            with poll_state.state_lock:
                update_with_cache(bot, update, poll_state.updates)
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            send_log_message(bot, f"Webhook error: {e}", config)
        return ''

    @app.route('/prepoll', methods=['POST'])
    @scheduler_only
    def scheduled_prepoll():
        return run_job("prepoll", lambda: send_prepoll(bot, messages, get_recre_id(config), config))

    @app.route('/poll', methods=['POST'])
    @scheduler_only
    def scheduled_poll():
        return run_job("poll", lambda: open_poll(bot, messages, config, get_recre_id(config), LIVE))

    @app.route('/end', methods=['POST'])
    @scheduler_only
    def scheduled_end():
        return run_job("end", lambda: close_poll(bot, messages, config, get_recre_id(config), LIVE))

    return app
