import telebot
import logging
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils.gcs_utils import save_json_file_to_gcs
from utils.tg_logging import send_log_message
from utils.datetime_utils import DAYS

logger = logging.getLogger(__name__)
TRAINING_PRICE = 8

def send_confirmation_message(bot, admin_group, message_ids, payments, messages):

    # select the first N people that registered
    to_be_confirmed = __find_n_occupancy(message_ids, messages)

    # Reformat to_be_confirmed to {user1: {options: [options], paid:False}, user2: {options: [options], paid:False}...}
    __find_session_overlap(to_be_confirmed, payments)

    for _fullname_id, training_sess in payments.items():
        user_id_lst = eval(_fullname_id)
        _, _, _userid = user_id_lst[0], user_id_lst[1], user_id_lst[2]
        _training_sess = training_sess["options"]
        to_be_paid = len(_training_sess) * TRAINING_PRICE

        _message = messages["Confirmation"]["Body"]
        _google_doc = messages["Confirmation"]["Google Doc"]
        _message_format = __message_format(_training_sess)
        _payment_training_director = messages["Payment Director"]["Name"]
        _payment_phone_number = messages["Payment Director"]["Phone Number"]

        _message = (_message.replace("TO_BE_PAID", str(to_be_paid))
                            .replace("GOOGLE_DOC", _google_doc)
                            .replace("MESSAGE_FORMAT", _message_format)
                            .replace("TRAINING_DIRECTOR", _payment_training_director)
                            .replace("PHONE_NUMBER", _payment_phone_number))       

        try:
            bot.send_message(_userid, _message)
            logger.info(f"Sending Confirmation Message: {_fullname_id}")
        except telebot.apihelper.ApiTelegramException:
            logger.info(f"User have not started the bot: Unable to initiate conversation with user")
            send_log_message(bot, f"Unable to send confirmation: {_fullname_id}")

    send_log_message(bot, f"Sent confirmations to all poll members")

    if len(payments) != 0:
        markup, payment_message = __convert_payment_message(payments)
        bot.send_message(admin_group, payment_message, reply_markup=markup, parse_mode='HTML')

def confirm_payment_query(call, bot, payments, group_id):
    user_id = call.data
    for user_name in payments.keys():
        if user_id == str(eval(user_name)[2]):
            payments[user_name]["paid"] = True
            break

    markup, message = __convert_payment_message(payments)
    bot.edit_message_text(chat_id = group_id, message_id=call.message.message_id, text = message, reply_markup=markup, parse_mode='HTML')
    save_json_file_to_gcs("payments.json", payments)

def unconfirm_payment(bot, message, payments, ADMIN_GROUP):
    flag = False
    user = " ".join(message.text.split(" ")[1:])
    for _user in payments.keys():
        if user.lower() in _user.lower():
            payments[_user]["paid"] = False
            flag = True
            break
    if flag:
        markup, payment_message = __convert_payment_message(payments)
        bot.send_message(ADMIN_GROUP, payment_message, reply_markup=markup, parse_mode='HTML')
        save_json_file_to_gcs("payments.json", payments)
    else:
        bot.send_message(ADMIN_GROUP, text = f"Unable to unconfirm payment: {user}")

def bump_message(bot, payments):
    for _fullname_id, _training_sess in payments.items():
        _user_fullname, _user_username, _userid = _fullname_id.split("-")
        if not _training_sess["paid"]:
            bot.send_message(_userid, "bump")

def __convert_payment_message(payment_lst):
    markup = InlineKeyboardMarkup()
    message = f"<blockquote><b>Payment List</b></blockquote>"
    for _user in sorted(payment_lst):
        _val = payment_lst[_user]
        user_id_lst = eval(_user)
        _user_fullname, _user_username, _userid = user_id_lst[0], user_id_lst[1], user_id_lst[2]
        to_be_paid = len(_val["options"]) * TRAINING_PRICE
        if _val["paid"]:
            message += f'{_user_fullname} (@{_user_username}): ${to_be_paid} (Paid)\n'
        else:
            message += f'{_user_fullname} (@{_user_username}): ${to_be_paid} (Not Paid)\n'
            markup.add(InlineKeyboardButton(f"{_user_username}: ${to_be_paid}", callback_data = _userid))
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
    for _option, _users in message_ids.items():
        for _user in _users:
            if _user not in payments:
                payments[_user] = {"options": set(), "paid": False}
            payments[_user]["options"].add(_option)
    for _user, v in payments.items():
        v["options"] = list(v["options"])
        payments[_user] = v
    save_json_file_to_gcs("payments.json", payments)


def __find_n_occupancy(message_ids, messages):
    to_be_confirmed = {}
    options = messages["Poll"]["Options"]
    for _key, _value in message_ids.items():
        _sess_limit = options[_key]["Capacity"]
        if len(_value) >= _sess_limit:
            to_be_confirmed[_key] = _value[:_sess_limit]
            message_ids[_key] = _value[_sess_limit:len(_value)]
        else:
            to_be_confirmed[_key] = _value
            message_ids[_key] = []
    return to_be_confirmed


if __name__ == "__main__":
    payment_lst = {}