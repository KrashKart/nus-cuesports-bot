"""Poll state kept in memory and saved to Cloud Storage in the background.

Everything that changes while a poll runs lives in one file, poll_state.json:
the votes (polls, message_ids), payments, the users the bot can DM, and the
last Telegram update ID. Saving them together means they can't get out of step.

How it works:
- Handlers change the module-level containers below while holding state_lock
  (main.py takes it for every webhook update and scheduled route), then call
  mark_dirty(), and queue_edit() for the poll message.
- A background thread wakes every TICK seconds. It saves the file at most every
  SAVE_INTERVAL seconds, and sends the newest queued text for each message at
  most every EDIT_INTERVAL seconds. A burst of 20 votes becomes a few saves and
  edits instead of 60 saves and 20 edits.
- flush(force=True) does both straight away (used by /restart, end_poll, and
  when the process exits).

Locks: state_lock guards the state. _write_lock and _edit_lock only serialise
network calls, and are never held while taking state_lock, so they can't deadlock.
"""
import atexit
import copy
import logging
import threading
import time

import telebot
from google.api_core.exceptions import NotFound

from state.cloud_storage import load_json_file_from_gcs, save_json_file_to_gcs

logger = logging.getLogger(__name__)

POLL_STATE_FILE = "poll_state.json"

# Read once, only if poll_state.json doesn't exist yet (first start after this change)
LEGACY_FILES = {
    "polls": "polls.json",
    "message_ids": "message_ids.json",
    "payments": "payments.json",
    "updates": "updates.json",
    "started_users": "started_users.json",
}

TICK = 0.5          # seconds between background checks
SAVE_INTERVAL = 2   # Cloud Storage allows about one write per second to the same file
EDIT_INTERVAL = 3   # per message; keeps well under Telegram's limits for messages in a group

# Held for every change to the state below. RLock so code that already holds it can call flush().
state_lock = threading.RLock()

# The state itself. Always changed in place (never reassigned) so every module shares the same objects.
polls: dict = {}
message_ids: dict = {}
payments: dict = {}
updates: dict = {}
started_users: set = set()

_bot = None
_saving_disabled = False

# Saving
_version = 0          # bumped by mark_dirty()
_saved_version = 0    # newest version written to storage
_last_save = float("-inf")
_write_lock = threading.Lock()  # one write at a time, and an older snapshot never overwrites a newer one

# Message edits
_queue_lock = threading.Lock()
_edit_seq = 0
_pending_edits = {}      # (chat_id, message_id) -> (seq, text, reply_markup); only the newest is kept
_last_edit_time = {}     # (chat_id, message_id) -> time.monotonic() of the last edit sent
_applied_edit_seq = {}   # (chat_id, message_id) -> seq of the last edit sent
_edit_lock = threading.Lock()


def _read(file_name):
    """The file's contents, or None if it doesn't exist.

    Other errors are raised on purpose: starting with empty state and then
    saving it would wipe the real data in the bucket.
    """
    try:
        return load_json_file_from_gcs(file_name)
    except NotFound:
        return None

def load() -> None:
    global _version
    data = _read(POLL_STATE_FILE)
    if data is None:
        logger.info(f"{POLL_STATE_FILE} not found; loading the old separate files")
        data = {key: _read(name) for key, name in LEGACY_FILES.items()}
        _version += 1  # so the first background save creates poll_state.json

    # backwards compatibility for all the old files in case
    # we need to rebuild poll_state.json again
    polls.update(data.get("polls") or {})
    message_ids.update(data.get("message_ids") or {})
    payments.update(data.get("payments") or {})
    updates.update(data.get("updates") or {})
    started_users.update(data.get("started_users") or [])

def start(bot) -> None:
    """Start the background saver/editor."""
    global _bot
    _bot = bot
    threading.Thread(target=_background_loop, name="poll-state-flush", daemon=True).start()

    # Runs when the process exits normally, e.g. gunicorn stopping a worker on SIGTERM
    atexit.register(_final_flush)

def mark_dirty() -> None:
    """Call after changing any state, while holding state_lock."""
    global _version
    with state_lock:
        _version += 1

def queue_edit(chat_id, message_id, text, reply_markup) -> None:
    """Ask for a message to show `text`. Replaces any edit still waiting for that message."""
    global _edit_seq
    with _queue_lock:
        _edit_seq += 1
        _pending_edits[(chat_id, message_id)] = (_edit_seq, text, reply_markup)

def disable_saving() -> None:
    """For /restart_no_save"""
    global _saving_disabled
    _saving_disabled = True


def flush(force: bool = False) -> None:
    """Save and send edits that are due. force=True ignores the intervals."""
    if _saving_disabled:
        return
    _save(force)
    _apply_edits(force)


def _save(force: bool) -> None:
    global _last_save, _saved_version
    now = time.monotonic()
    with state_lock:
        # in case no neeed to save, just return early
        if _saving_disabled or _version == _saved_version:
            return
        # not force flush and the save interval hasn't refreshed
        if not force and now - _last_save < SAVE_INTERVAL:
            return
        version = _version
        snapshot = copy.deepcopy({
            "polls": polls,
            "message_ids": message_ids,
            "payments": payments,
            "updates": updates,
            "started_users": sorted(started_users),
        })
        _last_save = now

    # messages written outside state_lock so they don't block the main thread
    with _write_lock:
        # if saving disabled or a newer version has already been
        # written, just return
        if _saving_disabled or version <= _saved_version:
            return
        try:
            save_json_file_to_gcs(POLL_STATE_FILE, snapshot)
            _saved_version = version
        except Exception as e:
            # _saved_version is unchanged, so the next tick tries again
            logger.error(f"Could not save {POLL_STATE_FILE}, will retry: {e}")

def _apply_edits(force: bool) -> None:
    now = time.monotonic()
    due = []
    with _queue_lock:
        for key, edit in list(_pending_edits.items()):
            if force or now - _last_edit_time.get(key, float("-inf")) >= EDIT_INTERVAL:
                due.append((key, edit))
                del _pending_edits[key]
                _last_edit_time[key] = now

    with _edit_lock:
        for key, (seq, text, reply_markup) in due:
            if seq <= _applied_edit_seq.get(key, 0):
                continue  # a newer text for this message has already been sent
            _send_edit(key, seq, text, reply_markup)

def _send_edit(key, seq, text, reply_markup) -> None:
    chat_id, message_id = key
    try:
        _bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                               reply_markup=reply_markup, parse_mode='HTML')
        _applied_edit_seq[key] = seq
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            _applied_edit_seq[key] = seq
        elif e.error_code == 429:
            retry_after = (e.result_json or {}).get("parameters", {}).get("retry_after", EDIT_INTERVAL)
            logger.warning(f"Telegram rate limit editing message {message_id}; retrying in {retry_after}s")
            with _queue_lock:
                if key not in _pending_edits:  # unless a newer edit was queued meanwhile
                    _pending_edits[key] = (seq, text, reply_markup)
                _last_edit_time[key] = time.monotonic() + retry_after - EDIT_INTERVAL
        else:
            logger.error(f"Could not edit message {message_id} in {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Could not edit message {message_id} in {chat_id}: {e}")

def _background_loop() -> None:
    while True:
        time.sleep(TICK)
        try:
            flush()
        except Exception as e:
            logger.error(f"Background flush failed: {e}")

def _final_flush() -> None:
    if _saving_disabled:
        return
    logger.info("Saving poll state before exit")
    flush(force=True)
