# 🚀 Automated Cold Email Outreach System

An AI-powered system for automating personalized cold email campaigns with intelligent response handling.

![GitHub last commit](https://img.shields.io/github/last-commit/MahmoudSaad21/Automated-Cold-Email-Outreach-System)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📋 Overview

This project implements an end-to-end automated cold emailing system for businesses to streamline their outreach process. It leverages AI-driven content generation and efficient email management workflows to handle the complete email lifecycle – from crafting personalized messages to managing responses and logging communication.

### 🎥 [Watch the Demo Video]

https://github.com/user-attachments/assets/e0cb8708-2e2b-4667-a02f-58747804f58f



## ✨ Key Features

- **🤖 AI-Generated Email Content**: Uses state-of-the-art language models (Meta LLaMA-3.2) to create highly personalized and compelling emails
- **📊 Product-Aware Personalization**: Extracts relevant product information from PDF catalogs to enhance email personalization
- **📨 Smart Response Handling**: Automatically classifies and processes email responses with appropriate follow-ups
- **💾 Conversation Tracking**: Stores all communication in an SQLite database for easy tracking and analysis
- **🔍 Product Recommendation**: Uses FAISS and embeddings to find the most relevant products for each prospect
- **⏱️ Event-Driven Architecture**: Efficiently manages email queues and processes with minimal manual intervention

## 🛠️ Technologies Used

- **AI Models**: Meta LLaMA, Facebook BART for classification
- **Email Protocols**: SMTP (sending), IMAP (receiving)
- **Database**: SQLite
- **Embedding & Similarity**: FAISS, Sentence Transformers
- **PDF Processing**: PyPDF2
- **UI**: Streamlit

## 📁 Project Structure

```
.
├── app.py                          # Streamlit application for visualization/management
├── Cold Emailing.ipynb             # Jupyter notebook with code explanations and development
├── detailed_product_catalog.pdf    # Sample product information in PDF format
├── event_driven_emails.py          # Continuous email monitoring script
├── first_sent.py                   # Initial email sending script
├── response.py                     # Response classification and handling script
└── VR_and_Software_Companies_2.csv # Sample prospect data
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Gmail account with [App Password](https://support.google.com/accounts/answer/185833?hl=en) enabled
- Hugging Face account (for model access)

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/MahmoudSaad21/Automated-Cold-Email-Outreach-System.git
   cd Automated-Cold-Email-Outreach-System
   ```

2. Install required packages
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your email credentials
   - Edit `first_sent.py` and `event_driven_emails.py` to include your email and app password

4. Login to Hugging Face
   ```bash
   huggingface-cli login
   ```

### Usage

1. Prepare your prospect data in CSV format (see `VR_and_Software_Companies_2.csv` for example)
2. Add your product information in PDF format (see `detailed_product_catalog.pdf` for example)
3. Run the initial email campaign
   ```bash
   python first_sent.py
   ```
4. Start the email monitoring system
   ```bash
   python event_driven_emails.py
   ```
5. Launch the Streamlit dashboard (optional)
   ```bash
   streamlit run app.py
   ```

## 📋 How It Works

### System Workflow

1. **Initial Campaign**: `first_sent.py` reads company information from CSV, extracts product details from PDF, generates personalized emails using AI, and sends them via Gmail SMTP.

2. **Email Monitoring**: `event_driven_emails.py` continuously checks for unread responses using IMAP, stores them in the database, and passes them to the response handler.

3. **Response Processing**: `response.py` classifies incoming emails using NLP, generates appropriate replies based on the intent, and maintains conversation context through the database.

4. **Visualization**: The Streamlit app provides real-time insights into campaign performance, email statistics, and conversation threads.

### Email Classification Categories

- **Not Interested**: No further action taken
- **Need More Details**: Automatically generates a detailed response with relevant product information
- **Meeting Request**: Forwards to HR (or designated team) for scheduling

## 📊 Database Schema

The system uses an SQLite database (`emails.db`) with the following structure:

```sql
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'sent' or 'received'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

## 📈 Future Enhancements

- Add A/B testing for email templates
- Implement sentiment analysis for better response understanding
- Create more advanced scheduling functionality for meetings
- Add CRM integration capabilities

## 🔒 Privacy & Ethics

This tool is designed for legitimate business outreach. Please ensure:

- You have the right to contact the individuals in your list
- You comply with anti-spam laws like CAN-SPAM, GDPR, etc.
- You provide clear opt-out mechanisms in all communications

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- [Hugging Face](https://huggingface.co/) for their transformer models
- [Meta AI](https://ai.meta.com/) for the LLaMA model
- [Facebook Research](https://github.com/facebookresearch) for FAISS
