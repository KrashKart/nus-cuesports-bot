import logging
from state.config import get_admin_id, get_recre_id
from handlers.permissions import _admin_group_perms, _log

from telebot import TeleBot
from telebot.types import Message

logger = logging.getLogger(__name__)

def _send_message_to_group(bot: TeleBot, message: Message, group_id) -> None:
    # Everything after the command. Split on any whitespace, not just spaces: with
    # split(' '), a message starting on a new line after the command was lost.
    parts = message.html_text.split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""
    if not text.strip():
        bot.send_message(message.chat.id, "Usage: /send_admin <message> or /send_recre <message>")
        return
    bot.send_message(group_id, text, parse_mode="HTML")

@_admin_group_perms
@_log
def send_message_admin(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    _send_message_to_group(bot, message, get_admin_id(config))

@_admin_group_perms
@_log
def send_message_recre(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    _send_message_to_group(bot, message, get_recre_id(config))
