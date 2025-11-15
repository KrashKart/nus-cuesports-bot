import logging
from utils.gcs_utils import save_json_file_to_gcs
from utils.permissions import _admin_group_perms, _log
from utils.datetime_utils import is_valid_day, is_valid_time, convert_to_ampm, DAYS

from telebot import TeleBot
from telebot.types import Message

logger = logging.getLogger(__name__)
DEFAULT_MAX_CAPACITY = 36

@_log
@_admin_group_perms
def view_sessions(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.split()
    if len(command_params) != 1:
        bot.send_message(message.chat.id, text = f"usage: /view_session")
    else:
        options = messages.get("Poll", {}).get("Options", {})

        other_options_format = "\n".join([f"{_i + 1}: {k} (Cap {v['Capacity']})" for _i, (k, v) in enumerate(options.items()) if not v["Active"]])
        active_options_format = "\n".join([f"{_i + 1}: {k} (Cap {v['Capacity']})" for _i, (k, v) in enumerate(options.items()) if v["Active"]])
        bot.send_message(message.chat.id, f"Active Sessions:\n{active_options_format}\n\nAvailable Sessions:\n{other_options_format}")

@_log
@_admin_group_perms
def add_session(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.strip().split()

    if len(command_params) != 4:
        bot.send_message(message.chat.id,
                            text = f"usage: /add_session <day> <start time> <end time>\n All times are in HH:MM format.\ne.g. /add_session Monday 20:00")
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
        options = messages["Poll"]["Options"]
        if new_all_option in options:
            bot.send_message(message.chat.id, "Session already exists!")
            return

        options[new_all_option] = {"Capacity": DEFAULT_MAX_CAPACITY, "Active": 0}
        messages["Poll"]["Options"] = dict(sorted(options.items(), 
                                                  key=lambda x: int(DAYS[x[0].strip().split()[0].lower()])))

        save_json_file_to_gcs("messages.json", messages)
        bot.send_message(message.chat.id, f"Session added:\n{new_all_option}")

@_log
@_admin_group_perms
def delete_session(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.strip().split()
    options = messages.get("Poll", {}).get("Options", [])
    if len(command_params) != 2:
        bot.send_message(message.chat.id, text = f"usage: /delete_session <number>")
    else:
        _, idx = command_params
        idx = int(idx)
        if 0 < idx <= len(options):
            sess_name = list(options.keys())[idx - 1]
            del options[sess_name]
            messages["Poll"]["Options"] = options

            save_json_file_to_gcs("messages.json", messages)
            bot.send_message(message.chat.id, f"Session deleted:\n{sess_name}")
        else:
            bot.send_message(message.chat.id, f"Enter a valid option number to delete! (From 1 to {len(options)})")

@_log
@_admin_group_perms
def update_sessions(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.split()
    options = messages.get("Poll", {}).get("Options", [])
    if len(command_params) == 1 or len(command_params) > 4:
        all_options_format = "\n".join([f"{_i + 1}: {_option}" for _i, _option in enumerate(options)])
        bot.send_message(message.chat.id,
                            text = f"usage: /update_session <Option 1> <Option 2> <Option 3> (Enter the option numbers in ascending order)\n{all_options_format}")
    elif command_params[1:] != sorted(command_params[1:]):
        bot.send_message(message.chat.id, text = f"Enter option numbers in increasing order!")
    else:
        for i in command_params[1:]:
            if int(i) < 1 or int(i) > len(options):
                bot.send_message(message.chat.id, f"Enter a valid option number to activate! (From 1 to {len(options)})")
                return
        idxs = list(map(int, command_params[1:]))
        to_be_activated = [sess for idx, sess in enumerate(list(options.keys())) if idx + 1 in idxs]
        
        for sess in options:
            options[sess]["Active"] = 1 if sess in to_be_activated else 0
        
        messages["Poll"]["Options"] = options
        save_json_file_to_gcs("messages.json", messages)
        new_option_format = '\n'.join(map(lambda x: f'{x} (Cap {options[x]["Capacity"]})', to_be_activated))
        bot.send_message(message.chat.id, f"Session activated: \n{new_option_format}")

@_log
@_admin_group_perms
def set_capacity(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    command_params = message.text.strip().split()
    options = messages.get("Poll", {}).get("Options", [])
    if len(command_params) != 3:
        bot.send_message(message.chat.id, text = f"Usage: /set_capacity <session_number> <capacity>")
    else:
        _, session_idx, new_capacity = command_params
        session_idx = int(session_idx)
        if 0 < session_idx <= len(options):
            sess_name = list(options.keys())[session_idx - 1]
            old_capacity = options[sess_name]["Capacity"]
            options[sess_name]["Capacity"] = int(new_capacity)
            messages["Poll"]["Options"] = options
            save_json_file_to_gcs("messages.json", messages)
            bot.send_message(message.chat.id, f"Session capacity updated!\nSession: {sess_name}\nChange: {old_capacity} to {new_capacity}")
        else:
            bot.send_message(message.chat.id, f"Invalid session number! Choose between 1 and {len(options)} inclusive!")
