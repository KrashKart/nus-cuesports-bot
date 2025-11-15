import logging
from utils.config_interface import get_admin_id, get_recre_id
from utils.permissions import _admin_group_perms, _log

from telebot import TeleBot
from telebot.types import Message

logger = logging.getLogger(__name__)

@_log
def _send_message_to_group(bot: TeleBot, message: Message, group_id) -> None:
    text = ' '.join(message.html_text.split(' ')[1:])
    bot.send_message(group_id, text, parse_mode="HTML")

@_log
@_admin_group_perms
def send_message_admin(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    _send_message_to_group(bot, message, get_admin_id(config))

@_log
@_admin_group_perms
def send_message_recre(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    _send_message_to_group(bot, message, get_recre_id(config))
