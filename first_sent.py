import time
import random
import smtplib
import os
import pandas as pd
import PyPDF2
import torch
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import re
import sqlite3

# Gmail SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# Your Gmail Credentials (Use App Password, NOT Gmail password)
sender_email = "your_email"
app_password = "your_gmail_password"

# File paths
csv_file = "VR_and_Software_Companies_2.csv"
pdf_file = "detailed_product_catalog.pdf"

model = pipeline("text-generation", model="meta-llama/Llama-3.2-3B-Instruct", torch_dtype=torch.bfloat16, device_map="auto")

sender_name = "Mahmoud Saad"
sender_company = "Freeland"

# Read CSV containing company details
companies_df = pd.read_csv(csv_file)

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('emails.db')
cursor = conn.cursor()

# Create a table to store emails
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

def extract_subject_and_body(conversation):
    # Find the assistant's response
    assistant_response = next((item for item in conversation if item.get('role') == 'assistant'), None)

    if assistant_response:
        response_text = assistant_response.get('content', '')
    else:
        return "No Subject", "No Content"

    # Extract subject
    subject_match = re.search(r"Subject:\s*(.*)", response_text, re.IGNORECASE)
    subject = subject_match.group(1).strip() if subject_match else "No Subject"

    # Extract body: captures everything after the first "Subject" line
    body_match = re.search(r"Subject:.*?\n+(.*)", response_text, re.DOTALL)
    email_body = body_match.group(1).strip() if body_match else response_text.strip()

    return subject, email_body

# Extract product information from PDF
def extract_products_from_pdf(pdf_path):
    products = []
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

        lines = text.split("\n")
        for i in range(len(lines)):
            if "Product:" in lines[i]:
                product_name = lines[i].replace("Product: ", "").strip()
                industry = lines[i + 1].replace("Industry: ", "").strip()
                description = lines[i + 2].replace("Description: ", "").strip()
                specifications = lines[i + 3].replace("Specifications: ", "").strip()
                case_study = lines[i + 4].replace("Case Study: ", "").strip()
                compliance = lines[i + 5].replace("Compliance: ", "").strip()
                products.append({
                    "Product Name": product_name,
                    "Industry": industry,
                    "Description": description,
                    "Specifications": specifications,
                    "Case Study": case_study,
                    "Compliance": compliance
                })
    return products

product_list = extract_products_from_pdf(pdf_file)

# Load Sentence Transformer model for embeddings
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Create FAISS index for product descriptions
def create_faiss_index(products):
    descriptions = [p['Description'] for p in products]
    embeddings = embedder.encode(descriptions)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))
    return index, descriptions

faiss_index, product_descriptions = create_faiss_index(product_list)

# Function to find relevant products using embeddings
def find_relevant_products(need, top_k=3):
    need_embedding = embedder.encode([need])
    distances, indices = faiss_index.search(np.array(need_embedding), top_k)
    return [product_list[i] for i in indices[0]]

# Function to generate customized email and subject using LLM
def generate_email_and_subject(company_name, industry, need):
    relevant_products = find_relevant_products(need)
    product_suggestions = "\n".join([f"- {p['Product Name']}: {p['Description']}" for p in relevant_products])

    messages = [
        {"role": "system", "content": "You are a professional email assistant specializing in crafting compelling and structured business emails."},
        {"role": "user", "content": f"Generate a professional email with a compelling subject for {company_name} team in a company in {company_name}, a company in the {industry} industry.\n\nThe company has expressed a need for {need}, and we offer the following relevant products:\n\n{product_suggestions}\n\nThe email should include:\n- A relevant subject line\n- A personalized greeting\n- A concise, engaging introduction\n- A brief mention of the relevant products\n- A clear call to action for scheduling a discussion or demo\n- A professional closing with the sender's name ({sender_name}) and company ({sender_company})\n\nRespond with only the email subject and body."}
    ]

    output = model(messages, max_new_tokens=512)[0]['generated_text']
    print(output)
    subject, email_body = extract_subject_and_body(output)
    torch.cuda.empty_cache()

    print(subject)
    return subject, email_body

# Function to send email and log it
def send_email(to_email, company_name, industry, need):
    try:
        subject, email_body = generate_email_and_subject(company_name, industry, need)

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(email_body, "plain"))

        with open(pdf_file, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(pdf_file)}")
        message.attach(part)

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, to_email, message.as_string())

        # Log the sent email in the SQLite database
        cursor.execute('''
        INSERT INTO emails (company_name, email, subject, message, category)
        VALUES (?, ?, ?, ?, ?)
        ''', (company_name, to_email, subject, email_body, 'sent'))

        conn.commit()

    except Exception as e:
        print(f"❌ Error sending email to {company_name} ({to_email}): {e}")

# Function to store received emails
def store_received_email(company_name, email, subject, message):
    cursor.execute('''
    INSERT INTO emails (company_name, email, subject, message, category)
    VALUES (?, ?, ?, ?, ?)
    ''', (company_name, email, subject, message, 'received'))

    conn.commit()

# Function to retrieve emails
def get_emails(category=None):
    if category:
        cursor.execute('SELECT * FROM emails WHERE category = ?', (category,))
    else:
        cursor.execute('SELECT * FROM emails')

    return cursor.fetchall()

# Send emails to all companies
for _, row in companies_df.iterrows():
    send_email(row["Email"], row["Company Name"], row["Industry"], row["Need"])

# Example usage:
sent_emails = get_emails(category='sent')
received_emails = get_emails(category='received')

print("Sent Emails:")
for email in sent_emails:
    print(email)

print("\nReceived Emails:")
for email in received_emails:
    print(email)

# Close the database connection
conn.close()