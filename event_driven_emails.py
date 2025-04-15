import imaplib
import email
import time
import sqlite3
import subprocess
import json
from email.header import decode_header
import psutil  # To check if the external script is running
import time
import random
import smtplib
import os
import sqlite3
import PyPDF2
import numpy as np
import faiss
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# Email credentials
EMAIL_USER = "your_email"
EMAIL_PASSWORD = "your_gmail_password"  # Use an app password if required
IMAP_SERVER = "imap.gmail.com"

# SQLite database path
SQLITE_DB = "emails.db"
TEMP_FILE = "temp_emails.json"  # Temporary file for email list
QUEUE_FILE = "email_queue.json"   # ✅ Queue file for pending emails
PROCESS_SCRIPT = "response.py"  # External script to handle emails

# Connect to SQLite database
conn = sqlite3.connect(SQLITE_DB)
cursor = conn.cursor()

# Create emails table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'sent' or 'received'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# ✅ Check if the response.py script is running
def is_process_running(script_name):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if script_name in proc.info['cmdline']:
            return True
    return False

# ✅ Add emails to the queue
def add_to_queue(email_list):
    with open(QUEUE_FILE, "r") as file:
        queue = json.load(file)

    queue.extend(email_list)

    with open(QUEUE_FILE, "w") as file:
        json.dump(queue, file)

    print(f"Queued {len(email_list)} emails.")

# ✅ Process emails from the queue
def process_queue():
    with open(QUEUE_FILE, "r") as file:
        queued_emails = json.load(file)

    if queued_emails:
        print(f"Processing {len(queued_emails)} queued emails...")
        send_emails_to_script(queued_emails)

        # Clear the queue after processing
        with open(QUEUE_FILE, "w") as file:
            json.dump([], file)


def mark_email_as_read(mail, email_id):
    """Mark the email as read."""
    mail.store(email_id, '+FLAGS', '\\Seen')

def fetch_unread_emails():
    """Fetch unread emails from the inbox."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select("inbox")  # Select inbox

        # Search for unread emails
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        if not email_ids:
            print("No new emails found.")
            mail.logout()
            return []

        EMAIL_LIST = []  # Store extracted email addresses
        for num in reversed(email_ids):  # Process from latest to oldest
            status, data = mail.fetch(num, "(RFC822)")
            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Decode email subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else 'utf-8')

                    # Get sender email
                    from_email = msg.get("From")
                    from_email = from_email.split("<")[-1].strip(">")  # Extract clean email
                    EMAIL_LIST.append(from_email)

                    # Get email body
                    body = ""
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition") or "")

                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break  # Stop after getting the plain text part

                    if not body:
                        continue  # Skip if no body found
                    print(f"\nNew Email from {from_email}: {subject}")

                    # ✅ Check if the sender exists in the contacts table
                    cursor.execute('SELECT * FROM emails WHERE email = ?', (from_email,))
                    contact = cursor.fetchone()

                    if contact:  # ✅ Insert only if the sender exists in the database
                        company_name = contact[1] if len(contact) > 1 else "Unknown Company"

                        # ✅ Insert the received email into the SQLite database
                        cursor.execute('''
                            INSERT INTO emails (company_name, email, subject, message, category)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (company_name, from_email, subject, body, 'received'))
                        conn.commit()

                        # ✅ Mark email as read only for known senders
                        mark_email_as_read(mail, num)
                    else:
                        print(f"Skipped email from unknown sender: {from_email}")

        mail.logout()
        return EMAIL_LIST  # Return the list of emails

    except Exception as e:
        print("Error:", e)
        return []

def send_emails_to_script(email_list):
    """Pass the list of emails to another script (process_emails.py)."""
    if email_list:
        print(f"Passing {len(email_list)} emails to {PROCESS_SCRIPT}...")

        # Save email list to a temporary file
        with open(TEMP_FILE, "w") as file:
            json.dump(email_list, file)

        # Run the external script with the file path as an argument
        subprocess.Popen(["python", PROCESS_SCRIPT, TEMP_FILE])

# Ensure the queue file exists
if not os.path.exists(QUEUE_FILE):
    with open(QUEUE_FILE, "w") as file:
        json.dump([], file)  # Initialize with an empty list


# Run the script continuously every 60 seconds
while True:
    emails = fetch_unread_emails()

    # Check the size of the email queue
    with open(QUEUE_FILE, "r") as file:
        queue_size = len(json.load(file))

    if emails or queue_size != 0:
        if is_process_running(PROCESS_SCRIPT):
            # Add new emails to the queue if the process is running
            add_to_queue(emails)
        elif emails and queue_size != 0:
            # Process queued emails first, then send new emails
            process_queue()
            send_emails_to_script(emails)
        elif emails:
            # Send new emails directly if there's no queue
            send_emails_to_script(emails)
        elif queue_size != 0:
            # Process queued emails if no new emails are found
            process_queue()
    time.sleep(60)