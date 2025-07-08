from dotenv import load_dotenv
import telebot
import os
import logging
import re
import pytz
import sys

from features.polls import end_poll, start_poll_announcement, callback_query, manual_end_poll
from features.confirmation import send_confirmation_message, confirm_payment_query, unconfirm_payment

from commands.group_management import set_admin_group, set_recre_group, set_spam_test_group
from commands.scheduler import update_schedule, send_current_schedule, create_or_update_scheduler_job
from commands.super_user import get_user_id, get_group_id, register_super_user, unregister_super_user, is_super_user, list_super_users

from utils.gcs_utils import load_json_file_from_gcs, save_json_file_to_gcs
from flask import Flask, jsonify, request, abort
from telebot.types import Message

# try:
from utils.tg_logging import send_log_message
# except ImportError:
#     sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils"))
#     from tg_logging import send_log_message

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
    SPAM_TEST_GROUP = groups.get("SPAM_TEST_GROUP", {}).get("id", None)

    assert ADMIN_GROUP != None, "ADMIN_GROUP is None"
    assert RECRE_GROUP != None, "RECRE_GROUP is None"
    assert SPAM_TEST_GROUP != None, "SPAM_TEST_GROUP is None"

    bot = create_bot(api_key)

    # Persistent data
    polls = load_data_from_gcs("polls.json")
    message_ids = load_data_from_gcs("message_ids.json")
    payments = load_data_from_gcs("payments.json")

    # Initialize Flask app
    app = Flask(__name__)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if not WEBHOOK_URL:
        logger.error("No Webhook URL provided. Set the WEBHOOK_URL environment variable.")
        raise ValueError("No Webhook URL provided. Set the WEBHOOK_URL environment variable.")

    # Webhook setup
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    @app.route('/webhook', methods=['POST'])
    def webhook():
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            abort(403)
    
    @app.route('/prepoll', methods=['POST'])
    def scheduled_prepoll():
        try:
            logger.info(messages["Prepoll Announcement"])
            formatted_slots = " /n    ".join([f"- <b>{slot}</b>" for slot in messages["Poll"]["Options"]])
            prepoll_message = messages["Prepoll Announcement"].replace("POLL_OPTIONS", formatted_slots)
            bot.send_message(RECRE_GROUP, prepoll_message, parse_mode='HTML')
            logger.info(f"Prepoll announcement sent to: {RECRE_GROUP}")
            send_log_message(bot, f"Prepoll started in group {RECRE_GROUP}")
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
            start_poll_announcement(bot, messages, polls, RECRE_GROUP, ADMIN_GROUP, message_ids, schedules["poll"]["end"], payments)
            save_data_to_gcs("polls.json", polls)
            save_data_to_gcs("message_ids.json", message_ids)
            logger.info(f"Poll started in group {RECRE_GROUP}")
            send_log_message(bot, f"Poll started in group {RECRE_GROUP}")
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
        
    @bot.message_handler(commands=['start'])
    def start_command(message: Message):
        bot.send_message(message.chat.id, "Thank you for starting the bot, this bot will be sending you the confirmation messages for the training sessions.")
        if message.chat.id in [ADMIN_GROUP, SPAM_TEST_GROUP]:
            bot.send_message(message.chat.id, "Starting bot...")
            logger.info(f"Bot started by admin: {message.chat.id}")
        if message.chat.id == super_users[0]["id"]:
            bot.send_message(message.chat.id, f"Admin Group: {ADMIN_GROUP['name']}({ADMIN_GROUP['id']})")

    @bot.message_handler(commands=['help', 'command_list'])
    def help_command(message: Message):
        if message.chat.id in [ADMIN_GROUP, SPAM_TEST_GROUP]:
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

    @bot.message_handler(commands=['prepoll'])
    def start_prepoll_announcement(message: Message):
        if message.chat.id == ADMIN_GROUP:
            formatted_slots = " /n    ".join([f"- <b>{slot}</b>" for slot in messages["Poll"]["Options"]])
            prepoll_message = messages["Prepoll Announcement"].replace("POLL_OPTIONS", formatted_slots)
            bot.send_message(RECRE_GROUP, prepoll_message, parse_mode='HTML')
            logger.info(f"Prepoll announcement sent to: {RECRE_GROUP}")

    @bot.message_handler(commands=['poll'])
    def handle_start_poll_announcement(message: Message):
        start_poll_announcement(bot, messages, polls, groups, message_ids, schedules["poll"]["end"])

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback_query(call):
        group_id = call.message.chat.id
        if re.search(r'\b\w+\b:\b\w+\b', call.data) or call.data == "poll_ended":
            callback_query(call, bot, messages, polls, message_ids, group_id)
        else:
            confirm_payment_query(call, bot, payments, group_id)

    @bot.message_handler(commands=["confirmation"])
    def handle_confirmation_message(message: Message):
        if message.chat.id == ADMIN_GROUP:
            send_confirmation_message(bot, ADMIN_GROUP, message_ids, payments, messages)

    @bot.message_handler(commands=["unconfirm"])
    def handle_unconfirm_message(message: Message):
        if message.chat.id == ADMIN_GROUP:
            unconfirm_payment(bot, message, payments, ADMIN_GROUP)

    @bot.message_handler(commands=['update_schedule'])
    def update_schedule_handler(message: Message):
        update_schedule(bot, message, schedules, config, ADMIN_GROUP)

    @bot.message_handler(commands=['update_session'])
    def update_session(message: Message):
        if message.chat.id != ADMIN_GROUP:
            return
        try:
            command_params = message.text.split()
            all_options = messages.get("Poll", {}).get("all_options", [])
            all_option_format = "\n".join([f"{_i + 1}: {_option}" for _i, _option in enumerate(all_options)])
            if len(command_params) == 1:
                bot.send_message(message.chat.id,
                                 text = f"usage: /update_session <Option 1> <Option 2> <Option 3> (Numeric ascending Order)\n{all_option_format}")
            else:
                new_option = [all_options[int(_i)-1] for _i in command_params[1:]]
                messages["Poll"]["Options"] = new_option
                save_json_file_to_gcs("messages.json", messages)
                new_option_format = '\n'.join(new_option)
                bot.send_message(message.chat.id, f"Session updated:\n{new_option_format}")
        except Exception as e:
            bot.send_message(message.chat.id, f"Error updating sessions: {e}")
            logger.error(f"Error updating schedule: {e}")

    @bot.message_handler(commands=['current_schedule'])
    def send_current_schedule_handler(message: Message):
        send_current_schedule(bot, message, schedules, ADMIN_GROUP)

    @bot.message_handler(commands=['set_recre'])
    def set_recre_group_handler(message: Message):
        result = set_recre_group(bot, message, super_users, groups, config)
        if result:
            nonlocal RECRE_GROUP
            RECRE_GROUP = groups["RECRE_GROUP"]["id"]

    @bot.message_handler(commands=['set_admin'])
    def set_admin_group_handler(message: Message):
        result = set_admin_group(bot, message, super_users, groups, config)
        if result:
            nonlocal ADMIN_GROUP
            ADMIN_GROUP = groups["ADMIN_GROUP"]["id"]

    @bot.message_handler(commands=['set_spam_test'])
    def set_spam_test_group_handler(message: Message):
        result = set_spam_test_group(bot, message, super_users, groups, config)
        if result:
            nonlocal SPAM_TEST_GROUP
            SPAM_TEST_GROUP = groups["SPAM_TEST_GROUP"]["id"]

    @bot.message_handler(commands=['restart'])
    def restart(message: Message):
        if message.chat.id == ADMIN_GROUP:
            bot.send_message(message.chat.id, "Restarting the bot...")
            restart_bot()

    @bot.message_handler(commands=['end_poll'])
    def end_poll_handler(message: Message):
        user_id = message.from_user.id
        if any(user["id"] == user_id for user in super_users):
            manual_end_poll(bot, polls, message_ids, RECRE_GROUP, ADMIN_GROUP, payments, messages)

    @bot.message_handler(commands=['get_user_id'])
    def get_user_id_handler(message: Message):
        get_user_id(bot, message, super_users, groups, config)
    
    @bot.message_handler(commands=['get_group_id'])
    def get_group_id_handler(message: Message):
        get_group_id(bot, message, super_users, groups, config)

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
    create_or_update_scheduler_job("prepoll", schedules["prepoll"]["day"], schedules["prepoll"]["time"], job_name, schedules)

    job_name = 'poll_job'
    create_or_update_scheduler_job("poll", schedules["poll"]["day"], schedules["poll"]["time"], job_name, schedules)

    job_name = 'end_job'
    create_or_update_scheduler_job("end", schedules["poll"]["end"]["day"], schedules["poll"]["end"]["time"], job_name, schedules)

    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

    logger.info("Bot started.")

if __name__ == "__main__":
    main()
