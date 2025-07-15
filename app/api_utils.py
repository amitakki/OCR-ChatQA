import requests
import streamlit as st
import time
from typing import Optional, Dict, Any


BASE_URL = "http://localhost:8000"


def handle_api_error(response, action_description="API request"):
    """Handle API errors with user-friendly messages"""
    if response.status_code == 404:
        st.error(f"❌ {action_description} failed: Resource not found")
    elif response.status_code == 500:
        st.error(f"❌ {action_description} failed: Server error")
    else:
        st.error(
            f"❌ {action_description} failed: {response.status_code} - {response.text}"
        )


def get_api_response(
    question: str, session_id: Optional[str], model: str
) -> Optional[Dict[str, Any]]:
    """Get response from chat API"""
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    data = {"question": question, "model": model}
    if session_id:
        data["session_id"] = session_id

    try:
        with st.spinner("🤔 Thinking..."):
            response = requests.post(
                f"{BASE_URL}/chat", headers=headers, json=data, timeout=60
            )

        if response.status_code == 200:
            result = response.json()

            # Show processing time if available
            if result.get("processing_time"):
                st.caption(
                    f"⏱️ Response generated in {result['processing_time']:.2f} seconds"
                )

            return result
        else:
            handle_api_error(response, "Chat request")
            return None

    except requests.exceptions.Timeout:
        st.error("⏰ Request timed out. The model might be processing a complex query.")
        return None
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
        return None


def upload_document(file) -> Optional[Dict[str, Any]]:
    """Upload document for processing"""
    try:
        files = {"file": (file.name, file, file.type)}

        with st.spinner(f"📤 Uploading {file.name}..."):
            response = requests.post(f"{BASE_URL}/upload-doc", files=files, timeout=120)

        if response.status_code == 200:
            result = response.json()
            st.success(f"✅ {result['message']}")

            # Show processing status
            if result.get("status") == "pending":
                st.info(
                    "⏳ Document queued for processing. Check status in document list."
                )

            return result
        else:
            handle_api_error(response, "File upload")
            return None

    except requests.exceptions.Timeout:
        st.error("⏰ Upload timed out. Large files may take longer to process.")
        return None
    except Exception as e:
        st.error(f"❌ Upload error: {str(e)}")
        return None


def list_documents() -> list:
    """Get list of all documents"""
    try:
        response = requests.get(f"{BASE_URL}/list-docs", timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            handle_api_error(response, "Document list fetch")
            return []

    except requests.exceptions.Timeout:
        st.error("⏰ Request timed out while fetching document list.")
        return []
    except Exception as e:
        st.error(f"❌ Error fetching documents: {str(e)}")
        return []


def delete_document(file_id: int) -> Optional[Dict[str, Any]]:
    """Delete document"""
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    data = {"file_id": file_id}

    try:
        with st.spinner(f"🗑️ Deleting document {file_id}..."):
            response = requests.post(
                f"{BASE_URL}/delete-doc", headers=headers, json=data, timeout=30
            )

        if response.status_code == 200:
            result = response.json()
            if "message" in result:
                st.success(f"✅ {result['message']}")
            return result
        else:
            handle_api_error(response, "Document deletion")
            return None

    except requests.exceptions.Timeout:
        st.error("⏰ Delete request timed out.")
        return None
    except Exception as e:
        st.error(f"❌ Delete error: {str(e)}")
        return None


def get_document_status(file_id: int) -> Optional[Dict[str, Any]]:
    """Get processing status of a document"""
    try:
        response = requests.get(f"{BASE_URL}/doc-status/{file_id}", timeout=10)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            st.warning(f"📄 Document {file_id} not found")
            return None
        else:
            handle_api_error(response, "Status check")
            return None

    except requests.exceptions.Timeout:
        st.error("⏰ Status check timed out.")
        return None
    except Exception as e:
        st.error(f"❌ Status check error: {str(e)}")
        return None


def get_processing_stats(file_id: int) -> Optional[Dict[str, Any]]:
    """Get processing statistics for a document"""
    try:
        response = requests.get(f"{BASE_URL}/doc-stats/{file_id}", timeout=10)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            st.warning(f"📄 Statistics for document {file_id} not found")
            return None
        else:
            handle_api_error(response, "Statistics fetch")
            return None

    except requests.exceptions.Timeout:
        st.error("⏰ Statistics request timed out.")
        return None
    except Exception as e:
        st.error(f"❌ Statistics error: {str(e)}")
        return None


def check_health() -> bool:
    """Check if the API is healthy and OCR is enabled"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)

        if response.status_code == 200:
            health_data = response.json()
            return health_data.get("status") == "healthy"
        else:
            return False

    except Exception:
        return False


def get_health_info() -> Optional[Dict[str, Any]]:
    """Get detailed health information"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)

        if response.status_code == 200:
            return response.json()
        else:
            return None

    except Exception:
        return None


def wait_for_processing(file_id: int, max_wait_seconds: int = 300) -> str:
    """
    Wait for document processing to complete

    Args:
        file_id: Document ID to monitor
        max_wait_seconds: Maximum time to wait

    Returns:
        Final processing status
    """
    start_time = time.time()
    check_interval = 2  # seconds

    progress_bar = st.progress(0)
    status_text = st.empty()

    while time.time() - start_time < max_wait_seconds:
        status_response = get_document_status(file_id)

        if status_response:
            status = status_response.get("status", "unknown")

            # Update progress
            elapsed = time.time() - start_time
            progress = min(elapsed / max_wait_seconds, 1.0)
            progress_bar.progress(progress)

            status_text.text(f"⏳ Processing status: {status} ({elapsed:.1f}s)")

            if status in ["completed", "failed"]:
                progress_bar.empty()
                status_text.empty()
                return status

        time.sleep(check_interval)

    # Timeout
    progress_bar.empty()
    status_text.empty()
    st.warning(f"⏰ Processing timeout after {max_wait_seconds} seconds")
    return "timeout"


def batch_upload_documents(files: list) -> Dict[str, Any]:
    """
    Upload multiple documents

    Args:
        files: List of uploaded files

    Returns:
        Dictionary with upload results
    """
    results = {"successful": [], "failed": [], "total": len(files)}

    progress_bar = st.progress(0)

    for i, file in enumerate(files):
        st.write(f"📤 Uploading {file.name}...")

        result = upload_document(file)
        if result and "file_id" in result:
            results["successful"].append(
                {"filename": file.name, "file_id": result["file_id"]}
            )
        else:
            results["failed"].append(file.name)

        # Update progress
        progress_bar.progress((i + 1) / len(files))

    progress_bar.empty()

    # Show summary
    st.success(f"✅ {len(results['successful'])} files uploaded successfully")
    if results["failed"]:
        st.error(
            f"❌ {len(results['failed'])} files failed: {', '.join(results['failed'])}"
        )

    return results
