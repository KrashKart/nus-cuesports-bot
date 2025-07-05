from telebot import types
import telebot
import logging
import schedule
import pytz
import sys
import os
from datetime import datetime, timedelta
from features.confirmation import send_confirmation_message
from utils.gcs_utils import save_json_file_to_gcs, load_json_file_from_gcs

# For some reason mine dont work
try:
    from utils.tg_logging import get_logger
except:
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utils"))
    from tg_logging import send_log_message

logger = logging.getLogger(__name__)
poll_message = ""
singapore_tz = pytz.timezone("Asia/Singapore")

def has_started_bot(bot, user_id, group_id):
    try:
        numeric_user_id = int(user_id.split('-')[-1])
        logger.info(f"Checking if user {user_id} has started bot in group {group_id}")
        message = bot.send_message(numeric_user_id, ".", disable_notification=True)
        bot.delete_message(numeric_user_id, message.message_id)
        return True
    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"Error checking user status for user {user_id} in group {group_id}: {e}")
        return False

def end_poll(bot, polls, message_ids, chat_id, admin_id, payments, messages):
    poll_id = next(iter(polls))
    message_id = polls[poll_id]["message_id"]
    poll_message = load_json_file_from_gcs("poll_message.json")
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Poll ended", callback_data="poll_ended"))
        try:
            bot.edit_message_text(chat_id=chat_id,
                                  message_id=message_id,
                                  text=poll_message,
                                  reply_markup=markup,
                                  parse_mode='HTML')
        except Exception as e:
            print(e)

        logger.info(f"Successfully ended the poll in group {chat_id}")

        send_confirmation_message(bot, admin_id, message_ids, payments, messages)

    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"Error ending poll for group {chat_id}: {e}")
        send_log_message(bot, f"Error ending poll for group {chat_id}: {e}")

        if "message is not modified" in str(e):
            logger.info("The message was not modified.")
        elif "message to edit not found" in str(e):
            logger.info("The message to edit was not found.")
        elif "bot was kicked from the group chat" in str(e):
            logger.info("The bot was kicked from the group chat.")
        else:
            logger.error(f"Unhandled error: {e}")

def manual_end_poll(bot, polls, message_ids, chat_id, admin_id, payments, messages):
    logger.info(f"Payments before manual end poll: {payments}")
    poll_id = next(iter(polls))
    message_id = polls[poll_id]["message_id"]
    poll_message = load_json_file_from_gcs("poll_message.json")
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Poll ended" , callback_data="poll_ended"))
        try:
            bot.edit_message_text(chat_id=chat_id,
                                  message_id=message_id,
                                  text=poll_message,
                                  reply_markup=markup,
                                  parse_mode='HTML')
        except Exception as e:
            print(e)

        logger.info(f"Successfully ended the poll in group {chat_id}")

    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"Error ending poll for group {chat_id}: {e}")
        send_log_message(bot, f"Error ending poll for group {chat_id}: {e}")

        if "message is not modified" in str(e):
            logger.info("The message was not modified.")
        elif "message to edit not found" in str(e):
            logger.info("The message to edit was not found.")
        elif "bot was kicked from the group chat" in str(e):
            logger.info("The bot was kicked from the group chat.")
        else:
            logger.error(f"Unhandled error: {e}")

def start_poll_announcement(bot, messages, polls, group_id, admin_id, message_ids, end_schedule, payments):
    global poll_message

    question = messages["Poll"]["Question"]
    options = messages["Poll"]["Options"]
    poll_id = f"{group_id}_{int(datetime.now().timestamp())}"  # Create a unique poll_id
    polls[poll_id] = {option: [] for option in options}
    for option in options:
        message_ids[option] = []

    markup = types.InlineKeyboardMarkup()
    for option in options:
        markup.add(types.InlineKeyboardButton(option, callback_data=f"{poll_id}:{option}"))

    poll_message = f"<blockquote><b>{question}</b></blockquote>"
    poll_message += "Hi everyone! Here’s the poll for next week’s training sessions. Do note that they are at Aspire Recreational Centre (HarbourFront Centre)! There is a maximum of 36 pax for the session. Each session is $8. Please make sure you have a confirmation message from the TDs before coming!\n\nClick here to start the bot: https://t.me/nuscuesportsbot\n\n"
    for opt in options:
        poll_message += f"<blockquote><b>{opt}</b> (👤 0)</blockquote>"
        poll_message += "No votes yet\n\n"

    sent_message = bot.send_message(group_id, poll_message, reply_markup=markup, parse_mode='HTML')
    polls[poll_id]["message_id"] = sent_message.message_id
    logger.info(f"Poll started in group: {group_id}")

    # Save poll data to Google Cloud Storage
    save_json_file_to_gcs("polls.json", polls)
    save_json_file_to_gcs("message_ids.json", message_ids)
    save_json_file_to_gcs("payments.json", payments)
    save_json_file_to_gcs("poll_message.json", poll_message)

def callback_query(call, bot, messages, polls, message_ids, group_id):
    if call.data == "poll_ended":
        bot.answer_callback_query(call.id, "The poll has ended. Please wait for next week's poll to be released.", show_alert=True)
        return
    poll_message = load_json_file_from_gcs("poll_message.json")

    poll_id, option = call.data.split(":")
    user = call.from_user
    user_id = f"{user.full_name}-@{user.username}-{user.id}"
    user_id_lst = str([user.full_name, user.username, user.id])
    user_name = f"{user.full_name} (@{user.username})" if user.username else user.full_name

    if not has_started_bot(bot, user_id, group_id):
        bot.answer_callback_query(call.id, "Please start the bot to participate in the poll. Click the link provided in the poll message to start.", show_alert=True)
        return

    # Toggle user vote
    if user_name in polls[poll_id][option]:
        logger.info(f"Removing {user_name} from {option}")
        polls[poll_id][option].remove(user_name)
        message_ids[option].remove(user_id_lst)
    else:
        logger.info(f"Adding {user_name} to {option}")
        polls[poll_id][option].append(user_name)
        message_ids[option].append(user_id_lst)

    poll_message = f"<blockquote><b>{messages['Poll']['Question']}</b></blockquote>\n\n"
    poll_message += "Hi everyone! Here’s the poll for next week’s training sessions. Do note that they are from 7PM-9PM at Aspire Recreational Centre (HarbourFront Centre)! There is a maximum of 36 pax for the session. Each session is $8. Please make sure you have a confirmation message from the TDs before coming!\n\nClick here to start the bot: https://t.me/nuscuesportsbot\n\n"
    for opt, names in polls[poll_id].items():
        if opt == "message_id":
            continue
        count = len(names)
        poll_message += f"<blockquote><b>{opt}</b> (👤 {count})</blockquote>"
        if names:
            poll_message += "\n".join(names) + "\n"
        else:
            poll_message += "No votes yet\n"
        poll_message += "\n"

    save_json_file_to_gcs("polls.json", polls)
    save_json_file_to_gcs("message_ids.json", message_ids)
    save_json_file_to_gcs("poll_message.json", poll_message)

    try:
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=poll_message,
                              reply_markup=call.message.reply_markup,
                              parse_mode='HTML')
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            logger.info("No changes to update.")
        else:
            logger.error(f"Error updating message: {e}")

    bot.answer_callback_query(call.id)
