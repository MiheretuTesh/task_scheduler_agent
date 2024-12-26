import streamlit as st
from .utils import get_google_creds, get_existing_calendar_events, schedule_single_task, analyze_and_schedule_tasks
from .task_analysis import get_task_analysis
import gspread
import datetime
from googleapiclient.discovery import build
import pytz
import os

def single_task_scheduler():
    st.header("Schedule Individual Task")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("task_form"):
            title = st.text_input("Task Title")
            description = st.text_area("Description")
            priority = st.select_slider("Priority", options=["Low", "Medium", "High"])
            category = st.text_input("Category")
            deadline = st.date_input("Deadline")
            timezone = st.selectbox("Timezone", pytz.common_timezones)
            
            submit_button = st.form_submit_button("Analyze Task")
            
            if submit_button:
                task = {
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "category": category,
                    "deadline": deadline.strftime("%Y-%m-%d"),
                    "timezone": timezone
                }
                
                with st.spinner("Analyzing task..."):
                    analysis = get_task_analysis(task, [])
                    st.session_state.current_analysis = analysis
                    st.session_state.current_task = task

    with col2:
        if 'current_analysis' in st.session_state:
            st.subheader("Task Analysis")
            st.json(st.session_state.current_analysis)
            
            if st.button("Schedule This Task"):
                with st.spinner("Scheduling..."):
                    schedule_single_task(st.session_state.current_task, 
                                      st.session_state.current_analysis)
                st.success("Task scheduled successfully! 🎉")

def batch_scheduler():
    st.header("Batch Schedule Tasks")
    
    if st.button("Load and Schedule All Tasks"):
        with st.spinner("Processing tasks from spreadsheet..."):
            try:
                creds = get_google_creds()
                gc = gspread.authorize(creds)
                tasks = gc.open_by_key(os.getenv('SPREADSHEET_ID')).sheet1.get_all_records()
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, task in enumerate(tasks):
                    status_text.text(f"Processing task {idx + 1}/{len(tasks)}: {task['title']}")
                    progress_bar.progress((idx + 1) / len(tasks))
                
                results = analyze_and_schedule_tasks(tasks)
                
                st.success(f"Successfully scheduled {results['total_tasks_scheduled']} tasks")
                
                with st.expander("View Scheduled Tasks"):
                    for task in results['scheduled_tasks']:
                        st.write(f"📅 {task['task']['title']} - {task['scheduled_time']}")
                        
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

def calendar_viewer():
    st.header("Calendar Overview")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        days_ahead = st.slider("Days to view", 1, 30, 7)
    
    try:
        calendar_service = build('calendar', 'v3', credentials=get_google_creds())
        start_date = datetime.datetime.now(datetime.timezone.utc)
        end_date = start_date + datetime.timedelta(days=days_ahead)
        
        events = get_existing_calendar_events(calendar_service, start_date, end_date)
        
        events_by_date = {}
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            date = start.split('T')[0]
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)
        
        for date in sorted(events_by_date.keys()):
            st.subheader(f"📅 {date}")
            for event in events_by_date[date]:
                start_time = event['start'].get('dateTime', '').split('T')[1][:5]
                st.write(f"🕒 {start_time} - {event['summary']}")
                with st.expander("Details"):
                    st.write(event.get('description', 'No description available'))
                    
    except Exception as e:
        st.error(f"Could not load calendar: {str(e)}")