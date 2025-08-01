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

# not in use i think
def datetime_to_cron(day: str, time: str) -> str:
    hour, minute = time.split(":")
    day_of_week = DAYS.get(day.lower(), "*")
    return f'{minute} {hour} * * {day_of_week}'
    