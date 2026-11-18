import html
import telebot
import logging
import pytz
from datetime import datetime
from polling.confirmation import send_confirmation_message
from state import poll_state
from state.poll_state import PollSet, user_key, parse_user_key
from state.config import get_admin_id
from state.messages import (get_sessions, get_active_sessions, get_prepoll_template, get_poll_question,
                            get_poll_body_template, fill_placeholders, poll_detail_placeholders,
                            payment_director_placeholders)
from utils.tg_logging import send_log_message
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from telebot import TeleBot

logger = logging.getLogger(__name__)
singapore_tz = pytz.timezone("Asia/Singapore")

def remember_started_user(started_users: set, user_id: int) -> None:
    """Record that the bot can DM this user. Saved with the rest of the poll state."""
    if user_id in started_users:
        return
    started_users.add(user_id)
    poll_state.mark_dirty()

def can_dm_user(bot: TeleBot, user_id: int, started_users: set) -> bool:
    """True if the bot can DM this user (needed later for confirmation messages).

    started_users is a set, so the lookup is O(1). Only users the bot hasn't
    seen before cost a Telegram call, and only once.
    """
    if user_id in started_users:
        return True
    try:
        # One call, no message left behind (at most a brief "typing..." in their chat).
        # Telegram refuses it if the user never started the bot or has blocked it.
        bot.send_chat_action(user_id, "typing")
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 403 or "chat not found" in str(e.description).lower():
            logger.info(f"User {user_id} has not started the bot: {e}")
            return False
        # Rate limits (429) or other errors: don't block the vote.
        # Confirmation already logs anyone it can't DM.
        logger.warning(f"Could not check whether user {user_id} started the bot, allowing vote: {e}")
        return True
    except Exception as e:
        logger.warning(f"Could not check whether user {user_id} started the bot, allowing vote: {e}")
        return True
    remember_started_user(started_users, user_id)
    return True

def clear_polls(polls: dict) -> None:
    polls.clear()

def send_prepoll(bot: TeleBot, messages: dict, group_id: str | int, config: dict) -> None:
    # Only this week's active sessions (inactive ones used to be announced too)
    sessions = get_sessions(messages)
    formatted_slots = "\n    ".join(f"- <b>{name}</b> ({sessions[name]['Capacity']} pax)"
                                    for name in get_active_sessions(messages))
    prepoll_message = fill_placeholders(get_prepoll_template(messages), {
        "POLL_OPTIONS": formatted_slots,
        **payment_director_placeholders(messages),
        **poll_detail_placeholders(messages),
    })

    bot.send_message(group_id, prepoll_message, parse_mode='HTML')
    logger.info(f"Prepoll announcement sent to: {group_id}")
    send_log_message(bot, f"Prepoll started in group {group_id}", config)

def render_poll_message(messages: dict, poll: dict) -> str:
    """Build the poll message from the current votes, so the text never needs to be stored."""
    options = get_sessions(messages)
    body = fill_placeholders(get_poll_body_template(messages), poll_detail_placeholders(messages))
    text = f"<blockquote><b>{get_poll_question(messages)}</b></blockquote>\n\n" + body
    for sess_name, names in poll.items():
        if sess_name == "message_id":
            continue
        # .get: a session deleted mid-poll shouldn't break the message
        capacity = options.get(sess_name, {}).get("Capacity", "?")
        text += f"<blockquote><b>{sess_name}</b> (👤 {len(names)}/{capacity})</blockquote>"
        # Escaped: the message is HTML, and a name containing & or < would make Telegram reject it
        text += ("\n".join(html.escape(name) for name in names) + "\n") if names else "No votes yet\n"
        text += "\n"
    return text

def start_poll_announcement(bot: TeleBot, messages: dict, polls: dict, group_id: str | int, message_ids: dict, payments: dict, config: dict) -> None:
    active = get_active_sessions(messages)

    poll_id = f"{group_id}_{int(datetime.now().timestamp())}"  # Create a unique poll_id
    # Only active sessions (inactive ones used to appear in the message after the first vote)
    polls[poll_id] = {name: [] for name in active}

    markup = InlineKeyboardMarkup()
    for name in active:
        message_ids[name] = []
        markup.add(InlineKeyboardButton(name, callback_data=f"{poll_id}:{name}"))

    poll_message = render_poll_message(messages, polls[poll_id])
    sent_message = bot.send_message(group_id, poll_message, reply_markup=markup, parse_mode='HTML')
    polls[poll_id]["message_id"] = sent_message.message_id
    send_log_message(bot, f"Poll started in group {group_id} with id {sent_message.message_id}", config)
    logger.info(f"Poll started in group: {group_id}")

    poll_state.mark_dirty()

def callback_query(call: CallbackQuery, bot: TeleBot, messages: dict, polls: dict, message_ids: dict, group_id: str | int, config: dict, started_users: set) -> None:
    if call.data == "poll_ended":
        bot.answer_callback_query(call.id, "The poll has ended. Please wait for next week's poll to be released.", show_alert=True)
        return

    poll_id, option = call.data.split(":")
    if poll_id not in polls or option not in polls[poll_id]:
        # old poll button
        bot.answer_callback_query(call.id, "This poll has closed.", show_alert=True)
        return

    user = call.from_user
    user_name = f"{user.full_name} (@{user.username})" if user.username else user.full_name
    names = polls[poll_id][option]
    voters = message_ids.setdefault(option, [])

    # Found by Telegram user ID, not by name: a name can change between clicks (which
    # used to add a duplicate vote), and two people can share one (which used to crash)
    position = _find_voter(voters, user.id)
    is_removing = position is not None

    # Only check when adding a vote: removing one doesn't need a DM later
    if not is_removing and not can_dm_user(bot, user.id, started_users):
        bot.answer_callback_query(call.id, "Please start the bot to participate in the poll. Click the link provided in the poll message to start.", show_alert=True)
        return

    # Toggle user vote
    if is_removing:
        logger.info(f"Removing {user_name} from {option}")
        voters.pop(position)
        # names and voters are always added and removed together, so they line up by position
        if len(names) == len(voters) + 1:
            names.pop(position)
        elif user_name in names:
            names.remove(user_name)
    else:
        logger.info(f"Adding {user_name} to {option}")
        names.append(user_name)
        voters.append(user_key(user))

    # Saving and the message edit happen in the background (state/poll_state.py),
    # batched so a burst of votes doesn't hit Cloud Storage or Telegram limits
    poll_state.mark_dirty()
    poll_state.queue_edit(call.message.chat.id, call.message.message_id,
                          render_poll_message(messages, polls[poll_id]), call.message.reply_markup)

    # Answer straight away so the button stops spinning; the message catches up within a few seconds
    bot.answer_callback_query(call.id, f"Removed from {option}" if is_removing else f"Added to {option}")


def _find_voter(voters: list, user_id: int):
    """Position of this Telegram user in a session's voter list, or None if they haven't voted."""
    for position, key in enumerate(voters):
        try:
            if parse_user_key(key)[2] == user_id:
                return position
        except Exception:
            continue  # an unreadable entry can't be this user
    return None


def open_poll(bot: TeleBot, messages: dict, config: dict, group_id: int, poll_set: PollSet) -> None:
    """Start a fresh poll in group_id. Replaces the previous poll in this set, and its payments."""
    poll_set.polls.clear()
    poll_set.message_ids.clear()
    poll_set.payments.clear()
    poll_state.mark_dirty()  # so the clear is saved even if sending the new poll fails
    start_poll_announcement(bot, messages, poll_set.polls, group_id, poll_set.message_ids, poll_set.payments, config)


def close_poll(bot: TeleBot, messages: dict, config: dict, group_id: int, poll_set: PollSet) -> None:
    """End this set's open poll and send confirmations. The payment list goes to the admin group."""
    end_poll(bot, poll_set.polls, poll_set.message_ids, group_id, get_admin_id(config),
             poll_set.payments, messages, config, poll_set.payment_button_prefix)


def end_poll(bot: TeleBot, polls: dict, message_ids: dict, chat_id: str | int, admin_id: str | int, payments: dict, messages: dict, config: dict, payment_button_prefix: str = "") -> None:
    if not polls:
        logger.info("end_poll called but there is no open poll")
        send_log_message(bot, "End poll called, but there is no open poll", config)
        return

    poll_id = next(iter(polls))
    poll = polls.pop(poll_id)
    message_id = poll["message_id"]

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Poll ended", callback_data="poll_ended"))
    # Replaces any vote edit still waiting for this message, and flush sends it right away.
    # Any later clicks on the old buttons get "This poll has closed."
    poll_state.queue_edit(chat_id, message_id, render_poll_message(messages, poll), markup)
    poll_state.mark_dirty()
    poll_state.flush(force=True)
    logger.info(f"Poll ended in group {chat_id} with id {message_id}")
    send_log_message(bot, f"Poll ended in group {chat_id} with id {message_id}", config)

    try:
        send_confirmation_message(bot, admin_id, message_ids, payments, messages, config, payment_button_prefix)

    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"Error ending poll for group {chat_id}: {e}")
        send_log_message(bot, f"Error ending poll for group {chat_id}: {e}", config)

        if "message is not modified" in str(e):
            logger.info("The message was not modified.")
        elif "message to edit not found" in str(e):
            logger.info("The message to edit was not found.")
        elif "bot was kicked from the group chat" in str(e):
            logger.info("The bot was kicked from the group chat.")
        else:
            logger.error(f"Unhandled error: {e}")
