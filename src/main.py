from dotenv import load_dotenv
import telebot
import os
import logging
import re
import pytz
import sys
import hmac
import signal
from functools import wraps

from polling.poll import send_prepoll, end_poll, start_poll_announcement, callback_query, remember_started_user
from polling.confirmation import send_confirmation_message, confirm_payment_query, unconfirm_payment
from state import poll_state

from handlers.dedupe import update_with_cache
from handlers.command_menu import __register_commands, CMD_LIST
from handlers.groups import set_admin_group, set_recre_group, get_group_id, verify_group
from handlers.schedules import update_schedule, send_current_schedule, create_or_update_scheduler_job, SCHEDULER_HEADER, SCHEDULER_SECRET
from handlers.super_users import get_user_id, register_super_user, unregister_super_user, is_super_user, list_super_users
from handlers.poll_settings import view_sessions, update_sessions, add_session, delete_session, set_capacity, set_payment_director, set_bot_director, set_location, set_cost
from handlers.broadcast import send_message_admin, send_message_recre

from state.cloud_storage import load_json_file_from_gcs, save_json_file_to_gcs
from flask import Flask, jsonify, request, abort
from telebot.types import Message

from utils.tg_logging import send_log_message

singapore_tz = pytz.timezone('Asia/Singapore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()

# Load API Key
def load_api_key():
    api_key = os.getenv("TELEGRAM_API_KEY")
    if not api_key:
        logger.error("No API key provided. Set the TELEGRAM_API_KEY environment variable.")
        raise ValueError("No API key provided. Set the TELEGRAM_API_KEY environment variable.")
    return api_key

# Load and Save Persistent Data from Google Cloud Storage
def load_data_from_gcs(file_name):
    try:
        data = load_json_file_from_gcs(file_name) or {}
        logger.info(f"Data loaded successfully from GCS: {file_name}.")
        return data
    except Exception as e:
        logger.error(f"Error loading data from GCS: {file_name}, {e}")
        return {}

def save_data_to_gcs(file_name, data):
    try:
        save_json_file_to_gcs(file_name, data)
        logger.info(f"Data saved successfully to GCS: {file_name}.")
    except Exception as e:
        logger.error(f"Error saving data to GCS: {file_name}, {e}")

# Bot initialization
def create_bot(api_key):
    # threaded=False: handlers run inside the webhook request, so state_lock below
    # covers them. A threaded bot would hand work to a pool and return immediately.
    return telebot.TeleBot(api_key, threaded=False)

# Every change to poll/payment/config state happens while holding this lock
# (webhook updates and scheduled routes). Shared with the background saver in poll_state.
state_lock = poll_state.state_lock

def restart_bot():
    if "gunicorn" in os.path.basename(sys.argv[0]):
        # Under gunicorn (production): stop this worker. Gunicorn lets the current request
        # finish, the worker exits (saving poll state unless saving was disabled), and
        # gunicorn starts a fresh worker, which reloads everything from storage.
        os.kill(os.getpid(), signal.SIGTERM)
    else:
        # Run directly (python src/main.py): replace this process with a new one
        python = sys.executable
        os.execl(python, python, *sys.argv)

def load_required_env(name):
    value = os.getenv(name)
    if not value:
        logger.error(f"{name} is not set. Set the {name} environment variable.")
        raise ValueError(f"{name} is not set. Set the {name} environment variable.")
    return value

def secret_matches(provided, expected):
    # compare_digest takes the same time whether or not the strings match,
    # so the secret can't be guessed by timing responses
    return provided is not None and hmac.compare_digest(provided.encode(), expected.encode())

# Main function
def main():
    api_key = load_api_key()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Load config and messages
    config = load_data_from_gcs("config.json")
    messages = load_data_from_gcs("messages.json")
    groups = config.get("groups", {})
    schedules = config.get("schedules", {})
    # The keep-alive ping was removed (min_instances: 1 keeps the bot running instead).
    # Dropping it here also removes it from config.json the next time config is saved.
    schedules.pop("ping", None)
    super_users = config.get("super_users", [])

    ADMIN_GROUP = groups.get("ADMIN_GROUP", {}).get("id", None)
    RECRE_GROUP = groups.get("RECRE_GROUP", {}).get("id", None)

    bot = create_bot(api_key)
    send_log_message(bot, f"Bot started", config)
    __register_commands(bot, ADMIN_GROUP)

    # Poll state (votes, payments, started users, last update ID) lives in one file,
    # poll_state.json, saved in the background. See state/poll_state.py.
    poll_state.load()
    poll_state.start(bot)
    polls = poll_state.polls
    message_ids = poll_state.message_ids
    payments = poll_state.payments
    updates = poll_state.updates
    started_users = poll_state.started_users  # a set: O(1) "can the bot DM this user?" lookups

    # Initialize Flask app
    app = Flask(__name__)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if not WEBHOOK_URL:
        logger.error("No Webhook URL provided. Set the WEBHOOK_URL environment variable.")
        raise ValueError("No Webhook URL provided. Set the WEBHOOK_URL environment variable.")

    # Secrets that prove a request came from Telegram / Cloud Scheduler
    WEBHOOK_SECRET = load_required_env("WEBHOOK_SECRET")
    if not SCHEDULER_SECRET:
        load_required_env("SCHEDULER_SECRET")  # raises with a clear message

    # Webhook setup: Telegram will send WEBHOOK_SECRET in a header on every update
    bot.remove_webhook()
    # max_connections=1: Telegram sends one update at a time, in order. With the default (40
    # in parallel) updates could arrive out of order, and update_with_cache would drop any
    # whose ID is lower than one already processed, e.g. a vote.
    bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET, max_connections=1)

    def scheduler_only(route):
        @wraps(route)  # keeps each route's own name; Flask needs unique endpoint names
        def wrapper(*args, **kwargs):
            if not secret_matches(request.headers.get(SCHEDULER_HEADER), SCHEDULER_SECRET):
                abort(403)
            with state_lock:
                return route(*args, **kwargs)
        return wrapper

    #################################################
    #
    #  Webhook and Scheduling functions
    #
    #################################################
    @app.route('/webhook', methods=['POST'])
    def webhook():
        # Checked outside the try: abort() works by raising, and the except below would swallow it
        if not secret_matches(request.headers.get('X-Telegram-Bot-Api-Secret-Token'), WEBHOOK_SECRET):
            abort(403)
        if request.headers.get('content-type') != 'application/json':
            abort(403)
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            with state_lock:
                update_with_cache(bot, update, updates)
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            send_log_message(bot, f"Webhook error: {e}", config)
        return ''

    @app.route('/prepoll', methods=['POST'])
    @scheduler_only
    def scheduled_prepoll():
        try:
            send_prepoll(bot, messages, RECRE_GROUP, config)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Error sending prepoll announcement: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/poll', methods=['POST'])
    @scheduler_only
    def scheduled_poll():
        try:
            polls.clear()
            message_ids.clear()
            payments.clear()
            start_poll_announcement(bot, messages, polls, RECRE_GROUP, message_ids, payments, config)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Error starting poll: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
        
    @app.route('/end', methods=['POST'])
    @scheduler_only
    def handle_end_poll():
        try:
            end_poll(bot, polls, message_ids, RECRE_GROUP, ADMIN_GROUP, payments, messages, config)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Error ending poll: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    #################################################
    #
    #  Bot Operations
    #
    ################################################# 
    @bot.message_handler(commands=['start'])
    def start_command(message: Message):
        # /start in a private chat means the bot can now DM this user
        if message.chat.type == "private":
            remember_started_user(started_users, message.from_user.id)
        bot.send_message(message.chat.id, "Thank you for starting the bot, this bot will be sending you the confirmation messages for the training sessions.")
        if message.chat.id == ADMIN_GROUP:
            bot.send_message(message.chat.id, "Starting bot...")
            logger.info(f"Bot started by admin: {message.chat.id}")
        if super_users and message.chat.id == super_users[0]["id"]:
            admin_group = groups.get("ADMIN_GROUP", {})
            bot.send_message(message.chat.id, f"Admin Group: {admin_group.get('name')}({admin_group.get('id')})")
    
    @bot.message_handler(commands=['restart'])
    def restart(message: Message):
        if message.chat.id == ADMIN_GROUP:
            poll_state.flush(force=True)
            save_data_to_gcs("config.json", config)
            save_data_to_gcs("messages.json", messages)

            send_log_message(bot, f"Bot restart called on {message.chat.id}", config)
            restart_bot()

    @bot.message_handler(commands=['restart_no_save'])
    def restart_no_save(message: Message):
        if message.chat.id == ADMIN_GROUP:
            # Stop all saving first, so hand-edited files in the bucket are what gets reloaded
            poll_state.disable_saving()
            send_log_message(bot, f"Bot restart without save called on {message.chat.id}", config)
            restart_bot()

    @bot.message_handler(commands=['help', 'command_list'])
    def help_command(message: Message):
        if message.chat.id == ADMIN_GROUP:
            bot.send_message(
                message.chat.id,
                text="You can refer to the commands list <a href='https://krashkart.github.io/nus-cuesports-bot/commands'>here</a>!",
                parse_mode='HTML'
            )

    #################################################
    #
    #  Recre poll functions (sends to RECRE_GROUP)
    #
    ################################################# 
    @bot.message_handler(commands=['prepoll'])
    def start_prepoll_announcement(message: Message):
        if message.chat.id == ADMIN_GROUP:
            send_prepoll(bot, messages, RECRE_GROUP, config)

    @bot.message_handler(commands=['poll'])
    def handle_start_poll_announcement(message: Message):
        if message.chat.id == ADMIN_GROUP:
            polls.clear()
            message_ids.clear()
            payments.clear()
            start_poll_announcement(bot, messages, polls, RECRE_GROUP, message_ids, payments, config)
    
    @bot.message_handler(commands=['end_poll'])
    def handle_end_poll(message: Message):
        if message.chat.id == ADMIN_GROUP:
            end_poll(bot, polls, message_ids, RECRE_GROUP, ADMIN_GROUP, payments, messages, config)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback_query(call):
        group_id = call.message.chat.id
        if re.search(r'\b\w+\b:\b\w+\b', call.data) or call.data == "poll_ended":
            callback_query(call, bot, messages, polls, message_ids, group_id, config, started_users)
        else:
            confirm_payment_query(call, bot, payments, group_id, messages)
    
    #################################################
    #
    #  Recre Confirmation Functions (Actual)
    #
    #################################################
    @bot.message_handler(commands=["confirmation"])
    def handle_confirmation_message(message: Message):
        if message.chat.id == ADMIN_GROUP:
            send_confirmation_message(bot, ADMIN_GROUP, message_ids, payments, messages, config)

    @bot.message_handler(commands=["unconfirm"])
    def handle_unconfirm_message(message: Message):
        if message.chat.id == ADMIN_GROUP:
            unconfirm_payment(bot, message, payments, ADMIN_GROUP)
    
    #################################################
    #
    #  Test poll functions (sends to ADMIN_GROUP)
    #
    #################################################
    @bot.message_handler(commands=['test_prepoll'])
    def handle_start_test_prepoll_announcement(message: Message):
        if message.chat.id == ADMIN_GROUP:
            send_prepoll(bot, messages, ADMIN_GROUP, config)
    
    @bot.message_handler(commands=['test_poll'])
    def handle_start_test_poll_announcement(message: Message):
        if message.chat.id == ADMIN_GROUP:
            polls.clear()
            message_ids.clear()
            payments.clear()
            start_poll_announcement(bot, messages, polls, ADMIN_GROUP, message_ids, payments, config)
    
    @bot.message_handler(commands=['test_end_poll'])
    def handle_test_end_poll(message: Message):
        if message.chat.id == ADMIN_GROUP:
            end_poll(bot, polls, message_ids, ADMIN_GROUP, ADMIN_GROUP, payments, messages, config)

    #################################################
    #
    #  Scheduling Management
    #
    #################################################
    @bot.message_handler(commands=['current_schedule'])
    def send_current_schedule_handler(message: Message):
        send_current_schedule(bot, message, messages, config)
        
    @bot.message_handler(commands=['update_schedule'])
    def update_schedule_handler(message: Message):
        update_schedule(bot, message, messages, config)

    #################################################
    #
    #  Session Management
    #
    #################################################
    @bot.message_handler(commands=['view_sessions'])
    def view_sessions_handler(message: Message):
        view_sessions(bot, message, messages, config)

    @bot.message_handler(commands=['update_sessions'])
    def update_sessions_handler(message: Message):
        update_sessions(bot, message, messages, config)

    @bot.message_handler(commands=['add_session'])
    def add_session_handler(message: Message):
        add_session(bot, message, messages, config)

    @bot.message_handler(commands=['delete_session'])
    def delete_session_handler(message: Message):
        delete_session(bot, message, messages, config)
    
    @bot.message_handler(commands=['set_capacity'])
    def set_capacity_handler(message: Message):
        if message.chat.id == ADMIN_GROUP:
            set_capacity(bot, message, messages, config)

    @bot.message_handler(commands=['set_payment_director'])
    def set_payment_director_handler(message: Message):
        if message.chat.id == ADMIN_GROUP:
            set_payment_director(bot, message, messages, config)

    @bot.message_handler(commands=['set_bot_director'])
    def set_bot_director_handler(message: Message):
        if message.chat.id == ADMIN_GROUP:
            set_bot_director(bot, message, messages, config)

    @bot.message_handler(commands=['set_location'])
    def set_location_handler(message: Message):
        if message.chat.id == ADMIN_GROUP:
            set_location(bot, message, messages, config)

    @bot.message_handler(commands=['set_cost'])
    def set_cost_handler(message: Message):
        if message.chat.id == ADMIN_GROUP:
            set_cost(bot, message, messages, config)


    #################################################
    #
    #  Group Management Functions
    #
    #################################################
    @bot.message_handler(commands=['set_recre'])
    def set_recre_handler(message: Message):
        set_recre_group(bot, message, messages, config)
        bot.send_message(message.chat.id, "Remember to restart the bot to effect changes...")

    @bot.message_handler(commands=['set_admin'])
    def set_admin_group_handler(message: Message):
        set_admin_group(bot, message, messages, config)
        bot.send_message(message.chat.id, "Remember to restart the bot to effect changes...")
    
    @bot.message_handler(commands=['verify_groups'])
    def verify_group_handler(message: Message):
        verify_group(bot, message, messages, config)
    
    @bot.message_handler(commands=['get_group_id'])
    def get_group_id_handler(message: Message):
        get_group_id(bot, message, messages, config)

    #################################################
    #
    #  Super User Management
    #
    #################################################
    @bot.message_handler(commands=['register_super_user'])
    def register_super_user_handler(message: Message):
        register_super_user(bot, message, messages, config)
    
    @bot.message_handler(commands=['unregister_super_user'])
    def unregister_super_user_handler(message: Message):
        unregister_super_user(bot, message, messages, config)

    @bot.message_handler(commands=['is_super_user'])
    def is_super_user_handler(message: Message):
        is_super_user(bot, message, messages, config)

    @bot.message_handler(commands=['list_super_users'])
    def list_super_users_handler(message: Message):
        list_super_users(bot, message, messages, config)

    @bot.message_handler(commands=['get_user_id'])
    def get_user_id_handler(message: Message):
        get_user_id(bot, message, messages, config)

    #################################################
    #
    #  Miscellaneous
    #
    #################################################
    @bot.message_handler(commands=['send_admin'])
    def send_message_admin_handler(message: Message):
        send_message_admin(bot, message, messages, config)
    
    @bot.message_handler(commands=['send_recre'])
    def send_message_recre_handler(message: Message):
        send_message_recre(bot, message, messages, config)
        
    #################################################
    #
    #  Task Schedules
    #
    #################################################
    job_name = 'prepoll_job'
    create_or_update_scheduler_job("prepoll", schedules["prepoll"]["day"], schedules["prepoll"]["time"], job_name)

    job_name = 'poll_job'
    create_or_update_scheduler_job("poll", schedules["poll"]["day"], schedules["poll"]["time"], job_name)

    job_name = 'end_job'
    create_or_update_scheduler_job("end", schedules["end"]["day"], schedules["end"]["time"], job_name)

    logger.info("Bot started.")
    return app

# Module-level so gunicorn can import `app` (see entrypoint in app.yaml).
# Running this file directly uses Flask's development server instead.
app = main()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
