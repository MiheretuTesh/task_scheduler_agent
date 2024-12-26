import json
from .utils import model

def get_task_analysis(task, existing_events):
    events_summary = "\n".join([
        f"Event: {event['summary']}, Time: {event['start']['dateTime']} to {event['end']['dateTime']}"
        for event in existing_events
    ])
    
    prompt = f"""
    Analyze this task and provide scheduling recommendations considering:
    1. Existing calendar events for next week: {events_summary}
    2. Task deadline: {task['deadline']}
    3. Working hours: 9 AM - 5 PM
    4. Lunch break: 12 PM - 1 PM
    
    Task details:
    Title: {task['title']}
    Description: {task['description']}
    Priority: {task['priority']}
    Category: {task['category']}
    
    Provide ONLY these three fields in JSON:
    duration_hours: (number between 1-8)
    best_time: (exactly "morning", "afternoon", or "evening")
    importance: (number between 1-5)
    """
    
    response = model.generate_content(prompt)
    response_text = response.text.strip()
    return json.loads(response_text[response_text.find('{'):response_text.rfind('}')+1])