import streamlit as st
from api_utils import (
    upload_document,
    list_documents,
    delete_document,
    get_document_status,
    get_processing_stats,
)
import time


def display_processing_status(doc):
    """Display processing status with appropriate styling"""
    status = doc.get("processing_status", "unknown")

    if status == "completed":
        st.success(f"✅ {status.title()}")
    elif status == "processing":
        st.info(f"⏳ {status.title()}")
    elif status == "failed":
        st.error(f"❌ {status.title()}")
        if doc.get("error_message"):
            st.caption(f"Error: {doc['error_message']}")
    elif status == "pending":
        st.warning(f"⏸️ {status.title()}")
    else:
        st.caption(f"❓ {status}")


def display_processing_method(doc):
    """Display processing method information"""
    method = doc.get("processing_method")
    if method:
        if method == "pure_ocr":
            st.caption("🔍 Processed with OCR")
        elif method == "standard":
            st.caption("📄 Standard text extraction")
        else:
            st.caption(f"🔧 Method: {method}")


def display_sidebar():
    # Header with OCR info
    st.sidebar.title("📄 RAG Chatbot with OCR")
    st.sidebar.caption("Supports text and scanned documents")

    # Model Selection
    st.sidebar.header("🤖 Model Configuration")
    model_options = ["llama-3.3-70b-versatile", "gpt-4o", "gpt-4o-mini"]
    st.sidebar.selectbox("Select Model", options=model_options, key="model")

    # Upload Document Section
    st.sidebar.header("📤 Upload Document")
    st.sidebar.caption("Supports: PDF (text & scanned), DOCX, HTML")

    uploaded_file = st.sidebar.file_uploader(
        "Choose a file",
        type=["pdf", "docx", "html"],
        help="Upload text-based or scanned PDF files, Word documents, or HTML files",
    )

    if uploaded_file is not None:
        col1, col2 = st.sidebar.columns(2)

        with col1:
            if st.button("📤 Upload", key="upload_btn"):
                with st.spinner("Uploading and processing..."):
                    upload_response = upload_document(uploaded_file)
                    if upload_response:
                        st.success(
                            f"✅ File uploaded! ID: {upload_response['file_id']}"
                        )
                        st.info("📋 Processing started in background")
                        st.session_state.documents = list_documents()
                        time.sleep(1)  # Brief pause for user to see success message
                        st.rerun()

        with col2:
            # Show file info
            st.caption(f"📁 {uploaded_file.name}")
            if hasattr(uploaded_file, "size"):
                size_mb = uploaded_file.size / (1024 * 1024)
                st.caption(f"📊 {size_mb:.1f} MB")

    # Document Management Section
    st.sidebar.header("📚 Document Management")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 Refresh", key="refresh_docs"):
            with st.spinner("Refreshing..."):
                st.session_state.documents = list_documents()

    with col2:
        if st.button("📊 Stats", key="show_stats"):
            st.session_state.show_stats = not st.session_state.get("show_stats", False)

    # Initialize document list if not present
    if "documents" not in st.session_state:
        st.session_state.documents = list_documents()

    documents = st.session_state.documents

    # Show statistics if requested
    if st.session_state.get("show_stats", False):
        if documents:
            total_docs = len(documents)
            completed = len(
                [d for d in documents if d.get("processing_status") == "completed"]
            )
            processing = len(
                [d for d in documents if d.get("processing_status") == "processing"]
            )
            failed = len(
                [d for d in documents if d.get("processing_status") == "failed"]
            )

            st.sidebar.metric("📄 Total Documents", total_docs)
            col1, col2, col3 = st.sidebar.columns(3)
            with col1:
                st.metric("✅", completed)
            with col2:
                st.metric("⏳", processing)
            with col3:
                st.metric("❌", failed)

    # Document List
    if documents:
        st.sidebar.subheader("📋 Uploaded Documents")

        for i, doc in enumerate(documents):
            with st.sidebar.expander(f"📄 {doc['filename']}", expanded=False):
                # Basic info
                st.caption(f"🆔 ID: {doc['id']}")
                st.caption(f"📅 {doc['upload_timestamp'][:19]}")

                if doc.get("file_size"):
                    size_mb = doc["file_size"] / (1024 * 1024)
                    st.caption(f"📊 Size: {size_mb:.1f} MB")

                # Processing status
                display_processing_status(doc)
                display_processing_method(doc)

                # Action buttons
                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button(
                        "🔄", key=f"refresh_{doc['id']}", help="Refresh status"
                    ):
                        status_response = get_document_status(doc["id"])
                        if status_response:
                            st.info(f"Status: {status_response['status']}")

                with col2:
                    if st.button("📊", key=f"stats_{doc['id']}", help="View stats"):
                        stats = get_processing_stats(doc["id"])
                        if stats and "error" not in stats:
                            st.json(stats)

                with col3:
                    if st.button(
                        "🗑️", key=f"delete_{doc['id']}", help="Delete document"
                    ):
                        if st.session_state.get(f"confirm_delete_{doc['id']}", False):
                            with st.spinner("Deleting..."):
                                delete_response = delete_document(doc["id"])
                                if delete_response and "message" in delete_response:
                                    st.success("✅ Deleted successfully")
                                    st.session_state.documents = list_documents()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Delete failed")
                            st.session_state[f"confirm_delete_{doc['id']}"] = False
                        else:
                            st.session_state[f"confirm_delete_{doc['id']}"] = True
                            st.warning("Click again to confirm deletion")

        # Bulk actions
        if len(documents) > 1:
            st.sidebar.subheader("🔧 Bulk Actions")

            # Filter by status
            status_filter = st.sidebar.selectbox(
                "Filter by status",
                ["All", "completed", "processing", "failed", "pending"],
                key="status_filter",
            )

            if status_filter != "All":
                filtered_docs = [
                    d for d in documents if d.get("processing_status") == status_filter
                ]
                st.sidebar.caption(
                    f"📊 {len(filtered_docs)} documents with status '{status_filter}'"
                )

    else:
        st.sidebar.info("📭 No documents uploaded yet")
        st.sidebar.caption("Upload a document to get started with RAG!")

    # OCR Information
    with st.sidebar.expander("ℹ️ OCR Information", expanded=False):
        st.caption("🔍 **OCR Capabilities:**")
        st.caption("• Automatically detects scanned PDFs")
        st.caption("• Extracts text from images")
        st.caption("• Creates searchable documents")
        st.caption("• Supports multi-page documents")
        st.caption("")
        st.caption("📋 **Supported Formats:**")
        st.caption("• PDF (text-based)")
        st.caption("• PDF (scanned/image-based)")
        st.caption("• DOCX (Word documents)")
        st.caption("• HTML files")
