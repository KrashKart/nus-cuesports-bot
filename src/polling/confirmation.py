import html
import telebot
import logging
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from state import poll_state
from state.poll_state import parse_user_key
from state.messages import (get_sessions, get_price_per_session, get_confirmation_template, get_google_doc,
                            fill_placeholders, payment_director_placeholders)
from utils.tg_logging import send_log_message
from utils.datetime_utils import DAYS

logger = logging.getLogger(__name__)

def send_confirmation_message(bot, admin_group, message_ids, payments, messages, config, payment_button_prefix=""):
    # price of training session
    price_per_session = get_price_per_session(messages)

    # Confirmation DMs go out once per poll. payments is only filled by the first run
    # (and cleared when a new poll starts), so if it has entries the DMs were already
    # sent: just re-post the payment list so admins can see the latest state.
    if payments:
        __send_payment_list(bot, admin_group, payments, price_per_session, payment_button_prefix)
        send_log_message(bot, "Confirmation already sent for this poll; re-sent payment list only", config)
        return

    # select the first N people that registered
    to_be_confirmed = __find_n_occupancy(message_ids, messages)

    # Reformat to_be_confirmed to {user1: {options: [options], paid:False}, user2: {options: [options], paid:False}...}
    __find_session_overlap(to_be_confirmed, payments)

    for _fullname_id, training_sess in payments.items():
        _, _, _userid = parse_user_key(_fullname_id)
        _training_sess = training_sess["options"]
        to_be_paid = len(_training_sess) * price_per_session

        _message = fill_placeholders(get_confirmation_template(messages), {
            "TO_BE_PAID": f"{to_be_paid:.2f}",
            "GOOGLE_DOC": get_google_doc(messages),
            "MESSAGE_FORMAT": __message_format(_training_sess),
            **payment_director_placeholders(messages),
        })

        try:
            bot.send_message(_userid, _message)
            logger.info(f"Sending Confirmation Message: {_fullname_id}")
        except telebot.apihelper.ApiTelegramException:
            logger.info(f"User have not started the bot: Unable to initiate conversation with user")
            send_log_message(bot, f"Unable to send confirmation: {_fullname_id}", config)

    send_log_message(bot, f"Sent confirmations to all poll members", config)

    if len(payments) != 0:
        __send_payment_list(bot, admin_group, payments, price_per_session, payment_button_prefix)

def __send_payment_list(bot, admin_group, payments, price_per_session, payment_button_prefix=""):
    markup, payment_message = __convert_payment_message(payments, price_per_session, payment_button_prefix)
    bot.send_message(admin_group, payment_message, reply_markup=markup, parse_mode='HTML')

def confirm_payment_query(call, bot, payments, messages, user_id, payment_button_prefix=""):
    """A button on the payment list was pressed: mark user_id as paid and update the list."""
    # Answered first, so the button stops its loading spinner even if the edit below fails
    bot.answer_callback_query(call.id)

    price_per_session = get_price_per_session(messages)
    for key in payments:
        if str(parse_user_key(key)[2]) == user_id:
            payments[key]["paid"] = True
            break

    poll_state.mark_dirty()
    markup, message = __convert_payment_message(payments, price_per_session, payment_button_prefix)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=message, reply_markup=markup, parse_mode='HTML')

def unconfirm_payment(bot, message, payments, messages, admin_group, payment_button_prefix=""):
    """/unconfirm <@username, user ID or full name>: mark someone as not paid.

    Needs an exact match. It used to match any part of the stored text, so "/unconfirm a"
    un-paid the first person with an "a" in their name, and a bare "/unconfirm" matched anyone.
    """
    parts = message.text.split(maxsplit=1)
    query = parts[1].strip() if len(parts) > 1 else ""
    if not query:
        bot.send_message(admin_group, "Usage: /unconfirm <@username, user ID or full name>")
        return

    wanted = query.lstrip("@").lower()
    matches = []
    for key in payments:
        full_name, username, user_id = parse_user_key(key)
        if wanted in (str(user_id), (username or "").lower(), (full_name or "").lower()):
            matches.append(key)

    if not matches:
        bot.send_message(admin_group, f"No one in the payment list matches {query}.")
        return
    if len(matches) > 1:
        people = "\n".join(f"• {_display_name(*parse_user_key(key)[:2])} (ID {parse_user_key(key)[2]})" for key in matches)
        bot.send_message(admin_group, f"More than one person matches {query}:\n{people}\nUse their @username or user ID instead.")
        return

    payments[matches[0]]["paid"] = False
    poll_state.mark_dirty()
    __send_payment_list(bot, admin_group, payments, get_price_per_session(messages), payment_button_prefix)

def bump_message(bot, payments):
    for _fullname_id, _training_sess in payments.items():
        _user_fullname, _user_username, _userid = _fullname_id.split("-")
        if not _training_sess["paid"]:
            bot.send_message(_userid, "bump")

def _display_name(full_name, username):
    return f"{full_name} (@{username})" if username else full_name

def __convert_payment_message(payment_lst, price_per_session, payment_button_prefix=""):
    markup = InlineKeyboardMarkup()
    message = f"<blockquote><b>Payment List</b></blockquote>"
    for _user in sorted(payment_lst):
        _val = payment_lst[_user]
        _user_fullname, _user_username, _userid = parse_user_key(_user)
        to_be_paid = f"{len(_val['options']) * price_per_session:.2f}"
        # Escaped: this message is HTML, and a name containing & or < would make Telegram reject it
        name = html.escape(_display_name(_user_fullname, _user_username))
        if _val["paid"]:
            message += f'{name}: ${to_be_paid} (Paid)\n'
        else:
            message += f'{name}: ${to_be_paid} (Not Paid)\n'
            markup.add(InlineKeyboardButton(f"{_user_username or _user_fullname}: ${to_be_paid}",
                                            callback_data=f"{payment_button_prefix}{_userid}"))
    return markup, message


def __message_format(lst):
    lst = list(lst)
    lst.sort(key=lambda x: int(DAYS[x.strip().split()[0].lower()]))
    if len(lst) == 1:
        return lst[0]
    elif len(lst) == 2:
        return " and ".join(lst)
    else:
        return ", ".join(lst[:len(lst) - 1]) + " and " + lst[-1]


def __find_session_overlap(message_ids, payments):
    # One entry per Telegram user ID, so someone whose name changed between votes
    # still gets a single entry (and a single confirmation DM)
    key_for_user = {parse_user_key(key)[2]: key for key in payments}
    for _option, _users in message_ids.items():
        for _user in _users:
            key = key_for_user.setdefault(parse_user_key(_user)[2], _user)
            if key not in payments:
                payments[key] = {"options": set(), "paid": False}
            # options is a list after a save/reload, so normalise to a set before adding
            payments[key]["options"] = set(payments[key]["options"])
            payments[key]["options"].add(_option)
    for v in payments.values():
        v["options"] = list(v["options"])
    poll_state.mark_dirty()


def __find_n_occupancy(message_ids, messages):
    to_be_confirmed = {}
    options = get_sessions(messages)
    for _key, _value in message_ids.items():
        # First N voters per session. message_ids is left as-is: it used to be trimmed
        # down to the waitlist here, which is what let a second /confirmation confirm it.
        # .get: if the session was deleted during the poll, confirm its voters instead of crashing
        _sess_limit = options.get(_key, {}).get("Capacity", len(_value))
        to_be_confirmed[_key] = _value[:_sess_limit]
    return to_be_confirmed
