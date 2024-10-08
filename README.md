# **On-Call Schedule Sync with Google Calendar**
This script synchronizes on-call schedules from Opsgenie to a Google Calendar. It fetches schedules from Opsgenie and updates a specified Google Calendar with events representing on-call rotations.

## **Features**

- Multiple Rotations: Supports syncing multiple on-call rotations into a single Google Calendar.
- Event Coloring: Assigns different colors to events based on the rotation.
- Time Range Filtering: Syncs events starting from 3 days in the past up to 90 days in the future.
- Encoding Handling: Corrects encoding issues to properly display special characters in event summaries.
- Automated Scheduling: Can be set up to run daily using CI/CD.

## **Prerequisites**

- Python: Version 3.7 or higher.
- Google Cloud Project: With a service account and Google Calendar API enabled.
- Opsgenie Account: With API access and appropriate permissions.
- GitLab CI/CD: For scheduling the script.

## **Setting Variables Locally**

```
export OPS_GENIE_API_KEY='your_opsgenie_api_key'
export SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
export CALENDAR_ID='your_calendar_id@group.calendar.google.com'
export CALENDAR_1_SCHEDULE_ID='your_goalkeeper_schedule_id'
export CALENDAR_2_SCHEDULE_ID='your_alert_troubleshooter_schedule_id'
export CALENDAR_3_SCHEDULE_ID='your_on_call_schedule_id'
```
