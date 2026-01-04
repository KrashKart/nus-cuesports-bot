import json
import telebot
from telebot import TeleBot
from typing import Any
from utils.gcs_utils import load_json_file_from_gcs

# deprecated
def load_json_file(file_path: str) -> Any:
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        raise
    except json.JSONDecodeError:
        raise

def send_log_message(bot: TeleBot, message: str) -> None:
    config = load_json_file_from_gcs("config.json")
    logging_group_id = config["groups"]["LOGGING_GROUP"]["id"]
    try:
        bot.send_message(logging_group_id, message)
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Failed to send log message to telegram logging group: {e}")
