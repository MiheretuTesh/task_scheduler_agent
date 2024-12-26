import streamlit as st
from services.calendar_service import single_task_scheduler, batch_scheduler, calendar_viewer

st.set_page_config(page_title="Smart Task Scheduler", layout="wide")

def main():
    st.title("🗓️ Smart Task Scheduler")
    
    tab1, tab2, tab3 = st.tabs(["📝 Single Task", "📊 Batch Schedule", "📅 Calendar View"])
    
    with tab1:
        single_task_scheduler()
    
    with tab2:
        batch_scheduler()
    
    with tab3:
        calendar_viewer()

if __name__ == '__main__':
    main()