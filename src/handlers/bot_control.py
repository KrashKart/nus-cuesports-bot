"""Commands that control the bot itself: /start, /restart, /restart_no_save, /help."""
import logging
import os
import signal
import sys

from telebot import TeleBot
from telebot.types import Message

from handlers.permissions import _admin_group_perms, _log
from polling.poll import remember_started_user
from state import poll_state
from state.config import get_admin_id, get_groups, get_super_users, save_config
from state.messages import save_messages
from utils.tg_logging import send_log_message

logger = logging.getLogger(__name__)

COMMANDS_PAGE = "https://krashkart.github.io/nus-cuesports-bot/commands"


def start_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    # /start in a private chat means the bot can now DM this user
    if message.chat.type == "private":
        remember_started_user(poll_state.started_users, message.from_user.id)
    bot.send_message(message.chat.id, "Thank you for starting the bot, this bot will be sending you the confirmation messages for the training sessions.")
    if message.chat.id == get_admin_id(config):
        bot.send_message(message.chat.id, "Starting bot...")
        logger.info(f"Bot started by admin: {message.chat.id}")
    super_users = get_super_users(config)
    if super_users and message.chat.id == super_users[0]["id"]:
        admin_group = get_groups(config).get("ADMIN_GROUP", {})
        bot.send_message(message.chat.id, f"Admin Group: {admin_group.get('name')}({admin_group.get('id')})")


@_admin_group_perms
@_log
def restart(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    poll_state.flush(force=True)
    save_config(config)
    save_messages(messages)
    send_log_message(bot, f"Bot restart called on {message.chat.id}", config)
    restart_bot()


@_admin_group_perms
@_log
def restart_no_save(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    # Stop all saving first, so hand-edited files in the bucket are what gets reloaded
    poll_state.disable_saving()
    send_log_message(bot, f"Bot restart without save called on {message.chat.id}", config)
    restart_bot()


@_admin_group_perms
@_log
def help_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    bot.send_message(message.chat.id,
                     text=f"You can refer to the commands list <a href='{COMMANDS_PAGE}'>here</a>!",
                     parse_mode='HTML')


def restart_bot() -> None:
    if "gunicorn" in os.path.basename(sys.argv[0]):
        # Under gunicorn (production): stop this worker. Gunicorn lets the current request
        # finish, the worker exits (saving poll state unless saving was disabled), and
        # gunicorn starts a fresh worker, which reloads everything from storage.
        os.kill(os.getpid(), signal.SIGTERM)
    else:
        # Run directly (python src/main.py): replace this process with a new one
        python = sys.executable
        os.execl(python, python, *sys.argv)
