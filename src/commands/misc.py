import logging
from utils.tg_logging import send_log_message

from telebot import TeleBot
from telebot.types import Message

logger = logging.getLogger(__name__)

def _send_message_to_group(bot: TeleBot, message: Message, group: int) -> None:
    try:
        text = ' '.join(message.html_text.split(' ')[1:])
        bot.send_message(group, text, parse_mode="HTML")
    except Exception as e:
        send_log_message(bot, f"Error in {function.__name__}: {e}")
        logger.error(f"Error in {function.__name__}: {e}")


def send_message_admin(bot: TeleBot, message: Message, groups: dict) -> None:
    try:
        if message.chat.id == groups["ADMIN_GROUP"]["id"]:
            _send_message_to_group(bot, message, groups["ADMIN_GROUP"]["id"])
        else:
            bot.send_message(message.chat.id, f"You are not allowed to use this in {message.chat.title}")
    except Exception as e:
        send_log_message(bot, f"Error in {function.__name__}: {e}")
        logger.error(f"Error in {function.__name__}: {e}")

def send_message_recre(bot: TeleBot, message: Message, groups: dict) -> None:
    try:
        if message.chat.id == groups["ADMIN_GROUP"]["id"]:
            _send_message_to_group(bot, message, groups["RECRE_GROUP"]["id"])
        else:
            bot.send_message(message.chat.id, f"You are not allowed to use this in {message.chat.title}")
    except Exception as e:
        send_log_message(bot, f"Error in {function.__name__}: {e}")
        logger.error(f"Error in {function.__name__}: {e}")