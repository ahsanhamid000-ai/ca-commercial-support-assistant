# System Architecture

## Main Flow

1. User uploads PDF, DOCX, or TXT file
2. System validates and stores file
3. Text is extracted and cleaned
4. Summary is generated
5. Key information is extracted
6. User asks document-based questions
7. Chatbot answers using relevant document context
8. Structured report is displayed

## Main Modules

- `app.py` - route controller
- `utils/parser.py` - text extraction
- `utils/cleaner.py` - text preprocessing
- `utils/summarizer.py` - executive summary generation
- `utils/context_selector.py` - relevant chunk selection
- `utils/qa_engine.py` - chatbot answer generation
- `utils/extractor.py` - data extraction
- `utils/report_generator.py` - report preparation
- `utils/db_helper.py` - SQLite storage
