from telebot.types import Update
from telebot import TeleBot

def update_with_cache(bot: TeleBot, update: Update, updates: dict) -> None:
    if update.update_id > updates["latest"]:
        updates["latest"] = update.update_id
        bot.process_new_updates([update])