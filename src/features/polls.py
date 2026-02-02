import telebot
import logging
import pytz
from datetime import datetime
from features.confirmation import send_confirmation_message
from utils.gcs_utils import save_json_file_to_gcs, load_json_file_from_gcs
from utils.tg_logging import send_log_message
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from telebot import TeleBot

logger = logging.getLogger(__name__)
singapore_tz = pytz.timezone("Asia/Singapore")

def has_started_bot(bot: TeleBot, user_id: str | int, group_id: str | int) -> bool:
    try:
        numeric_user_id = int(user_id.split('-')[-1])
        logger.info(f"Checking if user {user_id} has started bot in group {group_id}")
        message = bot.send_message(numeric_user_id, ".", disable_notification=True)
        bot.delete_message(numeric_user_id, message.message_id)
        return True
    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"Error checking user status for user {user_id} in group {group_id}: {e}")
        return False

def clear_polls(polls: dict) -> None:
    polls.clear()

def send_prepoll(bot: TeleBot, messages: dict, group_id: str | int) -> None:
    options = messages["Poll"]["Options"]
    slots = zip(options.keys(), [option["Capacity"] for option in options.values()])
    formatted_slots = "\n    ".join([f"- <b>{slot}</b> ({capacity} pax)" for slot, capacity in slots])
    payment_director = messages["Payment Director"]["Name"]
    payment_director_handle = messages["Payment Director"]["Handle"]
    bot_director = messages["Bot Director"]["Name"]
    bot_director_handle = messages["Bot Director"]["Handle"]
    
    prepoll_message = (messages["Prepoll Announcement"].replace("POLL_OPTIONS", formatted_slots)
                                                        .replace("PAYMENT_HANDLE", payment_director_handle)
                                                        .replace("PAYMENT_DIRECTOR", payment_director)
                                                        .replace("BOT_DIRECTOR", bot_director)
                                                        .replace("BOT_HANDLE", bot_director_handle))
    
    bot.send_message(group_id, prepoll_message, parse_mode='HTML')
    logger.info(f"Prepoll announcement sent to: {group_id}")
    send_log_message(bot, f"Prepoll started in group {group_id}")

def end_poll(bot: TeleBot, polls: dict, message_ids: dict, chat_id: str | int, admin_id: str | int, payments: dict, messages: dict) -> None:
    poll_id = next(iter(polls))
    message_id = polls[poll_id]["message_id"]
    poll_message = load_json_file_from_gcs("poll_message.json")
    try:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Poll ended", callback_data="poll_ended"))
        try:
            bot.edit_message_text(chat_id=chat_id,
                                  message_id=message_id,
                                  text=poll_message,
                                  reply_markup=markup,
                                  parse_mode='HTML')
            del polls[poll_id]
            save_json_file_to_gcs("polls.json", polls)
            logger.info(f"Poll ended in group {chat_id} with id {message_id}")
            send_log_message(bot, f"Poll ended in group {chat_id} with id {message_id}")
        except Exception as e:
            print(e)

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

def start_poll_announcement(bot: TeleBot, messages: dict, polls: dict, group_id: str | int, message_ids: dict, payments: dict) -> None:
    question = messages["Poll"]["Question"]
    body = messages["Poll"]["Body"]
    options = messages["Poll"]["Options"]
    bot_director = messages["Bot Director"]["Name"]
    bot_director_handle = messages["Bot Director"]["Handle"]

    body = body.replace("BOT_DIRECTOR", bot_director).replace("BOT_DIR_HANDLE", bot_director_handle)

    poll_id = f"{group_id}_{int(datetime.now().timestamp())}"  # Create a unique poll_id
    polls[poll_id] = {option: [] for option in options}

    markup = InlineKeyboardMarkup()

    poll_message = f"<blockquote><b>{question}</b></blockquote>"
    poll_message += body

    for k, v in options.items():
        if v["Active"]:
            message_ids[k] = []
            markup.add(InlineKeyboardButton(k, callback_data=f"{poll_id}:{k}"))
            poll_message += f"<blockquote><b>{k}</b> (👤 0/{v['Capacity']})</blockquote>"
            poll_message += "No votes yet\n\n"

    sent_message = bot.send_message(group_id, poll_message, reply_markup=markup, parse_mode='HTML')
    polls[poll_id]["message_id"] = sent_message.message_id
    send_log_message(bot, f"Poll started in group {group_id} with id {sent_message.message_id}")
    logger.info(f"Poll started in group: {group_id}")

    # Save poll data to Google Cloud Storage
    save_json_file_to_gcs("polls.json", polls)
    save_json_file_to_gcs("message_ids.json", message_ids)
    save_json_file_to_gcs("payments.json", payments)
    save_json_file_to_gcs("poll_message.json", poll_message)

def callback_query(call: CallbackQuery, bot: TeleBot, messages: Message, polls: dict, message_ids: dict, group_id: str | int) -> None:
    if call.data == "poll_ended":
        bot.answer_callback_query(call.id, "The poll has ended. Please wait for next week's poll to be released.", show_alert=True)
        return

    poll_id, option = call.data.split(":")
    user = call.from_user
    user_id = f"{user.full_name}-@{user.username}-{user.id}"
    user_id_lst = str([user.full_name, user.username, user.id])
    user_name = f"{user.full_name} (@{user.username})" if user.username else user.full_name
    user_name = user_name.replace("<", "").replace(">", "")

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

    question = messages["Poll"]["Question"]
    body = messages["Poll"]["Body"]
    bot_director = messages["Bot Director"]["Name"]
    bot_director_handle = messages["Bot Director"]["Handle"]
    options = messages["Poll"]["Options"]

    body = body.replace("BOT_DIRECTOR", bot_director).replace("BOT_DIR_HANDLE", bot_director_handle)
    
    poll_message = f"<blockquote><b>{question}</b></blockquote>\n\n"
    poll_message += body

    for sess_name, names in polls[poll_id].items():
        if sess_name == "message_id":
            continue
        count = len(names)
        poll_message += f"<blockquote><b>{sess_name}</b> (👤 {count}/{options[sess_name]['Capacity']})</blockquote>"
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
