import requests
import logging
import re
import hashlib
from datetime import datetime, timezone, timedelta
from icalendar import Calendar
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json

API_URL = "https://api.eu.opsgenie.com"
SCOPES = ['https://www.googleapis.com/auth/calendar']

OPS_GENIE_API_KEY = os.environ.get('OPS_GENIE_API_KEY')
if OPS_GENIE_API_KEY is None:
    raise ValueError('OPS_GENIE_API_KEY environment variable is not set')

HEADERS = {
    'Authorization': f'GenieKey {OPS_GENIE_API_KEY}'
}

def get_calendar_service():
    SERVICE_ACCOUNT_JSON = os.environ.get('SERVICE_ACCOUNT_JSON')
    if SERVICE_ACCOUNT_JSON is None:
        raise ValueError('SERVICE_ACCOUNT_JSON environment variable is not set')
    service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    return service

def fix_encoding(text):
    try:
        return text.encode('latin1').decode('utf-8')
    except UnicodeError:
        return text

def get_ics_schedule(schedule_id):
    url = f'https://api.eu.opsgenie.com/v2/schedules/{schedule_id}.ics'
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.text

def parse_ics_data(ics_data):
    cal = Calendar.from_ical(ics_data)
    events = []
    for component in cal.walk():
        if component.name == "VEVENT":
            start = component.get('dtstart').dt
            end = component.get('dtend').dt
            # Ensure datetime objects are timezone-aware
            if isinstance(start, datetime):
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                else:
                    start = start.astimezone(timezone.utc)
            if isinstance(end, datetime):
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                else:
                    end = end.astimezone(timezone.utc)
            # Extract UID and Summary with proper decoding
            uid = component.get('uid').to_ical().decode('utf-8')
            summary_bytes = component.get('summary').to_ical()
            # Try decoding the summary correctly
            try:
                summary = summary_bytes.decode('utf-8')
            except UnicodeDecodeError:
                summary = summary_bytes.decode('latin1')
            # Fix encoding issues
            summary = fix_encoding(summary)
            event = {
                'uid': uid,
                'summary': summary,
                'start': start,
                'end': end
            }
            events.append(event)
    return events

def sanitize_event_id(uid):
    # Create a SHA256 hash of the UID
    hash_object = hashlib.sha256(uid.encode('utf-8'))
    hex_dig = hash_object.hexdigest()
    # Truncate to meet length requirements
    event_id = hex_dig[:1024]
    return event_id

def create_or_update_event(service, calendar_id, event, color_id=None):
    event_id = sanitize_event_id(event['uid'])
    event_body = {
        'summary': event['summary'],
        'start': {
            'dateTime': event['start'].isoformat(),
            'timeZone': 'UTC'  # Adjust if necessary
        },
        'end': {
            'dateTime': event['end'].isoformat(),
            'timeZone': 'UTC'  # Adjust if necessary
        }
    }
    if color_id:
        event_body['colorId'] = color_id
    try:
        # Try to get the event; if it exists, update it
        service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        event_body['id'] = event_id  # Include ID when updating
        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()
        print(f"Updated event: {updated_event['summary']} (ID: {event_id})")
    except HttpError as error:
        if error.resp.status == 404:
            # Create event with the ID
            event_body['id'] = event_id
            try:
                created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
                print(f"Created event: {created_event['summary']} (ID: {event_id})")
            except HttpError as insert_error:
                print(f"Error inserting event with ID {event_id}: {insert_error}")
                raise
        else:
            print(f"Error accessing event with ID {event_id}: {error}")
            raise

def delete_all_events_since_past_days(service, calendar_id, days=3):
    start_time = datetime.now(timezone.utc) - timedelta(days=days)
    page_token = None
    while True:
        events = service.events().list(
            calendarId=calendar_id,
            pageToken=page_token,
            timeMin=start_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        for event in events.get('items', []):
            try:
                service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
                print(f"Deleted event: {event.get('summary', 'No Title')} (ID: {event['id']})")
            except HttpError as error:
                print(f"An error occurred deleting event {event['id']}: {error}")
        page_token = events.get('nextPageToken')
        if not page_token:
            break

def main():
    service = get_calendar_service()
    # Get calendar ID from environment variable
    calendar_id = os.environ.get('CALENDAR_ID')
    if calendar_id is None:
        raise ValueError('CALENDAR_ID environment variable is not set')
    # Delete events starting from 3 days ago
    delete_all_events_since_past_days(service, calendar_id, days=3)
    # Define the schedules with their names and IDs
    schedules = {
        'CALENDAR_1': os.environ.get('CALENDAR_1_SCHEDULE_ID'),
        'CALENDAR_2': os.environ.get('CALENDAR_2_SCHEDULE_ID'),
        'CALENDAR_3': os.environ.get('CALENDAR_3_SCHEDULE_ID')
    }
    # Ensure all schedule IDs are set
    for name, schedule_id in schedules.items():
        if schedule_id is None:
            raise ValueError(f"{name} schedule ID environment variable is not set")
    # Define the mapping of schedule names to color IDs
    schedule_colors = {
        'CALENDAR_1': '5',  # Citron (Banana)
        'CALENDAR_2': '8',  # Cocoa (Graphite)
        'CALENDAR_3': '11'  # Tomato
    }
    start_time = datetime.now(timezone.utc) - timedelta(days=3)
    ninety_days_ahead = start_time + timedelta(days=93)  # 90 days ahead from today
    for rotation_name, schedule_id in schedules.items():
        ics_data = get_ics_schedule(schedule_id)
        events = parse_ics_data(ics_data)
        color_id = schedule_colors.get(rotation_name, None)
        for event in events:
            # Include events starting from 3 days ago
            if event['start'] < start_time or event['start'] > ninety_days_ahead:
                continue
            event['summary'] = f"{rotation_name}: {event['summary']}"
            create_or_update_event(service, calendar_id, event, color_id)

if __name__ == '__main__':
    main()
