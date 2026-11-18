from telebot.types import Update
from telebot import TeleBot
from utils import poll_state

def update_with_cache(bot: TeleBot, update: Update, updates: dict) -> None:
    # Correct because the webhook uses max_connections=1, so updates arrive in order
    if update.update_id > updates.get("latest", 0):
        updates["latest"] = update.update_id
        poll_state.mark_dirty()  # saved with poll state, so this survives restarts
        bot.process_new_updates([update])