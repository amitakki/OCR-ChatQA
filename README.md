# 🤖 OCR-Enhanced RAG Chatbot

A powerful Retrieval-Augmented Generation (RAG) chatbot with advanced OCR capabilities that can process both text-based and scanned PDF documents. Built with FastAPI, Gradio, Streamlit, and LangChain.

## ✨ Features

- 🔍 **Advanced OCR Processing**: Automatically detects and processes scanned PDFs using Tesseract OCR
- 📄 **Multi-format Support**: PDF (text & scanned), DOCX, HTML files
- 🤖 **Multiple AI Models**: Choose from Llama, GPT-4o, and GPT-4o-mini
- 💬 **Intelligent RAG Chat**: Context-aware conversation with your documents
- 📊 **Real-time Status Tracking**: Monitor document processing progress
- 🗑️ **Document Management**: Easy upload, deletion, and organization
- 📁 **File Path Management**: Organized storage of converted documents
- 🔄 **Dual Interface**: Both Gradio and Streamlit frontends available

## 🏗️ Project Structure

```
ocr-rag-chatbot/
├── api/                          # Backend API components
│   ├── chroma_utils.py          # Vector store operations with OCR support
│   ├── db_utils.py              # Database operations with OCR tracking
│   ├── langchain_utils.py       # LangChain RAG pipeline
│   ├── main.py                  # FastAPI application
│   ├── ocr_utils.py             # OCR processing utilities
│   ├── pydantic_models.py       # Data models and schemas
│   └── requirements.txt         # Backend dependencies
├── app/                         # Frontend applications
│   ├── api_utils.py            # API communication utilities
│   ├── chat_interface.py       # Streamlit chat interface
│   ├── gradio_app.py           # Gradio web interface
│   ├── sidebar.py              # Streamlit sidebar components
│   └── streamlit_app.py        # Main Streamlit application
├── processed_documents/         # OCR output directory (auto-created)
├── chroma_db/                  # Vector database directory (auto-created)
├── .env.example                # Environment variables template
├── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Tesseract OCR Engine**
3. **Poppler Utils** (for PDF processing)
4. **API Keys** (Groq API key required)

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils
```

#### macOS
```bash
brew install tesseract poppler
```

#### Windows
1. Download and install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
2. Download and install [Poppler](https://poppler.freedesktop.org/)
3. Add both to your system PATH

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ocr-rag-chatbot.git
cd ocr-rag-chatbot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
cd api
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env file with your API keys
```

### Environment Variables

Create a `.env` file in the root directory:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional OCR Configuration
TESSERACT_PATH=/usr/bin/tesseract
OCR_DPI=300
OCR_TIMEOUT=300

# Optional Application Settings
LOG_LEVEL=INFO
MAX_FILE_SIZE=50MB
PROCESSING_TIMEOUT=300
DEFAULT_MODEL=llama-3.3-70b-versatile
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## 🏃‍♂️ Running the Application

### Option 1: FastAPI + Streamlit (Recommended)

1. **Start the FastAPI backend**
```bash
cd api
python main.py
```
The API will be available at `http://localhost:8000`

2. **Start the Streamlit frontend**
```bash
cd app
streamlit run streamlit_app.py
```
The UI will be available at `http://localhost:8501`

### Option 2: Gradio Interface

```bash
cd app
python gradio_app.py
```
The interface will be available at `http://localhost:7860`

## 📖 Usage Guide

### 1. Upload Documents

- Navigate to the **Documents** tab
- Upload your files (PDF, DOCX, or HTML)
- For scanned PDFs: Wait for OCR processing to complete
- Monitor processing status in real-time

### 2. Chat with Documents

- Go to the **Chat** tab
- Select your preferred AI model
- Ask questions about your uploaded documents
- Get intelligent responses with source information

### 3. Manage Documents

- View all uploaded documents in the management interface
- Check processing status and OCR conversion results
- Delete documents when no longer needed
- View detailed processing statistics

## 🔧 OCR Features

### Automatic Document Detection
- **Smart Analysis**: Automatically distinguishes between text-based and scanned PDFs
- **Processing Method Selection**: Uses optimal processing method for each document type
- **Fallback Mechanisms**: Multiple processing approaches ensure maximum success rate

### OCR Output Management
- **Searchable PDFs**: Creates PDFs with invisible text layer for searching
- **Text Files**: Extracts pure text content for analysis
- **Organized Storage**: Saves converted files in `./processed_documents/`
- **Automatic Cleanup**: Removes associated files when documents are deleted

### File Naming Convention
- **Original**: `document.pdf`
- **OCR PDF**: `document_ocr_converted.pdf`
- **Text File**: `document_extracted_text.txt`

## 🔍 API Endpoints

### Core Endpoints
- `POST /chat` - Chat with RAG capabilities
- `POST /upload-doc` - Upload and process documents
- `GET /list-docs` - List all documents with status
- `POST /delete-doc` - Delete documents
- `GET /health` - System health check

### OCR-Specific Endpoints
- `GET /doc-status/{file_id}` - Get processing status
- `GET /doc-stats/{file_id}` - Get processing statistics
- `GET /processed-files` - List OCR output files

## 🔧 Configuration

### OCR Settings

Edit `api/ocr_utils.py` to adjust:
- **DPI Settings**: Default 300 DPI (higher = better quality, slower processing)
- **OCR Confidence**: Tesseract confidence thresholds
- **Image Preprocessing**: Noise reduction and enhancement parameters
- **Output Paths**: Customize where converted files are saved

### Vector Store Configuration

Edit `api/chroma_utils.py` to modify:
- **Chunk Size**: Default 1000 characters
- **Chunk Overlap**: Default 200 characters overlap
- **Embedding Model**: Default "all-MiniLM-L6-v2"
- **Search Parameters**: Number of results to retrieve

## 🚀 Advanced Features

### Background Processing
- Documents are processed asynchronously
- Real-time status updates
- Queue management for multiple uploads

### Enhanced Metadata
- Processing method tracking
- OCR conversion success rates
- File size and chunk statistics
- Processing time metrics

### Error Handling
- Comprehensive error logging
- Fallback processing methods
- User-friendly error messages
- Automatic retry mechanisms

## 📊 Monitoring

### Processing Statistics
- OCR success rates
- Average processing times
- Document type distribution
- Storage usage metrics

### File Management
- List all processed files
- Clean up orphaned files
- Monitor storage usage
- Track processing history

## 🐛 Troubleshooting

### Common Issues

#### Tesseract Not Found
```bash
# Check if Tesseract is installed
tesseract --version

# If not found, install or add to PATH
export PATH=$PATH:/usr/local/bin
```

#### Poor OCR Quality
- Increase DPI setting in `ocr_utils.py`
- Ensure source documents are high quality
- Install additional language packs if needed

#### Memory Issues
- Reduce DPI for faster processing
- Process smaller documents
- Increase system memory allocation

#### API Connection Issues
- Verify GROQ_API_KEY is set correctly
- Check network connectivity
- Review API rate limits

### Performance Optimization

#### For Speed
```python
# In ocr_utils.py
pages = convert_from_path(pdf_path, dpi=150)  # Lower DPI
```

#### For Quality
```python
# In ocr_utils.py
pages = convert_from_path(pdf_path, dpi=600)  # Higher DPI
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r api/requirements.txt
pip install black flake8 pytest

# Run tests
pytest

# Format code
black .

# Lint code
flake8 .
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangChain** for the RAG framework
- **Tesseract OCR** for text extraction
- **Chroma** for vector storage
- **FastAPI** for the backend API
- **Gradio & Streamlit** for the user interfaces
- **Groq** for AI model access

## 📞 Support

- **Documentation**: Check this README and code comments
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join GitHub Discussions for questions
- **Email**: [your-email@example.com]

---

**Built with ❤️ using Python, FastAPI, LangChain, and Tesseract OCR**
