import gradio as gr
import requests
import time
import os
from typing import List, Tuple, Optional
import json

# API Configuration
BASE_URL = "http://localhost:8000"
SUPPORTED_FORMATS = [".pdf", ".docx", ".html"]


class GradioAPIClient:
    """API client for communicating with the FastAPI backend"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session_id = None

    def chat(
        self, message: str, model: str = "llama-3.3-70b-versatile"
    ) -> Tuple[str, float]:
        """Send chat message and get response"""
        try:
            headers = {"accept": "application/json", "Content-Type": "application/json"}
            data = {"question": message, "model": model}
            if self.session_id:
                data["session_id"] = self.session_id

            response = requests.post(
                f"{self.base_url}/chat", headers=headers, json=data, timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                self.session_id = result.get("session_id")
                return result.get("answer", "No response"), result.get(
                    "processing_time", 0.0
                )
            else:
                return f"Error: {response.status_code} - {response.text}", 0.0

        except requests.exceptions.Timeout:
            return "Error: Request timed out. Please try again.", 0.0
        except Exception as e:
            return f"Error: {str(e)}", 0.0

    def upload_document(self, file_path: str) -> Tuple[bool, str, int]:
        """Upload document for processing"""
        try:
            with open(file_path, "rb") as f:
                files = {
                    "file": (
                        os.path.basename(file_path),
                        f,
                        self._get_mime_type(file_path),
                    )
                }
                response = requests.post(
                    f"{self.base_url}/upload-doc", files=files, timeout=120
                )

            if response.status_code == 200:
                result = response.json()
                return (
                    True,
                    result.get("message", "Upload successful"),
                    result.get("file_id", 0),
                )
            else:
                return False, f"Upload failed: {response.text}", 0

        except Exception as e:
            return False, f"Upload error: {str(e)}", 0

    def list_documents(self) -> List[dict]:
        """Get list of all documents"""
        try:
            response = requests.get(f"{self.base_url}/list-docs", timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []

    def delete_document(self, file_id: int) -> Tuple[bool, str]:
        """Delete document"""
        try:
            headers = {"accept": "application/json", "Content-Type": "application/json"}
            data = {"file_id": file_id}
            response = requests.post(
                f"{self.base_url}/delete-doc", headers=headers, json=data, timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return True, result.get("message", "Deleted successfully")
            else:
                return False, f"Delete failed: {response.text}"
        except Exception as e:
            return False, f"Delete error: {str(e)}"

    def get_document_status(self, file_id: int) -> str:
        """Get document processing status"""
        try:
            response = requests.get(f"{self.base_url}/doc-status/{file_id}", timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get("status", "unknown")
            return "unknown"
        except Exception:
            return "unknown"

    def check_health(self) -> Tuple[bool, dict]:
        """Check system health"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("status") == "healthy", health_data
            return False, {}
        except Exception:
            return False, {}

    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type for file"""
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".html": "text/html",
        }
        return mime_types.get(ext, "application/octet-stream")


# Initialize API client
api_client = GradioAPIClient()


def format_status_emoji(status: str) -> str:
    """Format status with appropriate emoji"""
    status_emojis = {
        "completed": "✅",
        "processing": "⏳",
        "pending": "⏸️",
        "failed": "❌",
        "unknown": "❓",
    }
    return f"{status_emojis.get(status, '❓')} {status.title()}"


def chat_function(
    message: str, history: List[List[str]], model: str
) -> Tuple[List[List[str]], str]:
    """Handle chat interactions"""
    if not message.strip():
        return history, ""

    # Get response from API
    response, processing_time = api_client.chat(message, model)

    # Add to history
    history.append([message, response])

    # Show processing time
    time_info = (
        f"⏱️ Response time: {processing_time:.2f}s" if processing_time > 0 else ""
    )

    return history, time_info


def upload_file(file) -> str:
    """Handle file upload"""
    if file is None:
        return "❌ No file selected"

    # Check file extension
    file_ext = os.path.splitext(file.name)[1].lower()
    if file_ext not in SUPPORTED_FORMATS:
        return f"❌ Unsupported file format. Supported: {', '.join(SUPPORTED_FORMATS)}"

    try:
        success, message, file_id = api_client.upload_document(file.name)
        if success:
            return f"✅ {message}\n📄 File ID: {file_id}\n⏳ Processing started in background..."
        else:
            return f"❌ {message}"
    except Exception as e:
        return f"❌ Upload failed: {str(e)}"


def refresh_documents() -> str:
    """Refresh and display document list"""
    documents = api_client.list_documents()

    if not documents:
        return "📭 No documents uploaded yet"

    doc_list = []
    for doc in documents:
        status = format_status_emoji(doc.get("processing_status", "unknown"))
        filename = doc.get("filename", "Unknown")
        file_id = doc.get("id", "N/A")
        upload_time = doc.get("upload_timestamp", "Unknown")[:19]  # Remove microseconds

        doc_info = f"📄 **{filename}** (ID: {file_id})\n"
        doc_info += f"   Status: {status}\n"
        doc_info += f"   Uploaded: {upload_time}\n"
        doc_list.append(doc_info)

    return "\n".join(doc_list)


def delete_document_by_id(file_id: str) -> str:
    """Delete document by ID"""
    if not file_id.strip():
        return "❌ Please enter a file ID"

    try:
        file_id_int = int(file_id)
        success, message = api_client.delete_document(file_id_int)
        if success:
            return f"✅ {message}"
        else:
            return f"❌ {message}"
    except ValueError:
        return "❌ Invalid file ID. Please enter a number."
    except Exception as e:
        return f"❌ Delete failed: {str(e)}"


def check_system_status() -> str:
    """Check and display system status"""
    is_healthy, health_data = api_client.check_health()

    if not is_healthy:
        return "❌ System is offline or unreachable"

    status_info = []
    status_info.append("✅ System Online")

    if health_data.get("ocr_enabled", False):
        status_info.append("🔍 OCR Available")
    else:
        status_info.append("❌ OCR Unavailable")

    supported_formats = health_data.get("supported_formats", [])
    if supported_formats:
        status_info.append(f"📄 Supported: {', '.join(supported_formats)}")

    features = health_data.get("features", [])
    if features:
        status_info.append(f"🚀 Features: {', '.join(features)}")

    return "\n".join(status_info)


def create_interface():
    """Create and configure Gradio interface"""

    # Custom CSS
    css = """
    .gradio-container {
        max-width: 1200px !important;
    }
    .chat-message {
        padding: 10px;
        margin: 5px 0;
        border-radius: 10px;
    }
    .status-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .upload-box {
        border: 2px dashed #667eea;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    """

    with gr.Blocks(
        css=css, title="OCR-Enhanced RAG Chatbot", theme=gr.themes.Soft()
    ) as interface:

        # Header
        gr.HTML(
            """
        <div style="text-align: center; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
            <h1>🤖 OCR-Enhanced RAG Chatbot</h1>
            <p style="margin: 0; font-size: 16px;">Intelligent document processing with OCR capabilities</p>
        </div>
        """
        )

        # Main interface tabs
        with gr.Tabs():

            # Chat Tab
            with gr.Tab("💬 Chat", id="chat"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            height=500,
                            label="Chat with your documents",
                            show_label=True,
                            avatar_images=("👤", "🤖"),
                            bubble_full_width=False,
                        )

                        with gr.Row():
                            msg = gr.Textbox(
                                placeholder="Ask questions about your uploaded documents...",
                                label="Your message",
                                lines=2,
                                scale=4,
                            )
                            send_btn = gr.Button("Send 📤", variant="primary", scale=1)

                        processing_info = gr.Textbox(
                            label="Processing Info",
                            interactive=False,
                            visible=True,
                            max_lines=1,
                        )

                    with gr.Column(scale=1):
                        model_choice = gr.Dropdown(
                            choices=[
                                "llama-3.3-70b-versatile",
                                "gpt-4o",
                                "gpt-4o-mini",
                            ],
                            value="llama-3.3-70b-versatile",
                            label="🤖 Select Model",
                            info="Choose the AI model for responses",
                        )

                        clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")

                        # System status
                        with gr.Group():
                            gr.HTML("<h4>🔧 System Status</h4>")
                            status_display = gr.Textbox(
                                label="Status", interactive=False, lines=6
                            )
                            status_refresh_btn = gr.Button(
                                "🔄 Refresh Status", size="sm"
                            )

            # Document Management Tab
            with gr.Tab("📄 Documents", id="documents"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.HTML(
                            """
                        <div class="upload-box">
                            <h3>📤 Upload Documents</h3>
                            <p>Supports: PDF (text & scanned), DOCX, HTML</p>
                        </div>
                        """
                        )

                        file_upload = gr.File(
                            label="Choose file",
                            file_types=[".pdf", ".docx", ".html"],
                            type="filepath",
                        )

                        upload_btn = gr.Button("📤 Upload Document", variant="primary")
                        upload_status = gr.Textbox(
                            label="Upload Status", interactive=False, lines=3
                        )

                    with gr.Column(scale=1):
                        gr.HTML("<h3>📋 Document List</h3>")

                        doc_list_display = gr.Textbox(
                            label="Uploaded Documents",
                            interactive=False,
                            lines=15,
                            placeholder="No documents uploaded yet...",
                        )

                        refresh_docs_btn = gr.Button(
                            "🔄 Refresh List", variant="secondary"
                        )

                # Delete section
                with gr.Row():
                    with gr.Column():
                        gr.HTML("<h3>🗑️ Delete Document</h3>")
                        delete_id_input = gr.Textbox(
                            label="File ID to delete",
                            placeholder="Enter file ID number...",
                        )
                        delete_btn = gr.Button("🗑️ Delete Document", variant="stop")
                        delete_status = gr.Textbox(
                            label="Delete Status", interactive=False, lines=2
                        )

        # Event handlers
        def clear_chat():
            api_client.session_id = None  # Reset session
            return [], ""

        # Chat events
        send_btn.click(
            chat_function,
            inputs=[msg, chatbot, model_choice],
            outputs=[chatbot, processing_info],
        ).then(lambda: "", outputs=[msg])

        msg.submit(
            chat_function,
            inputs=[msg, chatbot, model_choice],
            outputs=[chatbot, processing_info],
        ).then(lambda: "", outputs=[msg])

        clear_btn.click(clear_chat, outputs=[chatbot, processing_info])

        # Document events
        upload_btn.click(upload_file, inputs=[file_upload], outputs=[upload_status])

        refresh_docs_btn.click(refresh_documents, outputs=[doc_list_display])

        delete_btn.click(
            delete_document_by_id, inputs=[delete_id_input], outputs=[delete_status]
        ).then(lambda: "", outputs=[delete_id_input])

        # Status events
        status_refresh_btn.click(check_system_status, outputs=[status_display])

        # Load initial data
        interface.load(check_system_status, outputs=[status_display])

        interface.load(refresh_documents, outputs=[doc_list_display])

        # Footer
        gr.HTML(
            """
        <div style="text-align: center; color: #666; padding: 20px; margin-top: 20px; border-top: 1px solid #eee;">
            🤖 OCR-Enhanced RAG Chatbot | Built with Gradio, FastAPI, and LangChain
        </div>
        """
        )

    return interface


def main():
    """Main function to launch the Gradio interface"""
    interface = create_interface()

    # Launch configuration
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True,
        show_error=True,
        favicon_path=None,
        ssl_verify=False,
        max_threads=10,
    )


if __name__ == "__main__":
    print("🚀 Starting OCR-Enhanced RAG Chatbot Gradio Interface...")
    print("📡 Make sure the FastAPI backend is running on http://localhost:8000")
    print("🌐 Gradio interface will be available at http://localhost:7860")
    main()
