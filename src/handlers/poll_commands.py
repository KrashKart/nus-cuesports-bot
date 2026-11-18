"""Poll and confirmation commands, and the buttons on poll and payment-list messages.

The live commands (/prepoll, /poll, /end_poll, /confirmation, /unconfirm) post to the recre
group. The /test_* versions post to the admin group and keep their own votes and payments
(TEST in state/poll_state.py), so testing never touches the live poll or what people owe.
"""
import logging

from telebot import TeleBot
from telebot.types import CallbackQuery, Message

from handlers.permissions import _admin_group_perms, _log
from polling.confirmation import send_confirmation_message, confirm_payment_query, unconfirm_payment
from polling.poll import send_prepoll, open_poll, close_poll, callback_query
from state import poll_state
from state.config import get_admin_id, get_recre_id
from state.poll_state import LIVE, TEST
from utils.tg_logging import send_log_message

logger = logging.getLogger(__name__)


###########################
# Live (recre group)
###########################
@_admin_group_perms
@_log
def prepoll_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    send_prepoll(bot, messages, get_recre_id(config), config)

@_admin_group_perms
@_log
def poll_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    open_poll(bot, messages, config, get_recre_id(config), LIVE)

@_admin_group_perms
@_log
def end_poll_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    close_poll(bot, messages, config, get_recre_id(config), LIVE)

@_admin_group_perms
@_log
def confirmation_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    send_confirmation_message(bot, get_admin_id(config), LIVE.message_ids, LIVE.payments, messages, config)

@_admin_group_perms
@_log
def unconfirm_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    unconfirm_payment(bot, message, LIVE.payments, messages, get_admin_id(config))


###########################
# Test (admin group)
###########################
@_admin_group_perms
@_log
def test_prepoll_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    send_prepoll(bot, messages, get_admin_id(config), config)

@_admin_group_perms
@_log
def test_poll_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    open_poll(bot, messages, config, get_admin_id(config), TEST)

@_admin_group_perms
@_log
def test_end_poll_command(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    close_poll(bot, messages, config, get_admin_id(config), TEST)


###########################
# Buttons
###########################
def handle_button(bot: TeleBot, call: CallbackQuery, messages: dict, config: dict) -> None:
    """Every inline button press: votes on a poll, and "paid" buttons on a payment list."""
    data = call.data
    try:
        if data.startswith(TEST.payment_button_prefix):
            # Test payment-list buttons carry "testpay:<user id>"
            user_id = data[len(TEST.payment_button_prefix):]
            confirm_payment_query(call, bot, TEST.payments, messages, user_id, TEST.payment_button_prefix)
        elif data.isdigit():
            # Live payment-list buttons carry just the user ID
            confirm_payment_query(call, bot, LIVE.payments, messages, data)
        else:
            # Poll buttons carry "<poll id>:<session>", or "poll_ended" once the poll is over
            poll_set = TEST if data.split(":")[0] in TEST.polls else LIVE
            callback_query(call, bot, messages, poll_set.polls, poll_set.message_ids,
                           call.message.chat.id, config, poll_state.started_users)
    except Exception as e:
        logger.error(f"Error handling button {data!r}: {e}")
        send_log_message(bot, f"Error handling button {data!r}: {e}", config)
