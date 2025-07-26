import logging
from utils.tg_logging import send_log_message
from utils.gcs_utils import save_json_file_to_gcs

from telebot import TeleBot
from telebot.types import Message
from typing import Callable

logger = logging.getLogger(__name__)

def _super_user_wrapper(function: Callable[..., None]) -> Callable[..., None]:
    def new_function(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
        try:
            if message.chat.id == groups["ADMIN_GROUP"]["id"]:
                function(bot, message, super_users, groups, config)
            else:
                bot.send_message(message.chat.id, f"You are not allowed to use this in {message.chat.title}")
        except Exception as e:
            send_log_message(bot, f"Error in {function.__name__}: {e}")
            logger.error(f"Error in {function.__name__}: {e}")
    
    return new_function

@_super_user_wrapper
def get_user_id(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
    bot.send_message(message.chat.id, f"Your user id is {message.from_user.id}")

@_super_user_wrapper
def get_group_id(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
    bot.send_message(message.chat.id, f"The group id is {message.chat.id}")

@_super_user_wrapper
def register_super_user(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
    user_id = message.from_user.id
    params = message.text.strip().split()
    if user_id in [user["id"] for user in super_users]:
        bot.send_message(message.chat.id, "You are already a super user!")
    elif len(params) == 1:
        bot.send_message(message.chat.id, "Enter a name to register you under!\nusage: /register_super_user <name>")
    else:
        nickname = " ".join(params[1:])
        super_users.append({"id": user_id, "name": nickname})
        config["super_users"] = super_users
        save_json_file_to_gcs("config.json", config)
        send_log_message(bot, f"{nickname}: {user_id} registered as super user")
        bot.send_message(message.chat.id, f"{nickname} has been registered as a super user")

@_super_user_wrapper
def unregister_super_user(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
        user_id = message.from_user.id
        to_remove = list(filter(lambda x: x["id"] == user_id, super_users))
        if not to_remove:
            bot.send_message(message.chat.id, f"You are not a super user")
        else:
            to_remove = to_remove[0]
            super_users.remove(to_remove)
            config["super_users"] = super_users
            save_json_file_to_gcs("config.json", config)
            send_log_message(bot, f"{to_remove['name']}: {to_remove['id']} deregistered as super user")
            bot.send_message(message.chat.id, f"{to_remove['name']} has been deregistered as super user")

@_super_user_wrapper
def is_super_user(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
    user_id = message.from_user.id
    super_user_ids = [user["id"] for user in super_users]
    bot.send_message(message.chat.id, f"You are{' not' if user_id not in super_user_ids else ''} a super user.")

@_super_user_wrapper
def list_super_users(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
    super_user_str = "\n".join([f"• {user['name']}: {user['id']}" for user in super_users]).strip()
    bot.send_message(message.chat.id, f"Super users are:\n{super_user_str if super_user_str else '• No super users found!'}")
