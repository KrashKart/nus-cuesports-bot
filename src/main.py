from dotenv import load_dotenv
import telebot
import os
import logging
import re
import pytz
import sys

from features.polls import send_prepoll, end_poll, start_poll_announcement, callback_query, manual_end_poll
from features.confirmation import send_confirmation_message, confirm_payment_query, unconfirm_payment
from features.bump import read_paid_telegrams
from features.caching import update_with_cache

from commands.group_management import set_admin_group, set_recre_group, get_group_id
from commands.scheduler import update_schedule, send_current_schedule, create_or_update_scheduler_job
from commands.super_user import get_user_id, register_super_user, unregister_super_user, is_super_user, list_super_users
from commands.session_management import view_sessions, update_sessions, add_session, delete_session

from utils.gcs_utils import load_json_file_from_gcs, save_json_file_to_gcs
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
    return telebot.TeleBot(api_key)

def restart_bot():
    python = sys.executable
    os.execl(python, python, *sys.argv)

# Main function
def main():
    api_key = load_api_key()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Load config and messages
    config = load_data_from_gcs("config.json")
    messages = load_data_from_gcs("messages.json")
    groups = config.get("groups", {})
    schedules = config.get("schedules", {})
    super_users = config.get("super_users", [])

    ADMIN_GROUP = groups.get("ADMIN_GROUP", {}).get("id", None)
    RECRE_GROUP = groups.get("RECRE_GROUP", {}).get("id", None)

    bot = create_bot(api_key)
    send_log_message(bot, f"Bot started")

    # Persistent data
    polls = load_data_from_gcs("polls.json")
    message_ids = load_data_from_gcs("message_ids.json")
    payments = load_data_from_gcs("payments.json")
    updates = load_data_from_gcs("updates.json")

    # Initialize Flask app
    app = Flask(__name__)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if not WEBHOOK_URL:
        logger.error("No Webhook URL provided. Set the WEBHOOK_URL environment variable.")
        raise ValueError("No Webhook URL provided. Set the WEBHOOK_URL environment variable.")

    # Webhook setup
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    #################################################
    #
    #  Webhook and Schedule functions
    #
    #################################################
    @app.route('/webhook', methods=['POST'])
    def webhook():
        try:
            if request.headers.get('content-type') == 'application/json':
                json_string = request.get_data().decode('utf-8')
                update = telebot.types.Update.de_json(json_string)
                update_with_cache(bot, update, updates)
                return ''
            else:
                abort(403)
        except Exception as e:
            send_log_message(bot, e)
    
    @app.route('/prepoll', methods=['POST'])
    def scheduled_prepoll():
        try:
            send_prepoll(bot, messages, RECRE_GROUP)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Error sending prepoll announcement: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/poll', methods=['POST'])
    def scheduled_poll():
        try:
            polls.clear()
            message_ids.clear()
            payments.clear()
            start_poll_announcement(bot, messages, polls, RECRE_GROUP, message_ids, payments)
            save_data_to_gcs("polls.json", polls)
            save_data_to_gcs("message_ids.json", message_ids)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Error starting poll: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
        
    @app.route('/end', methods=['POST'])
    def handle_end_poll():
        try:
            end_poll(bot, polls, message_ids, RECRE_GROUP, ADMIN_GROUP, payments, messages)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Error ending poll: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    @app.route('/ping', methods=['POST'])
    def handle_ping():
        try:
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
        bot.send_message(message.chat.id, "Thank you for starting the bot, this bot will be sending you the confirmation messages for the training sessions.")
        if message.chat.id == ADMIN_GROUP:
            bot.send_message(message.chat.id, "Starting bot...")
            logger.info(f"Bot started by admin: {message.chat.id}")
        if message.chat.id == super_users[0]["id"]:
            bot.send_message(message.chat.id, f"Admin Group: {ADMIN_GROUP['name']}({ADMIN_GROUP['id']})")
    
    @bot.message_handler(commands=['restart'])
    def restart(message: Message):
        if message.chat.id == ADMIN_GROUP:
            save_data_to_gcs("polls.json", polls)
            save_data_to_gcs("message_ids.json", message_ids)
            save_data_to_gcs("payments.json", payments)
            save_data_to_gcs("config.json", config)
            save_data_to_gcs("messages.json", messages)
            save_data_to_gcs("updates.json", updates)

            send_log_message(bot, f"Bot restart called on {message.chat.id}")
            restart_bot()

    @bot.message_handler(commands=['restart_no_save'])
    def restart(message: Message):
        if message.chat.id == ADMIN_GROUP:
            send_log_message(bot, f"Bot restart without save called on {message.chat.id}")
            restart_bot()

    @bot.message_handler(commands=['help', 'command_list'])
    def help_command(message: Message):
        if message.chat.id == ADMIN_GROUP:
            bot.send_message(
                message.chat.id,
                text=(
                    "<blockquote><b>Command List</b></blockquote>"
                    "/restart [Restart Bot, for rescheduling the polls]\n"
                    "/update_schedule <b>&lt;prepoll/poll/end&gt; &lt;Day&gt; &lt;Time in 24h&gt;</b>\n"
                    "/current_schedule [To Check Current Schedule duh]\n"
                    "/unconfirm <b>&lt;Name/telehandle&gt;</b> (not caps sensitive)"
                ),
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
            send_prepoll(bot, messages, RECRE_GROUP)

    @bot.message_handler(commands=['poll'])
    def handle_start_poll_announcement(message: Message):
        if message.chat.id == ADMIN_GROUP:
            start_poll_announcement(bot, messages, polls, RECRE_GROUP, message_ids, payments)
    
    @bot.message_handler(commands=['end_poll'])
    def handle_end_poll(message: Message):
        if message.chat.id == ADMIN_GROUP:
            manual_end_poll(bot, polls, RECRE_GROUP, payments)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback_query(call):
        group_id = call.message.chat.id
        if re.search(r'\b\w+\b:\b\w+\b', call.data) or call.data == "poll_ended":
            callback_query(call, bot, messages, polls, message_ids, group_id)
        else:
            confirm_payment_query(call, bot, payments, group_id)
    
    #################################################
    #
    #  Recre Confirmation Functions (Actual)
    #
    #################################################
    @bot.message_handler(commands=["confirmation"])
    def handle_confirmation_message(message: Message):
        if message.chat.id == ADMIN_GROUP:
            send_confirmation_message(bot, ADMIN_GROUP, message_ids, payments, messages)

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
            send_prepoll(bot, messages, ADMIN_GROUP)
    
    @bot.message_handler(commands=['test_poll'])
    def handle_start_test_poll_announcement(message: Message):
        if message.chat.id == ADMIN_GROUP:
            start_poll_announcement(bot, messages, polls, ADMIN_GROUP, message_ids, {})
    
    @bot.message_handler(commands=['test_end_poll'])
    def handle_test_end_poll(message: Message):
        if message.chat.id == ADMIN_GROUP:
            manual_end_poll(bot, polls, ADMIN_GROUP, {})

    #################################################
    #
    #  Scheduling Management
    #
    #################################################
    @bot.message_handler(commands=['update_schedule'])
    def update_schedule_handler(message: Message):
        update_schedule(bot, message, schedules, config, ADMIN_GROUP)

    @bot.message_handler(commands=['current_schedule'])
    def send_current_schedule_handler(message: Message):
        send_current_schedule(bot, message, schedules, ADMIN_GROUP)

    
    #################################################
    #
    #  Session Management
    #
    #################################################
    @bot.message_handler(commands=['view_sessions'])
    def view_sessions_handler(message: Message):
        view_sessions(bot, message, messages, ADMIN_GROUP)

    @bot.message_handler(commands=['update_sessions'])
    def update_sessions_handler(message: Message):
        update_sessions(bot, message, messages, ADMIN_GROUP)

    @bot.message_handler(commands=['add_session'])
    def update_session_handler(message: Message):
        add_session(bot, message, messages, ADMIN_GROUP)

    @bot.message_handler(commands=['delete_session'])
    def delete_session_handler(message: Message):
        delete_session(bot, message, messages, ADMIN_GROUP)

    @bot.message_handler(commands=['get_paid'])
    def get_paid_list_handler(message: Message):
        if message.chat.id == ADMIN_GROUP:
            read_paid_telegrams(bot, message, ADMIN_GROUP)

    #################################################
    #
    #  Group Management Functions
    #
    #################################################
    @bot.message_handler(commands=['set_recre'])
    def set_recre_handler(message: Message):
        set_recre_group(bot, message, super_users, groups, config)
        bot.send_message(message.chat.id, "Remember to restart the bot to effect changes...")

    @bot.message_handler(commands=['set_admin'])
    def set_admin_group_handler(message: Message):
        set_admin_group(bot, message, super_users, groups, config)
        bot.send_message(message.chat.id, "Remember to restart the bot to effect changes...")
    
    @bot.message_handler(commands=['verify_groups'])
    def verify_group_handler(message: Message):
        if message.chat.id == ADMIN_GROUP:
            bot.send_message(chat_id=message.chat.id, text = f"Admin Group: {ADMIN_GROUP}\nRecre Group: {RECRE_GROUP}")

    @bot.message_handler(commands=['get_user_id'])
    def get_user_id_handler(message: Message):
        get_user_id(bot, message, super_users, groups, config)
    
    @bot.message_handler(commands=['get_group_id'])
    def get_group_id_handler(message: Message):
        get_group_id(bot, message)

    #################################################
    #
    #  Super User Management
    #
    #################################################
    @bot.message_handler(commands=['register_super_user'])
    def register_super_user_handler(message: Message):
        register_super_user(bot, message, super_users, groups, config)
    
    @bot.message_handler(commands=['unregister_super_user'])
    def unregister_super_user_handler(message: Message):
        unregister_super_user(bot, message, super_users, groups, config)

    @bot.message_handler(commands=['is_super_user'])
    def is_super_user_handler(message: Message):
        is_super_user(bot, message, super_users, groups, config)

    @bot.message_handler(commands=['list_super_users'])
    def list_super_users_handler(message: Message):
        list_super_users(bot, message, super_users, groups, config)

    # Schedule tasks
    job_name = 'prepoll_job'
    create_or_update_scheduler_job("prepoll", schedules["prepoll"]["day"], schedules["prepoll"]["time"], job_name)

    job_name = 'poll_job'
    create_or_update_scheduler_job("poll", schedules["poll"]["day"], schedules["poll"]["time"], job_name)

    job_name = 'end_job'
    create_or_update_scheduler_job("end", schedules["poll"]["end"]["day"], schedules["poll"]["end"]["time"], job_name)

    job_name = 'ping_job'
    create_or_update_scheduler_job("ping", schedules["ping"]["day"], schedules["ping"]["time"], job_name)

    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

    logger.info("Bot started.")

if __name__ == "__main__":
    main()
