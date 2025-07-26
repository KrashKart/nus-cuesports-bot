from google.cloud import scheduler_v1
from google.api_core.exceptions import NotFound
from utils.gcs_utils import save_json_file_to_gcs
from utils.datetime_utils import is_valid_day, is_valid_time, DAYS
from dotenv import load_dotenv
import logging, os

from telebot import TeleBot
from telebot.types import Message

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION_ID = os.getenv("LOCATION_ID")

def create_or_update_scheduler_job(schedule_type: str, day: str, time: str, job_name: str) -> None:
    client = scheduler_v1.CloudSchedulerClient()
    parent = f'projects/{PROJECT_ID}/locations/{LOCATION_ID}'

    # Convert day and time to cron expression
    hour, minute = time.split(":")
    day_of_week = DAYS.get(day.lower(), "*")

    cron_expression = f'{minute} {hour} * * {day_of_week}'

    job = {
        'name': f'{parent}/jobs/{job_name}',
        'schedule': cron_expression,
        'time_zone': 'Asia/Singapore',
        'http_target': {
            'uri': f'{os.getenv("SCHEDULER_URL")}/{schedule_type}',
            'http_method': scheduler_v1.HttpMethod.POST,
        },
    }

    # Create or update the job
    try:
        if client.get_job(name=job['name']).schedule != cron_expression:
            client.update_job(job=job)
    except NotFound:
        client.create_job(parent=parent, job=job)
    except Exception as e:
        logger.error(f"Error creating/updating scheduler job: {e}")
        raise

def delete_scheduler_job(job_name: str) -> None:
    client = scheduler_v1.CloudSchedulerClient()
    
    name = f'projects/{PROJECT_ID}/locations/{LOCATION_ID}/jobs/{job_name}'
    
    try:
        client.delete_job(name=name)
        print(f'Job {job_name} deleted successfully.')
    except Exception as e:
        print(f'Error deleting job: {e}')
        raise

def update_schedule(bot: TeleBot, message: Message, schedules: dict, config: dict, ADMIN_GROUP: str | int) -> None:
    if message.chat.id == ADMIN_GROUP:
        try:
            command_params = message.text.split()
            if len(command_params) != 4:
                bot.send_message(message.chat.id, "Usage: /update_schedule <prepoll/poll/end> <day> <time>")
                return
            
            schedule_type, day, time = command_params[1], command_params[2], command_params[3]
            if schedule_type not in ["prepoll", "poll", "end"]:
                bot.send_message(message.chat.id, "Invalid schedule type. Use 'prepoll', 'poll', or 'end'.")
                return
            elif not is_valid_day(day):
                bot.send_message(message.chat.id, "Invalid day. Use 'sunday', 'monday', etc (Lower/Upper case both accepted).")
                return
            elif not is_valid_time(time):
                bot.send_message(message.chat.id, "Invalid time. Time should be in format 'HH:MM'.")
                return

            if schedule_type == "end":
                schedules["poll"]["end"]["day"] = day
                schedules["poll"]["end"]["time"] = time
            else:
                schedules[schedule_type]["day"] = day
                schedules[schedule_type]["time"] = time
            
            # Update Cloud Scheduler job
            job_name = f'{schedule_type}_job'
            create_or_update_scheduler_job(schedule_type, day, time, job_name)

            config["schedules"] = schedules
            save_json_file_to_gcs("config.json", config)
            bot.send_message(message.chat.id, f"Schedule updated: {schedule_type.capitalize()} on {day.capitalize()}, {time}")

        except Exception as e:
            bot.send_message(message.chat.id, f"Error updating schedule: {e}")
            logger.error(f"Error updating schedule: {e}")

def send_current_schedule(bot: TeleBot, message: Message, schedules: dict, ADMIN_GROUP: int) -> None:
    if message.chat.id == ADMIN_GROUP:
        schedule_info = f"<blockquote><b>Current Schedule:</b></blockquote>\n"
        for key, value in schedules.items():
            if key == "poll" and "end" in value:
                schedule_info += f"<b>{key.capitalize()}:</b> {value['day'].capitalize()}, {value['time']}\n<b>Poll End:</b> {value['end']['day'].capitalize()}, {value['end']['time']}\n"
            else:
                schedule_info += f"<b>{key.capitalize()}:</b> {value['day'].capitalize()}, {value['time']}\n"
        bot.send_message(message.chat.id, schedule_info, parse_mode='HTML')
        