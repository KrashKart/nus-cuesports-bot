###########################
# Groups
###########################
def get_groups(config: dict) -> dict:
    return config.get("groups", {})

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
    return config.get("super_users", [])

def get_super_users_id(config: dict) -> list:
    return list(map(lambda x: x["id"], get_super_users(config)))

###########################
# Scheduling
###########################
def get_schedule(config: dict) -> dict:
    return config.get("schedules", {})

def get_prepoll(config: dict) -> dict:
    return get_schedule(config).get("prepoll", {})

def get_poll(config: dict) -> dict:
    return get_schedule(config).get("poll", {})

def get_end(config: dict) -> dict:
    return get_schedule(config).get("end", {})

def get_ping(config: dict) -> dict:
    return get_schedule(config).get("ping", {})
