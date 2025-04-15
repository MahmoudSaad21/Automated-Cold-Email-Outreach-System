import streamlit as st
import subprocess
import threading
import time
import sqlite3
import pandas as pd

# Function to run scripts
def run_script(script_name):
    subprocess.run(['python', script_name])

# Background thread for event-driven emails
def run_event_driven_emails():
    while True:
        subprocess.run(['python', 'event_driven_emails.py'])
        time.sleep(60)  # Check every 60 seconds

# Run first_sent.py once at startup
if 'first_sent_done' not in st.session_state:
    run_script('first_sent.py')
    st.session_state.first_sent_done = True

# Start event-driven emails in a background thread if not already running
if 'email_thread_started' not in st.session_state:
    threading.Thread(target=run_event_driven_emails, daemon=True).start()
    st.session_state.email_thread_started = True

# Streamlit App Layout
st.title("Cold Email Automation System")

# Containers for dynamic updates
sent_placeholder = st.empty()
received_placeholder = st.empty()

def fetch_and_display_emails():
    conn = sqlite3.connect('emails.db')
    try:
        sent_emails = pd.read_sql_query("SELECT * FROM emails WHERE category='sent'", conn)
        received_emails = pd.read_sql_query("SELECT * FROM emails WHERE category='received'", conn)

        # Display Sent Emails
        with sent_placeholder.container():
            st.subheader("📤 Sent Emails")
            st.dataframe(sent_emails, use_container_width=True)

        # Display Received Emails
        with received_placeholder.container():
            st.subheader("📥 Received Emails")
            st.dataframe(received_emails, use_container_width=True)

    except Exception as e:
        st.warning(f"Error fetching emails from database: {e}")
    finally:
        conn.close()

# Periodically refresh the email tables
while True:
    fetch_and_display_emails()
    time.sleep(10)  # Refresh every 5 seconds
