import logging
from utils.gcs_utils import save_json_file_to_gcs
from utils.tg_logging import send_log_message
from utils.datetime_utils import is_valid_day, is_valid_time, convert_to_ampm, DAYS

from telebot import TeleBot
from telebot.types import Message
from typing import Callable

logger = logging.getLogger(__name__)

def _session_management_wrapper(function: Callable[..., None]) -> Callable[..., None]:
    def new_function(bot: TeleBot, message: Message, messages: dict, admin_group: int) -> None:
        try:
            if message.chat.id == admin_group:
                function(bot, message, messages)
            else:
                bot.send_message(message.chat.id, f"You are not allowed to use this in {message.chat.title}")
        except Exception as e:
            send_log_message(bot, f"Error in {function.__name__}: {e}")
            logger.error(f"Error in {function.__name__}: {e}")
    
    return new_function

@_session_management_wrapper
def view_sessions(bot: TeleBot, message: Message, messages: dict) -> None:
    command_params = message.text.split()
    if len(command_params) != 1:
        bot.send_message(message.chat.id, text = f"usage: /view_session")
    else:
        all_options = messages.get("Poll", {}).get("all_options", [])
        active_options = messages.get("Poll", {}).get("Options", [])

        other_options_format = "\n".join([f"{_i + 1}: {_option}" for _i, _option in enumerate(all_options) if _option not in active_options])
        active_options_format = "\n".join([f"{_i + 1}: {_option}" for _i, _option in enumerate(all_options) if _option in active_options])
        bot.send_message(message.chat.id, f"Active Sessions:\n{active_options_format}\n\nAvailable Sessions:\n{other_options_format}")

@_session_management_wrapper
def add_session(bot: TeleBot, message: Message, messages: dict) -> None:
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

        if new_all_option in messages["Poll"]["all_options"]:
            bot.send_message(message.chat.id, "Session already exists!")
            return

        messages["Poll"]["all_options"].append(new_all_option)
        messages["Poll"]["all_options"].sort(key=lambda x: int(DAYS[x.strip().split()[0].lower()]))

        save_json_file_to_gcs("messages.json", messages)
        bot.send_message(message.chat.id, f"Session added:\n{new_all_option}")

@_session_management_wrapper
def delete_session(bot: TeleBot, message: Message, messages: dict) -> None:
    command_params = message.text.strip().split()
    all_options = messages.get("Poll", {}).get("all_options", [])
    if len(command_params) != 2:
        bot.send_message(message.chat.id, text = f"usage: /delete_session <number>")
    else:
        _, idx = command_params
        idx = int(idx)
        if 0 < idx <= len(all_options):
            removed = all_options.pop(idx - 1)
            messages["Poll"]["all_options"] = all_options
            save_json_file_to_gcs("messages.json", messages)
            bot.send_message(message.chat.id, f"Session deleted:\n{removed}")
        else:
            bot.send_message(message.chat.id, f"Enter a valid option number to delete! (From 1 to {len(all_options)})")

@_session_management_wrapper
def update_sessions(bot: TeleBot, message: Message, messages: dict) -> None:
    command_params = message.text.split()
    all_options = messages.get("Poll", {}).get("all_options", [])
    if len(command_params) == 1 or len(command_params) > 4:
        all_options_format = "\n".join([f"{_i + 1}: {_option}" for _i, _option in enumerate(all_options)])
        bot.send_message(message.chat.id,
                            text = f"usage: /update_session <Option 1> <Option 2> <Option 3> (Enter the option numbers in ascending order)\n{all_options_format}")
    elif command_params[1:] != sorted(command_params[1:]):
        bot.send_message(message.chat.id, text = f"Enter option numbers in increasing order!")
    else:
        for i in command_params[1:]:
            if int(i) < 1 or int(i) > len(all_options):
                bot.send_message(message.chat.id, f"Enter a valid option number to activate! (From 1 to {len(all_options)})")
                return
        new_options = [all_options[int(_i )- 1] for _i in command_params[1:]]
        messages["Poll"]["Options"] = new_options
        save_json_file_to_gcs("messages.json", messages)
        new_option_format = '\n'.join(new_options)
        bot.send_message(message.chat.id, f"Session updated:\n{new_option_format}")
