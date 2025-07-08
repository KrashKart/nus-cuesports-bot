import logging
from utils.tg_logging import send_log_message
from utils.gcs_utils import save_json_file_to_gcs

from telebot import TeleBot
from telebot.types import Message
from typing import Callable

logger = logging.getLogger(__name__)

def _set_group_wrapper(set_function: Callable[..., None]) -> Callable[..., bool]:
    def new_set_function(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> bool:
        user_id = message.from_user.id
        if any(user["id"] == user_id for user in super_users):
            try:
                set_function(bot, message, super_users, groups, config)
                return True
            except Exception as e:
                send_log_message(bot, f"Error in {set_function.__name__}: {e}")
                logger.error(f"Error in {set_function.__name__}: {e}")
            finally:
                return False
        else:
            bot.send_message(message.chat.id, "You are not authorized to use this command.")
            return False
    
    return new_set_function

@_set_group_wrapper
def set_admin_group(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
    new_admin_group_id = message.chat.id
    new_admin_group_name = message.chat.title if message.chat.type in ["group", "supergroup"] else "Private Chat"
    groups["ADMIN_GROUP"] = {"id": new_admin_group_id, "name": new_admin_group_name}
    save_json_file_to_gcs("config.json", config)
    send_log_message(bot, f"Admin group updated successfully to {new_admin_group_name} : {new_admin_group_id}.")
    logger.info(f"Admin group updated successfully to {new_admin_group_name} : {new_admin_group_id}.")

@_set_group_wrapper
def set_recre_group(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
    new_recre_group_id = message.chat.id
    new_recre_group_name = message.chat.title if message.chat.type in ["group", "supergroup"] else "Private Chat"
    groups["RECRE_GROUP"] = {"id": new_recre_group_id, "name": new_recre_group_name}
    save_json_file_to_gcs("config.json", config)
    send_log_message(bot, f"Recreational group updated successfully to {new_recre_group_name} : {new_recre_group_id}.")
    logger.info(f"Recreational group updated successfully to {new_recre_group_name} : {new_recre_group_id}.")

@_set_group_wrapper
def set_spam_test_group(bot: TeleBot, message: Message, super_users: list, groups: dict, config: dict) -> None:
    new_spam_test_group_id = message.chat.id
    new_spam_test_group_name = message.chat.title if message.chat.type in ["group", "supergroup"] else "Private Chat"
    groups["SPAM_TEST_GROUP"] = {"id": new_spam_test_group_id, "name": new_spam_test_group_name}
    save_json_file_to_gcs("config.json", config)
    send_log_message(bot, f"Spam Text group updated successfully to {new_spam_test_group_name} : {new_spam_test_group_id}.")
    logger.info(f"Spam Text group updated successfully to {new_spam_test_group_name} : {new_spam_test_group_id}.")