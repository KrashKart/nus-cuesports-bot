import datetime

DAYS = {"sunday": "0",
        "monday": "1",
        "tuesday": "2",
        "wednesday": "3",
        "thursday": "4",
        "friday": "5",
        "saturday": "6"
        }

def is_valid_time(time_str: str) -> bool:
    try:
        datetime.datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def is_valid_day(day_str: str) -> bool:
    return day_str.lower() in DAYS.keys()

def convert_to_ampm(time_str: str) -> str:
    dt = datetime.datetime.strptime(time_str, "%H:%M")
    return dt.strftime("%-I.%M%p").lower()
    