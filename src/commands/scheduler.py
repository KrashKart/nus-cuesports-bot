from google.cloud import scheduler_v1
from google.api_core.exceptions import NotFound
from utils.gcs_utils import save_json_file_to_gcs
from utils.datetime_utils import is_valid_day, is_valid_time, DAYS
from utils.config_interface import get_admin_id, get_schedule, get_prepoll, get_poll, get_end
from utils.permissions import _admin_group_perms, _log
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

# Unused
def delete_scheduler_job(job_name: str) -> None:
    client = scheduler_v1.CloudSchedulerClient()
    
    name = f'projects/{PROJECT_ID}/locations/{LOCATION_ID}/jobs/{job_name}'
    
    try:
        client.delete_job(name=name)
        print(f'Job {job_name} deleted successfully.')
    except Exception as e:
        print(f'Error deleting job: {e}')
        raise

@_log
@_admin_group_perms
def update_schedule(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    try:
        command_params = message.text.split()
        if len(command_params) != 4:
            bot.send_message(message.chat.id, "Usage: /update_schedule <prepoll/poll/end> <day> <time>")
            return
        
        schedule_type, day, time = command_params[1].lower(), command_params[2], command_params[3]
        if schedule_type not in ["prepoll", "poll", "end"]:
            bot.send_message(message.chat.id, "Invalid schedule type. Use 'prepoll', 'poll', or 'end'.")
            return
        elif not is_valid_day(day):
            bot.send_message(message.chat.id, "Invalid day. Use 'sunday', 'monday', etc (Lower/Upper case both accepted).")
            return
        elif not is_valid_time(time):
            bot.send_message(message.chat.id, "Invalid time. Time should be in format 'HH:MM'.")
            return

        get_schedule(config)[schedule_type]["day"] = day
        get_schedule(config)[schedule_type]["time"] = time
        
        # Update Cloud Scheduler job
        job_name = f'{schedule_type}_job'
        create_or_update_scheduler_job(schedule_type, day, time, job_name)

        save_json_file_to_gcs("config.json", config)
        bot.send_message(message.chat.id, f"Schedule updated: {schedule_type.capitalize()} on {day.capitalize()}, {time}")

    except Exception as e:
        bot.send_message(message.chat.id, f"Error updating schedule: {e}")
        logger.error(f"Error updating schedule: {e}")

@_log
@_admin_group_perms
def update_ping(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    try:
        command_params = message.text.split()
        if len(command_params) != 2:
            bot.send_message(message.chat.id, "Usage: /update_ping <interval_mins>")
            return
        elif not command_params[1].isdigit():
            bot.send_message(message.chat.id, "Ping interval in minutes must be an integer!")
            return
        
        ping_interval = command_params[1]

        day = get_schedule(config)["ping"]["day"]
        time_prefix = get_schedule(config)["ping"]["time"].split("/")[0]
        new_time = time_prefix + "/" + ping_interval
        get_schedule(config)["ping"]["time"] = new_time

        # Update Cloud Scheduler job
        job_name = f'ping_job'
        create_or_update_scheduler_job("ping", day, new_time, job_name)

        save_json_file_to_gcs("config.json", config)
        bot.send_message(message.chat.id, f"Schedule updated: Ping every {ping_interval} minutes.")

    except Exception as e:
        bot.send_message(message.chat.id, f"Error updating schedule: {e}")
        logger.error(f"Error updating schedule: {e}")

@_log
@_admin_group_perms
def send_current_schedule(bot: TeleBot, message: Message, messages: dict, config: dict) -> None:
    if message.chat.id == get_admin_id(config):
        schedule_info = f"<blockquote><b>Current Schedule:</b></blockquote>\n"
        for key, value in get_schedule(config).items():
            schedule_info += f"<b>{key.capitalize()}:</b> {value['day'].capitalize()}, {value['time']}\n"
        bot.send_message(message.chat.id, schedule_info, parse_mode='HTML')
        