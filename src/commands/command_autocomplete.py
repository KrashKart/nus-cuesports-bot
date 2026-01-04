from telebot import TeleBot
from telebot.types import BotCommand, BotCommandScopeChat

CMD_LIST: list[BotCommand] = [
    BotCommand("start", "Start the bot"),
    BotCommand("restart", "Restart the bot"),
    BotCommand("restart_no_save", "Restart the bot without saving states"),
    BotCommand("help", "Displays link to documentation"),
    BotCommand("prepoll", "Trigger prepoll message in recre chat"),
    BotCommand("poll", "Trigger poll in recrechat"),
    BotCommand("end_poll", "End poll in recre chat"),
    BotCommand("confirmation", "Trigger payment confirmation message"),
    BotCommand("unconfirm", "Unconfirm payment for user"),
    BotCommand("test_prepoll", "Trigger prepoll message in admin chat"),
    BotCommand("test_poll", "Trigger poll in admin chat"),
    BotCommand("test_end_poll", "End poll in admin chat"),
    BotCommand("current_schedule", "View current schedule"),
    BotCommand("update_schedule", "Update current schedule"),
    BotCommand("update_ping", "Update scheduled ping duration"),
    BotCommand("view_sessions", "View status of all sessions"),
    BotCommand("update_sessions", "Update active sessions"),
    BotCommand("add_session", "Add available session"),
    BotCommand("delete_session", "Delete available session"),
    BotCommand("set_capacity", "Set capacity for a session"),
    BotCommand("get_paid", "Get list of users that paid (WIP)"),
    BotCommand("verify_groups", "Get admin and recre group id"),
    BotCommand("set_admin", "Set admin group"),
    BotCommand("set_recre", "Set recre group"),
    BotCommand("get_group_id", "Get group id of current group"),
    BotCommand("list_super_users", "List all super users and their ids"),
    BotCommand("is_super_user", "Check if you are a super user"),
    BotCommand("register_super_user", "Register yourself under an alias"),
    BotCommand("unregister_super_user", "Unregister a super user"),
    BotCommand("get_user_id", "Get your user id"),
    BotCommand("send_admin", "Send a message to admin group as the bot"),
    BotCommand("send_recre", "Send a message to recre group as the bot"),
]

def __register_commands(bot: TeleBot, admin_group_id: int) -> bool:
    command_scope = BotCommandScopeChat(admin_group_id)
    return bot.set_my_commands(CMD_LIST, command_scope)