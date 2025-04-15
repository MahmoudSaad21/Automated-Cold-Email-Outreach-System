import smtplib
import os
import json
import sqlite3
import PyPDF2
import numpy as np
import faiss
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import torch
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import psutil  # To check if the external script is running
import time
import random
# File paths and email details
SQLITE_DB = "emails.db"
pdf_file = "detailed_product_catalog.pdf"
json_file = "temp_emails.json"
sender_email = "your_email"
app_password = "your_gmail_password"
sender_name = "Mahmoud Saad"
sender_company = "Freelance"

# Load email list from JSON file
with open(json_file, "r") as file:
    email_list = json.load(file)
print(email_list)
# Connect to SQLite database
conn = sqlite3.connect(SQLITE_DB)
cursor = conn.cursor()

# Load BART MNLI zero-shot classification pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# Load Llama model
model_id = "meta-llama/Llama-3.2-3B-Instruct"
pipe = pipeline(
    "text-generation",
    model=model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Classification categories
categories = ["Not interested", "Need more details", "Want to make a meeting"]

def classify_email(response):
    if not response or response.lower() == "no response":
        return "No Response"
    result = classifier(response, candidate_labels=categories)
    return result['labels'][0]

def get_latest_response(email):
    """Retrieve the latest response for a given email."""
    cursor.execute('''
    SELECT message FROM emails
    WHERE email = ? AND category = 'received'
    ORDER BY timestamp DESC
    LIMIT 1
    ''', (email,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_full_conversation(email):
    """Retrieve the full conversation history for a given email."""
    cursor.execute('''
    SELECT message, category FROM emails
    WHERE email = ?
    ORDER BY timestamp ASC
    ''', (email,))
    results = cursor.fetchall()
    conversation = []
    for message, category in results:
        conversation.append(f"{category}: {message}")
    return "\n".join(conversation)

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
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def create_embeddings(products):
    product_embeddings = []
    for product in products:
        text = f"Product: {product['Product Name']}, Description: {product['Description']}, Specifications: {product['Specifications']}, Case Study: {product['Case Study']}, Compliance: {product['Compliance']}"
        embedding = embedding_model.encode(text)
        product_embeddings.append(embedding)
    return np.array(product_embeddings)

product_embeddings = create_embeddings(product_list)
index = faiss.IndexFlatL2(product_embeddings.shape[1])
index.add(product_embeddings)

def get_relevant_product(query):
    query_embedding = embedding_model.encode([query])
    query_embedding = np.array(query_embedding)
    _, indices = index.search(query_embedding, k=1)
    return product_list[indices[0][0]]

def generate_email_and_subject(company_name, industry, conversation):
    relevant_product = get_relevant_product(conversation)
    messages = [
        {"role": "system", "content": "You are a professional email assistant who writes structured responses."},
        {"role": "user", "content": f"Given the conversation history for {company_name} in the {industry} industry, generate a well-structured response.\n\nConversation:\n{conversation}\n\nProduct Details:\n- {relevant_product}"}
    ]
    outputs = pipe(messages, max_new_tokens=512)
    response_text = outputs[0]["generated_text"]
    subject, email_body = extract_subject_and_body(response_text)
    torch.cuda.empty_cache()

    return subject, email_body

# Process each email in the list
for email in email_list:
    print(f"Processing email from {email}...")
    latest_response = get_latest_response(email)
    category = classify_email(latest_response)
    if category == "Need more details":
        conversation = get_full_conversation(email)
        cursor.execute('''
        SELECT company_name, subject FROM emails
        WHERE email = ? AND category = 'received'
        ORDER BY timestamp DESC
        LIMIT 1
        ''', (email,))
        result = cursor.fetchone()
        if result:
            company_name, industry = result
            subject, response = generate_email_and_subject(company_name, industry, conversation)

            # Insert the sent email into the SQLite database
            cursor.execute('''
            INSERT INTO emails (company_name, email, subject, message, category)
            VALUES (?, ?, ?, ?, ?)
            ''', (company_name, email, subject, response, 'sent'))
            conn.commit()

            # Send the email
            message = MIMEMultipart()
            message["From"], message["To"], message["Subject"] = sender_email, email, subject
            message.attach(MIMEText(response, "plain"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, app_password)
                server.sendmail(sender_email, email, message.as_string())

            print(f"Sent response to {email} for {company_name}")

conn.close()
print("✅ Emails categorized, responses sent, and database updated.")