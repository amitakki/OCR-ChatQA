# OCR-Enhanced RAG Chatbot Setup Guide

This guide will help you set up the enhanced RAG chatbot with OCR capabilities for processing both text-based and scanned PDF documents.

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Tesseract OCR Engine**
3. **Poppler Utils** (for PDF processing)
4. **API Keys** (Groq API key)

## 📦 System Dependencies Installation

### Ubuntu/Debian
```bash
# Install Tesseract OCR
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# Install Poppler for PDF processing
sudo apt-get install poppler-utils

# Install additional language packs (optional)
sudo apt-get install tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-spa
```

### macOS
```bash
# Install using Homebrew
brew install tesseract
brew install poppler

# Install additional language packs (optional)
brew install tesseract-lang
```

### Windows
1. **Download Tesseract**: https://github.com/UB-Mannheim/tesseract/wiki
2. **Download Poppler**: https://poppler.freedesktop.org/
3. Add both to your system PATH

## 🐍 Python Environment Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
TESSERACT_PATH=/usr/bin/tesseract  # Adjust path as needed
```

## 🏗️ Project Structure

```
rag-chatbot-ocr/
├── main.py                 # FastAPI application
├── streamlit_app.py        # Streamlit UI
├── ocr_utils.py           # OCR processing utilities
├── chroma_utils.py        # Enhanced vector store operations
├── db_utils.py            # Database operations with status tracking
├── langchain_utils.py     # LangChain RAG pipeline
├── api_utils.py           # API communication utilities
├── sidebar.py             # Enhanced Streamlit sidebar
├── chat_interface.py      # Chat interface
├── pydantic_models.py     # Data models
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── app.log               # Application logs
├── rag_app.db            # SQLite database
└── chroma_db/            # Vector database directory
```

## 🚀 Running the Application

### 1. Start the FastAPI Backend
```bash
# Terminal 1
python main.py
```
The API will be available at `http://localhost:8000`

### 2. Start the Streamlit Frontend
```bash
# Terminal 2
streamlit run streamlit_app.py
```
The UI will be available at `http://localhost:8501`

## 🔧 Configuration Options

### OCR Configuration
In `ocr_utils.py`, you can adjust:
- **DPI settings** for PDF conversion (default: 300)
- **OCR confidence thresholds**
- **Image preprocessing parameters**
- **Tesseract OCR modes**

### Vector Store Configuration
In `chroma_utils.py`:
- **Chunk size** (default: 1000)
- **Chunk overlap** (
