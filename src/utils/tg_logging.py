import json
import telebot
import os  

def load_json_file(file_path):
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        raise
    except json.JSONDecodeError:
        raise

def send_log_message(bot, message):
    config_path = os.path.join(os.path.dirname(__file__), "..", "json", "config.json")
    config = load_json_file(config_path)
    logging_group_id = config["groups"]["LOGGING_GROUP"]["id"]
    try:
        bot.send_message(logging_group_id, message)
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Failed to send log message to telegram logging group: {e}")
