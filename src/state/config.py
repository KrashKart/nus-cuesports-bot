"""Everything the code reads from or writes to config.json (groups, super users, schedules).

The getters for groups, super users and schedules use setdefault, so if the section is
missing it's created inside config. With .get(key, {}) a missing section came back as
a new, detached dict: changes made to it (e.g. /set_admin) were never saved.
"""
from state.cloud_storage import save_json_file_to_gcs

CONFIG_FILE = "config.json"


def save_config(config: dict) -> None:
    save_json_file_to_gcs(CONFIG_FILE, config)


###########################
# Groups
###########################
def get_groups(config: dict) -> dict:
    return config.setdefault("groups", {})

def get_admin_id(config: dict) -> int:
    return get_groups(config).get("ADMIN_GROUP", {}).get("id", None)

def get_recre_id(config: dict) -> int:
    return get_groups(config).get("RECRE_GROUP", {}).get("id", None)

def get_log_id(config: dict) -> int:
    return get_groups(config).get("LOGGING_GROUP", {}).get("id", None)


###########################
# Super User
###########################
def get_super_users(config: dict) -> list:
    return config.setdefault("super_users", [])

def get_super_users_id(config: dict) -> list:
    return list(map(lambda x: x["id"], get_super_users(config)))

###########################
# Scheduling
###########################
def get_schedule(config: dict) -> dict:
    return config.setdefault("schedules", {})

def get_prepoll(config: dict) -> dict:
    return get_schedule(config).get("prepoll", {})

def get_poll(config: dict) -> dict:
    return get_schedule(config).get("poll", {})

def get_end(config: dict) -> dict:
    return get_schedule(config).get("end", {})
