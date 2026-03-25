# CA Commercial Support Assistant

An AI-powered Flask application for processing commercial documents and providing intelligent support features such as summarization, document-grounded question answering, key information extraction, and structured report generation.

---

## Features

- Upload **PDF**, **DOCX**, and **TXT** files
- Extract and clean document text
- Generate an executive summary
- Ask document-based questions through a chatbot
- Extract useful information such as:
  - dates
  - emails
  - amounts
  - action items
- View a structured report in the browser
- Download the generated report as a PDF
- Store processed documents and chat history using SQLite

---

## Tech Stack

- Python
- Flask
- SQLite
- OpenAI API
- PyPDF2
- python-docx
- reportlab
- HTML / CSS / JavaScript
- pytest

---

## Project Structure

```text
ca-commercial-support-assistant/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env
├── uploads/
├── instance/
├── templates/
├── static/
├── utils/
├── tests/
└── docs/
