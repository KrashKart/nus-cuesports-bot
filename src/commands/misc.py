import logging
from utils.tg_logging import send_log_message

from telebot import TeleBot
from telebot.types import Message

logger = logging.getLogger(__name__)

def send_message_admin(bot: TeleBot, message: Message, groups: dict) -> None:
    try:
        if message.chat.id == groups["ADMIN_GROUP"]["id"]:
            text = ' '.join(message.html_text.split()[1:])
            bot.send_message(groups["ADMIN_GROUP"]["id"], text, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, f"You are not allowed to use this in {message.chat.title}")
    except Exception as e:
        send_log_message(bot, f"Error in {function.__name__}: {e}")
        logger.error(f"Error in {function.__name__}: {e}")

def send_message_recre(bot: TeleBot, message: Message, groups: dict) -> None:
    try:
        if message.chat.id == groups["ADMIN_GROUP"]["id"]:
            text = ' '.join(message.html_text.split()[1:])
            bot.send_message(groups["RECRE_GROUP"]["id"], text, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, f"You are not allowed to use this in {message.chat.title}")
    except Exception as e:
        send_log_message(bot, f"Error in {function.__name__}: {e}")
        logger.error(f"Error in {function.__name__}: {e}")