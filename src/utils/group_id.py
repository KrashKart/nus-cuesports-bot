def get_admin(groups: dict) -> int:
    return groups.get("ADMIN_GROUP", {}).get("id", None)

def get_recre(groups: dict) -> int:
    return groups.get("RECRE_GROUP", {}).get("id", None)

def get_log(groups: dict) -> int:
    return groups.get("ADMIN_GROUP", {}).get("id", None)