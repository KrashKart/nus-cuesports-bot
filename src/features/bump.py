import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Path to your downloaded service account key
SERVICE_ACCOUNT_FILE = 'service-account.json'  # Place this in your project folder

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Define the Sheet ID and range
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
RANGE_NAME = "Form Responses 1!E:E"

def read_paid_telegrams(bot, message, admin_group):
    if message.chat.id == admin_group:
        # Authenticate
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )

        # Connect to Sheets API
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()

        # Read data
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = list(map(lambda x: x[1:] if x.startswith("@") else x, result.get('values', [])))

        bot.send_message(admin_group, "\n".join(values))