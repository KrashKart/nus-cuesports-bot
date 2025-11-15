import logging
from utils.tg_logging import send_log_message
from utils.gcs_utils import save_json_file_to_gcs
from utils.config_interface import get_super_users, get_super_users_id
from utils.permissions import _admin_group_perms, _log

from telebot import TeleBot
from telebot.types import Message

logger = logging.getLogger(__name__)

@_log
@_admin_group_perms
def get_user_id(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    bot.send_message(message.chat.id, f"Your user id is {message.from_user.id}")

@_log
@_admin_group_perms
def register_super_user(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    user_id = message.from_user.id
    params = message.text.strip().split()
    if user_id in get_super_users_id(config):
        bot.send_message(message.chat.id, "You are already a super user!")
    elif len(params) == 1:
        bot.send_message(message.chat.id, "Enter a name to register you under!\nusage: /register_super_user <name>")
    else:
        super_users = get_super_users(config)
        nickname = " ".join(params[1:])
        super_users.append({"id": user_id, "name": nickname})
        save_json_file_to_gcs("config.json", config)
        send_log_message(bot, f"{nickname}: {user_id} registered as super user")
        bot.send_message(message.chat.id, f"{nickname} has been registered as a super user")

@_log
@_admin_group_perms
def unregister_super_user(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
        user_id = message.from_user.id
        to_remove = list(filter(lambda x: x["id"] == user_id, get_super_users(config)))
        if not to_remove:
            bot.send_message(message.chat.id, f"You are not a super user")
        else:
            super_users = get_super_users(config)
            to_remove = to_remove[0]
            super_users.remove(to_remove)
            save_json_file_to_gcs("config.json", config)
            send_log_message(bot, f"{to_remove['name']}: {to_remove['id']} deregistered as super user")
            bot.send_message(message.chat.id, f"{to_remove['name']} has been deregistered as super user")

@_log
@_admin_group_perms
def is_super_user(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f"You are{' not' if user_id not in get_super_users_id(config) else ''} a super user.")

@_log
@_admin_group_perms
def list_super_users(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    super_user_str = "\n".join([f"• {user['name']}: {user['id']}" for user in get_super_users(config)]).strip()
    bot.send_message(message.chat.id, f"Super users are:\n{super_user_str if super_user_str else '• No super users found!'}")
