import logging
from utils.tg_logging import send_log_message
from utils.config_interface import get_admin_id, get_super_users_id

from telebot import TeleBot
from telebot.types import Message
from typing import Callable

logger = logging.getLogger(__name__)

def _admin_group_perms(function: Callable[..., None]) -> Callable[..., None]:
    def new_function(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
        if message.chat.id == get_admin_id(config):
            function(bot, message, messages, config)
        else:
            bot.send_message(message.chat.id, f"You cannot call this command in {message.chat.title}")
    
    return new_function

def _super_user_perms(function: Callable[..., None]) -> Callable[..., None]:
    def new_function(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
        if message.from_user.id not in get_super_users_id(config):
            function(bot, message, messages, config)
        else:
            bot.send_message(message.chat.id, f"You ({message.from_user.username}) are not allowed to use this")
    
    return new_function

def _log(function: Callable[..., None]) -> Callable[..., None]:
    def new_function(bot: TeleBot, *args) -> None:
        try:
            function(bot, *args)
        except Exception as e:
            send_log_message(bot, f"Error in {function.__name__}: {e}")
            logger.error(f"Error in {function.__name__}: {e}")
    
    return new_function