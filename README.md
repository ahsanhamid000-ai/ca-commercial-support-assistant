# CA Commercial Support Assistant

An AI-powered Flask application for processing commercial documents and providing structured support through summarization, document-grounded question answering, extracted insights, and report generation.

## Features

- Upload **PDF**, **DOCX**, and **TXT** files
- Extract and normalize document text
- Generate an executive summary
- Ask document-based questions through the chatbot
- Use optional AI fallback when a direct document answer is not found
- Extract useful information such as:
  - dates
  - emails
  - amounts
  - action items
- View a structured report in the browser
- Download the report as a PDF
- Preview uploaded PDFs page by page inside the report page
- Store processed documents and chat history using SQLite

## Tech Stack

- Python
- Flask
- SQLite
- OpenAI API
- PyPDF2
- python-docx
- PyMuPDF
- reportlab
- HTML / CSS / JavaScript
- pytest

## Project Structure

```text
ca-commercial-support-assistant/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .env.example
├── uploads/
├── instance/
├── templates/
├── static/
├── utils/
├── tests/
└── docs/
