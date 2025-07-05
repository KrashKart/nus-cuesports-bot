from google.cloud import scheduler_v1
from google.protobuf import timestamp_pb2
from utils.gcs_utils import save_json_file_to_gcs
from dotenv import load_dotenv
import logging
import os

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION_ID = os.getenv("LOCATION_ID")

def create_or_update_scheduler_job(schedule_type, day, time, job_name, schedules):
    client = scheduler_v1.CloudSchedulerClient()
    parent = f'projects/{PROJECT_ID}/locations/{LOCATION_ID}'

    # Convert day and time to cron expression
    hour, minute = time.split(":")
    day_of_week = {
        "sunday": "0",
        "monday": "1",
        "tuesday": "2",
        "wednesday": "3",
        "thursday": "4",
        "friday": "5",
        "saturday": "6"
    }.get(day.lower(), "*")

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
        job_exists = False
        try:
            client.get_job(name=job['name'])
            job_exists = True
        except:
            pass

        if job_exists:
            if client.get_job(name=job['name']) == cron_expression:
                return
            client.update_job(job=job)
        else:
            client.create_job(parent=parent, job=job)
    except Exception as e:
        logger.error(f"Error creating/updating scheduler job: {e}")
        raise

def delete_scheduler_job(job_name):
    client = scheduler_v1.CloudSchedulerClient()
    
    name = f'projects/{PROJECT_ID}/locations/{LOCATION_ID}/jobs/{job_name}'
    
    try:
        client.delete_job(name=name)
        print(f'Job {job_name} deleted successfully.')
    except Exception as e:
        print(f'Error deleting job: {e}')
        raise

def update_schedule(bot, message, schedules, config, ADMIN_GROUP):
    if message.chat.id == ADMIN_GROUP:
        try:
            command_params = message.text.split()
            if len(command_params) < 4:
                bot.send_message(message.chat.id, "Usage: /update_schedule <prepoll/poll/end> <day> <time>")
                return
            
            if (schedule_type := command_params[1]) not in ["prepoll", "poll", "end"]:
                bot.send_message(message.chat.id, "Invalid schedule type. Use 'prepoll', 'poll', or 'end'.")
                return
            
            schedule_type, day, time = command_params[1], command_params[2], command_params[3]
            if schedule_type not in ["prepoll", "poll", "end"]:
                bot.send_message(message.chat.id, "Invalid schedule type. Use 'prepoll', 'poll', or 'end'.")
                return

            if schedule_type == "end":
                schedules["poll"]["end"]["day"] = day
                schedules["poll"]["end"]["time"] = time
            else:
                schedules[schedule_type]["day"] = day
                schedules[schedule_type]["time"] = time
            
            # Update Cloud Scheduler job
            job_name = f'{schedule_type}_job'
            create_or_update_scheduler_job(schedule_type, day, time, job_name, schedules)

            config["schedules"] = schedules
            save_json_file_to_gcs("config.json", config)
            bot.send_message(message.chat.id, f"Schedule updated: {schedule_type} on {day} at {time}")

        except Exception as e:
            bot.send_message(message.chat.id, f"Error updating schedule: {e}")
            logger.error(f"Error updating schedule: {e}")

def send_current_schedule(bot, message, schedules, ADMIN_GROUP):
    if message.chat.id == ADMIN_GROUP:
        schedule_info = f"<blockquote><b>Current Schedule:</b></blockquote>\n"
        for key, value in schedules.items():
            if key == "poll" and "end" in value:
                schedule_info += f"<b>{key.capitalize()}:</b> {value['day']}, {value['time']}\n<b>End:</b> {value['end']['day']}, {value['end']['time']}\n"
            else:
                schedule_info += f"<b>{key.capitalize()}:</b> {value['day']}, {value['time']}\n"
        bot.send_message(message.chat.id, schedule_info, parse_mode='HTML')