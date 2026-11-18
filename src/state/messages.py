"""Everything the code reads from or writes to messages.json, in one place.

messages.json holds the message templates (prepoll, poll, confirmation) and the
details shown in them (sessions, cost, location, directors). Other files call
these functions instead of indexing the dict, so only this file needs to know the
JSON layout. If messages.json is ever restructured, this is the file to change.

Getters raise KeyError if something is missing, on purpose: a broken messages.json
should fail loudly (the error is logged), not send messages with blanks in them.
"""
import re

from state.cloud_storage import save_json_file_to_gcs

MESSAGES_FILE = "messages.json"


def save_messages(messages: dict) -> None:
    save_json_file_to_gcs(MESSAGES_FILE, messages)


###########################
# Templates
###########################
def get_prepoll_template(messages: dict) -> str:
    return messages["Prepoll Announcement"]

def get_poll_question(messages: dict) -> str:
    return messages["Poll"]["Question"]

def get_poll_body_template(messages: dict) -> str:
    return messages["Poll"]["Body"]

def get_confirmation_template(messages: dict) -> str:
    return messages["Confirmation"]["Body"]

def get_google_doc(messages: dict) -> str:
    return messages["Confirmation"]["Google Doc"]


###########################
# Sessions
###########################
def get_sessions(messages: dict) -> dict:
    """Every session, in display order: {"Monday 7.00pm-9.00pm": {"Capacity": 36, "Active": 1}, ...}"""
    return messages["Poll"]["Options"]

def get_active_sessions(messages: dict) -> list:
    """Names of the sessions that go into this week's poll."""
    return [name for name, session in get_sessions(messages).items() if session["Active"]]

def replace_sessions(messages: dict, sessions: dict) -> None:
    messages["Poll"]["Options"] = sessions


###########################
# Directors, location and cost
###########################
def get_payment_director(messages: dict) -> dict:
    """{"Name": ..., "Handle": "@...", "Phone Number": ...}"""
    return messages["Payment Director"]

def change_payment_director(messages: dict, name: str, handle: str, phone: str) -> None:
    messages["Payment Director"] = {"Name": name, "Handle": handle, "Phone Number": phone}

def get_bot_director(messages: dict) -> dict:
    """{"Name": ..., "Handle": "@..."}"""
    return messages["Bot Director"]

def change_bot_director(messages: dict, name: str, handle: str) -> None:
    messages["Bot Director"] = {"Name": name, "Handle": handle}

def get_location(messages: dict) -> dict:
    """{"Name": ..., "Building": ...}"""
    return messages["Location"]

def change_location(messages: dict, name: str, building: str) -> None:
    messages["Location"] = {"Name": name, "Building": building}

def get_cost(messages: dict) -> str:
    """Cost per session as shown in messages, e.g. "5.00"."""
    return messages["Cost"]

def get_price_per_session(messages: dict) -> float:
    return float(get_cost(messages))

def change_cost(messages: dict, amount: float) -> None:
    messages["Cost"] = f"{amount:.2f}"


###########################
# Placeholders
###########################
def poll_detail_placeholders(messages: dict) -> dict:
    """Placeholders for the bot director, location and cost."""
    bot_director, location = get_bot_director(messages), get_location(messages)
    return {
        "BOT_DIRECTOR": bot_director["Name"],
        "BOT_HANDLE": bot_director["Handle"],
        "LOCATION_NAME": location["Name"],
        "LOCATION_BUILDING": location["Building"],
        "COST": get_cost(messages),
    }

def payment_director_placeholders(messages: dict) -> dict:
    """Placeholders for the payment director's details."""
    director = get_payment_director(messages)
    return {
        "PAYMENT_DIRECTOR": director["Name"],
        "PAYMENT_HANDLE": director["Handle"],
        "PAYMENT_NUMBER": director["Phone Number"],
    }

def fill_placeholders(template: str, values: dict) -> str:
    """Replace each placeholder in the template (e.g. COST) with its value.

    Done in a single pass, so a value that happens to contain a placeholder's
    name is never replaced a second time.
    """
    if not values:
        return template
    # Longest names first, so a name that starts with another one still matches whole
    pattern = re.compile("|".join(re.escape(name) for name in sorted(values, key=len, reverse=True)))
    return pattern.sub(lambda match: str(values[match.group(0)]), template)
