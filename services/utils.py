import os
import datetime
import pytz
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import google.generativeai as genai

# Initialize Gemini AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly', 'https://www.googleapis.com/auth/calendar']
PRIORITY_COLORS = {'High': '11', 'Medium': '5', 'Low': '2'}
PRIORITY_HOURS = {
    'high': [9, 10, 14, 15, 16],
    'medium': [8, 11, 13, 17],
    'low': [7, 12, 18, 19]
}

def get_google_creds():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def check_calendar_availability(calendar_service, start_time, end_time):
    if start_time <= datetime.datetime.now(datetime.timezone.utc):
        return False
    events = calendar_service.events().list(
        calendarId='primary',
        timeMin=start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        timeMax=end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return len(events.get('items', [])) == 0

def get_existing_calendar_events(calendar_service, start_date, end_date):
    events = calendar_service.events().list(
        calendarId='primary',
        timeMin=start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        timeMax=end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events.get('items', [])

def is_working_hours(time): return 9 <= time.hour <= 17
def is_lunch_time(time): return 12 <= time.hour <= 13
def is_weekend(time): return time.weekday() >= 5
def get_event_color(priority): return PRIORITY_COLORS.get(priority, '1')

def schedule_single_task(task, analysis):
    calendar_service = build('calendar', 'v3', credentials=get_google_creds())
    now = datetime.datetime.now()
    
    start_time = now.replace(
        hour=9 if analysis['best_time'].lower() == 'morning'
        else 13 if analysis['best_time'].lower() == 'afternoon'
        else 17
    )
    
    end_time = start_time + datetime.timedelta(hours=analysis['duration_hours'])
    
    event = calendar_service.events().insert(
        calendarId='primary',
        body={
            'summary': task['title'],
            'description': task['description'],
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'UTC'},
            'colorId': get_event_color(task['priority'])
        }
    ).execute()
    
    return event

def analyze_and_schedule_tasks(tasks):
    creds = get_google_creds()
    calendar_service = build('calendar', 'v3', credentials=creds)
    
    tasks.sort(key=lambda x: (x['deadline'], x['priority'] == 'High', x['priority'] == 'Medium'))
    start_date = datetime.datetime.now(datetime.timezone.utc)
    end_date = start_date + datetime.timedelta(days=30)
    existing_events = get_existing_calendar_events(calendar_service, start_date, end_date)
    
    scheduled_tasks = []
    
    for task in tasks:
        task_tz = pytz.timezone(task['timezone'])
        current_time = datetime.datetime.now(task_tz)
        deadline = datetime.datetime.strptime(task['deadline'], '%Y-%m-%d').replace(tzinfo=task_tz)
        
        if deadline < current_time:
            continue
            
        analysis = get_task_analysis(task, existing_events)
        start_date = current_time + datetime.timedelta(minutes=30)
        
        for day_offset in range(14):
            if len([t for t in scheduled_tasks if t['task'] == task]):
                break
                
            test_date = start_date + datetime.timedelta(days=day_offset)
            if test_date > deadline.replace(hour=23, minute=59):
                break
            
            possible_times = PRIORITY_HOURS[task['priority'].lower()]
            
            for hour in possible_times:
                start_time = test_date.replace(hour=hour, minute=0)
                end_time = start_time + datetime.timedelta(hours=analysis['duration_hours'])
                
                if task['priority'].lower() != 'high' and (is_weekend(start_time) or is_lunch_time(start_time)):
                    continue
                
                if check_calendar_availability(calendar_service, start_time, end_time):
                    event = calendar_service.events().insert(
                        calendarId='primary',
                        body={
                            'summary': f"{task['title']} ({task['priority']})",
                            'description': f"{task['description']}\nCategory: {task['category']}\nDeadline: {task['deadline']}",
                            'start': {'dateTime': start_time.isoformat(), 'timeZone': task['timezone']},
                            'end': {'dateTime': end_time.isoformat(), 'timeZone': task['timezone']},
                            'colorId': get_event_color(task['priority'])
                        }
                    ).execute()
                    
                    scheduled_tasks.append({
                        "task": task,
                        "analysis": analysis,
                        "event": event,
                        "scheduled_time": start_time.isoformat()
                    })
                    existing_events = get_existing_calendar_events(calendar_service, start_date, end_date)
                    break
    
    return {
        "status": "success",
        "scheduled_tasks": scheduled_tasks,
        "total_tasks_scheduled": len(scheduled_tasks),
        "unscheduled_tasks": len(tasks) - len(scheduled_tasks)
    }