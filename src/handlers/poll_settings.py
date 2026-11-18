import logging
from state.messages import (save_messages, get_sessions, replace_sessions, get_cost, change_cost,
                            change_payment_director, change_bot_director, change_location)
from handlers.permissions import _admin_group_perms, _log
from utils.datetime_utils import is_valid_day, is_valid_time, convert_to_ampm, DAYS

from telebot import TeleBot
from telebot.types import Message

logger = logging.getLogger(__name__)
DEFAULT_MAX_CAPACITY = 36

def _parse_number(text: str):
    """The whole number in text, or None if it isn't one.

    Plain int() raised on input like "abc", so the command failed without replying.
    """
    return int(text) if text.isdigit() else None

@_admin_group_perms
@_log
def view_sessions(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.split()
    if len(command_params) != 1:
        bot.send_message(message.chat.id, text = f"usage: /view_sessions")
    else:
        options = get_sessions(messages)

        other_options_format = "\n".join([f"{_i + 1}: {k} (Cap {v['Capacity']})" for _i, (k, v) in enumerate(options.items()) if not v["Active"]])
        active_options_format = "\n".join([f"{_i + 1}: {k} (Cap {v['Capacity']})" for _i, (k, v) in enumerate(options.items()) if v["Active"]])
        bot.send_message(message.chat.id, f"Active Sessions:\n{active_options_format}\n\nAvailable Sessions:\n{other_options_format}")

@_admin_group_perms
@_log
def add_session(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.strip().split()

    if len(command_params) != 4:
        bot.send_message(message.chat.id,
                            text = f"usage: /add_session <day> <start time> <end time>\nAll times are in HH:MM format.\ne.g. /add_session Monday 19:00 21:00")
    else:
        _, day, start_time, end_time = command_params
        if not is_valid_day(day):
            bot.send_message(message.chat.id, "Invalid day. Use 'sunday', 'monday', etc (Lower/Upper case both accepted).")
            return
        elif not is_valid_time(start_time):
            bot.send_message(message.chat.id, "Invalid start time. Time should be in format 'HH:MM'.")
            return
        elif not is_valid_time(end_time):
            bot.send_message(message.chat.id, "Invalid end time. Time should be in format 'HH:MM'.")
            return
        
        new_all_option = f"{day.capitalize()} {convert_to_ampm(start_time)}-{convert_to_ampm(end_time)}"
        options = get_sessions(messages)
        if new_all_option in options:
            bot.send_message(message.chat.id, "Session already exists!")
            return

        options[new_all_option] = {"Capacity": DEFAULT_MAX_CAPACITY, "Active": 0}
        replace_sessions(messages, dict(sorted(options.items(),
                                               key=lambda x: int(DAYS[x[0].strip().split()[0].lower()]))))

        save_messages(messages)
        bot.send_message(message.chat.id, f"Session added:\n{new_all_option}")

@_admin_group_perms
@_log
def delete_session(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.strip().split()
    options = get_sessions(messages)
    if len(command_params) != 2:
        bot.send_message(message.chat.id, text = f"usage: /delete_session <number>")
    else:
        _, idx = command_params
        idx = _parse_number(idx)
        if idx is not None and 0 < idx <= len(options):
            sess_name = list(options.keys())[idx - 1]
            del options[sess_name]

            save_messages(messages)
            bot.send_message(message.chat.id, f"Session deleted:\n{sess_name}")
        else:
            bot.send_message(message.chat.id, f"Enter a valid option number to delete! (From 1 to {len(options)})")

@_admin_group_perms
@_log
def update_sessions(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.split()
    options = get_sessions(messages)
    if len(command_params) == 1 or len(command_params) > 4:
        all_options_format = "\n".join([f"{_i + 1}: {_option}" for _i, _option in enumerate(options)])
        bot.send_message(message.chat.id,
                            text = f"usage: /update_sessions <Option 1> <Option 2> <Option 3> (Enter the option numbers in ascending order)\n{all_options_format}")
    else:
        idxs = [_parse_number(i) for i in command_params[1:]]
        if any(i is None or not 0 < i <= len(options) for i in idxs):
            bot.send_message(message.chat.id, f"Enter a valid option number to activate! (From 1 to {len(options)})")
            return
        # Compared as numbers: as text "10" sorts before "2", so "/update_sessions 2 10" was rejected
        if idxs != sorted(idxs):
            bot.send_message(message.chat.id, text = f"Enter option numbers in increasing order!")
            return
        to_be_activated = [sess for idx, sess in enumerate(list(options.keys())) if idx + 1 in idxs]
        
        for sess in options:
            options[sess]["Active"] = 1 if sess in to_be_activated else 0

        save_messages(messages)
        new_option_format = '\n'.join(map(lambda x: f'{x} (Cap {options[x]["Capacity"]})', to_be_activated))
        bot.send_message(message.chat.id, f"Session activated: \n{new_option_format}")

@_admin_group_perms
@_log
def set_capacity(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.strip().split()
    options = get_sessions(messages)
    if len(command_params) != 3:
        bot.send_message(message.chat.id, text = f"Usage: /set_capacity <session_number> <capacity>")
    else:
        _, session_idx, new_capacity = command_params
        session_idx, new_capacity = _parse_number(session_idx), _parse_number(new_capacity)
        if new_capacity is None or new_capacity < 1:
            # A negative capacity used to be accepted, and then cut voters off the end of the list
            bot.send_message(message.chat.id, "Capacity must be a whole number of at least 1!")
            return
        if session_idx is not None and 0 < session_idx <= len(options):
            sess_name = list(options.keys())[session_idx - 1]
            old_capacity = options[sess_name]["Capacity"]
            options[sess_name]["Capacity"] = new_capacity
            save_messages(messages)
            bot.send_message(message.chat.id, f"Session capacity updated!\nSession: {sess_name}\nChange: {old_capacity} to {new_capacity}")
        else:
            bot.send_message(message.chat.id, f"Invalid session number! Choose between 1 and {len(options)} inclusive!")

@_admin_group_perms
@_log
def set_payment_director(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.strip().split()
    if len(command_params) != 4:
        bot.send_message(message.chat.id, text = f"Usage: /set_payment_director <name> <handle without @> <mobile no.>")
    else:
        _, payment_director_name, payment_director_handle, payment_director_phone = command_params
        if not payment_director_phone.isdigit() or len(payment_director_phone) != 8:
            bot.send_message(message.chat.id, text = f"Invalid phone number! Please enter an 8-digit number.")
            return
        change_payment_director(messages, payment_director_name, f"@{payment_director_handle}", payment_director_phone)
        save_messages(messages)
        bot.send_message(message.chat.id, f"Payment director updated to:\nName: {payment_director_name}\nHandle: {payment_director_handle}\nPhone Number: {payment_director_phone}")

@_admin_group_perms
@_log
def set_bot_director(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.strip().split()
    if len(command_params) != 3:
        bot.send_message(message.chat.id, text = f"Usage: /set_bot_director <name> <handle without @>")
    else:
        _, bot_director_name, bot_director_handle = command_params
        change_bot_director(messages, bot_director_name, f"@{bot_director_handle}")
        save_messages(messages)
        bot.send_message(message.chat.id, f"Bot director updated to:\nName: {bot_director_name}\nHandle: {bot_director_handle}")

@_admin_group_perms
@_log
def set_location(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command, *params = message.text.strip().split()
    params = " ".join(params).split(",")
    if len(params) != 2:
        bot.send_message(message.chat.id, text = f"Usage: /set_location <name>, <building>\nNote: Please separate the name and building with a comma.")
    else:
        name, building = params
        name, building = name.strip(), building.strip()
        change_location(messages, name, building)
        save_messages(messages)
        bot.send_message(message.chat.id, f"Location updated to:\nName: {name}\nBuilding: {building}")

@_admin_group_perms
@_log
def set_cost(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.strip().split()
    if len(command_params) != 2:
        bot.send_message(message.chat.id, text = f"Usage: /set_cost <amount without $>")
    else:
        _, cost = command_params
        try:
            amount = float(cost)
        except ValueError:  # e.g. "1.2.3" passed the old check, then crashed here
            amount = None
        # float() also accepts "nan" and "inf", which fail this check
        if amount is None or not 0 <= amount < float("inf"):
            bot.send_message(message.chat.id, text = f"Invalid cost! Please enter a valid number.")
            return
        change_cost(messages, amount)
        save_messages(messages)
        bot.send_message(message.chat.id, f"Cost updated to: ${get_cost(messages)}")
