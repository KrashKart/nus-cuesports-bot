"""Every bot command in one table: its name, its description in Telegram's command menu, and its handler.

register_commands() connects each handler to the bot and sets the command menu (the list
shown when you type "/") in the admin group, so the menu and the handlers can't drift apart.

To add a command: write a handler that takes (bot, message, messages, config), usually with
the permission decorators from handlers/permissions.py, and add one line to COMMANDS.
"""
import logging
from typing import Callable, NamedTuple

from telebot import TeleBot
from telebot.types import BotCommand, BotCommandScopeChat

from handlers import bot_control, poll_commands
from handlers.broadcast import send_message_admin, send_message_recre
from handlers.groups import set_admin_group, set_recre_group, get_group_id, verify_group
from handlers.poll_settings import (view_sessions, update_sessions, add_session, delete_session, set_capacity,
                                    set_payment_director, set_bot_director, set_location, set_cost)
from handlers.schedules import send_current_schedule, update_schedule
from handlers.super_users import get_user_id, register_super_user, unregister_super_user, is_super_user, list_super_users
from state.config import get_admin_id

logger = logging.getLogger(__name__)


class Command(NamedTuple):
    name: str
    description: str     # shown in Telegram's command menu
    handler: Callable    # handler(bot, message, messages, config)
    aliases: tuple = ()  # other names that run the same handler; not shown in the menu


def _set_admin_and_move_menu(bot: TeleBot, message, messages: dict, config: dict) -> None:
    # The command menu is only shown in the admin group, so it moves with it
    set_admin_group(bot, message, messages, config)
    set_command_menu(bot, get_admin_id(config))


COMMANDS = [
    # Bot
    Command("start", "Start the bot", bot_control.start_command),
    Command("restart", "Restart the bot", bot_control.restart),
    Command("restart_no_save", "Restart the bot without saving states", bot_control.restart_no_save),
    Command("help", "Displays link to documentation", bot_control.help_command, aliases=("command_list",)),
    # Polls and confirmation
    Command("prepoll", "Trigger prepoll message in recre chat", poll_commands.prepoll_command),
    Command("poll", "Trigger poll in recre chat", poll_commands.poll_command),
    Command("end_poll", "End poll in recre chat", poll_commands.end_poll_command),
    Command("confirmation", "Trigger payment confirmation message", poll_commands.confirmation_command),
    Command("unconfirm", "Unconfirm payment for user", poll_commands.unconfirm_command),
    Command("test_prepoll", "Trigger prepoll message in admin chat", poll_commands.test_prepoll_command),
    Command("test_poll", "Trigger poll in admin chat", poll_commands.test_poll_command),
    Command("test_end_poll", "End poll in admin chat", poll_commands.test_end_poll_command),
    # Schedules
    Command("current_schedule", "View current schedule", send_current_schedule),
    Command("update_schedule", "Update current schedule", update_schedule),
    # Poll settings
    Command("view_sessions", "View status of all sessions", view_sessions),
    Command("update_sessions", "Update active sessions", update_sessions),
    Command("add_session", "Add available session", add_session),
    Command("delete_session", "Delete available session", delete_session),
    Command("set_capacity", "Set capacity for a session", set_capacity),
    Command("set_payment_director", "Set payment director", set_payment_director),
    Command("set_bot_director", "Set bot director", set_bot_director),
    Command("set_location", "Set location for sessions", set_location),
    Command("set_cost", "Set cost for all sessions", set_cost),
    # Groups
    Command("verify_groups", "Get admin and recre group id", verify_group),
    Command("set_admin", "Set admin group", _set_admin_and_move_menu),
    Command("set_recre", "Set recre group", set_recre_group),
    Command("get_group_id", "Get group id of current group", get_group_id),
    # Super users
    Command("list_super_users", "List all super users and their ids", list_super_users),
    Command("is_super_user", "Check if you are a super user", is_super_user),
    Command("register_super_user", "Register yourself under an alias", register_super_user),
    Command("unregister_super_user", "Unregister a super user", unregister_super_user),
    Command("get_user_id", "Get your user id", get_user_id),
    # Broadcast
    Command("send_admin", "Send a message to admin group as the bot", send_message_admin),
    Command("send_recre", "Send a message to recre group as the bot", send_message_recre),
]

CMD_LIST = [BotCommand(command.name, command.description) for command in COMMANDS]


def register_commands(bot: TeleBot, messages: dict, config: dict) -> None:
    """Connect every command and button handler to the bot, and set the command menu."""
    for command in COMMANDS:
        bot.register_message_handler(_bind(command.handler, bot, messages, config),
                                     commands=[command.name, *command.aliases])
    bot.register_callback_query_handler(lambda call: poll_commands.handle_button(bot, call, messages, config),
                                        func=lambda call: True)
    set_command_menu(bot, get_admin_id(config))


def set_command_menu(bot: TeleBot, admin_group_id) -> None:
    """Show the command menu in the admin group. A failure here shouldn't stop the bot."""
    if admin_group_id is None:
        logger.warning("No admin group set; skipping the command menu")
        return
    try:
        bot.set_my_commands(CMD_LIST, BotCommandScopeChat(admin_group_id))
    except Exception as e:
        logger.warning(f"Could not set the command menu in {admin_group_id}: {e}")


def _bind(handler, bot: TeleBot, messages: dict, config: dict):
    """Turn handler(bot, message, messages, config) into the handler(message) telebot calls."""
    return lambda message: handler(bot, message, messages, config)
