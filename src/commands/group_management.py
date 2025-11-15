import logging
from utils.tg_logging import send_log_message
from utils.gcs_utils import save_json_file_to_gcs
from utils.config_interface import get_groups, get_admin_id, get_recre_id
from utils.permissions import _admin_group_perms, _super_user_perms, _log

from telebot import TeleBot
from telebot.types import Message

logger = logging.getLogger(__name__)

@_log
@_super_user_perms
def set_admin_group(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    new_admin_group_id = message.chat.id
    new_admin_group_name = message.chat.title if message.chat.type in ["group", "supergroup"] else "Private Chat"
    groups = get_groups(config)
    groups["id"], groups["name"] = new_admin_group_id, new_admin_group_name
    save_json_file_to_gcs("config.json", config)
    send_log_message(bot, f"Admin group updated successfully to {new_admin_group_name} : {new_admin_group_id}.")
    logger.info(f"Admin group updated successfully to {new_admin_group_name} : {new_admin_group_id}.")

@_log
@_super_user_perms
def set_recre_group(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    new_recre_group_id = message.chat.id
    new_recre_group_name = message.chat.title if message.chat.type in ["group", "supergroup"] else "Private Chat"
    groups = get_groups(config)
    groups["id"], groups["name"] = new_recre_group_id, new_recre_group_name
    save_json_file_to_gcs("config.json", config)
    send_log_message(bot, f"Recreational group updated successfully to {new_recre_group_name} : {new_recre_group_id}.")
    logger.info(f"Recreational group updated successfully to {new_recre_group_name} : {new_recre_group_id}.")

@_log
@_super_user_perms
def get_group_id(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    bot.send_message(message.chat.id, f"The group id is {message.chat.id}")

@_log
@_super_user_perms
@_admin_group_perms
def verify_group(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    adm_grp, rcr_grp = get_admin_id(config), get_recre_id(config)
    bot.send_message(chat_id=message.chat.id, text = f"Admin Group: {adm_grp}\nRecre Group: {rcr_grp}")