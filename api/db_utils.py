import sqlite3
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

DB_NAME = "rag_app.db"


def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_application_logs():
    """Create application logs table"""
    conn = get_db_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS application_logs
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     session_id TEXT,
                     user_query TEXT,
                     gpt_response TEXT,
                     model TEXT,
                     processing_time REAL,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    )
    conn.commit()
    conn.close()


def insert_application_logs(
    session_id, user_query, gpt_response, model, processing_time=None
):
    """Insert application log entry"""
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO application_logs 
           (session_id, user_query, gpt_response, model, processing_time) 
           VALUES (?, ?, ?, ?, ?)""",
        (session_id, user_query, gpt_response, model, processing_time),
    )
    conn.commit()
    conn.close()


def get_chat_history(session_id):
    """Get chat history for a session"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT user_query, gpt_response FROM application_logs 
           WHERE session_id = ? ORDER BY created_at""",
        (session_id,),
    )
    messages = []
    for row in cursor.fetchall():
        messages.extend(
            [
                {"role": "human", "content": row["user_query"]},
                {"role": "ai", "content": row["gpt_response"]},
            ]
        )
    conn.close()
    return messages


def create_document_store():
    """Create document store table with enhanced OCR tracking"""
    conn = get_db_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS document_store
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     filename TEXT,
                     file_size INTEGER,
                     processing_status TEXT DEFAULT 'pending',
                     processing_method TEXT,
                     error_message TEXT,
                     upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     processing_start_time TIMESTAMP,
                     processing_end_time TIMESTAMP,
                     
                     -- OCR-specific fields
                     is_scanned_pdf BOOLEAN DEFAULT 0,
                     converted_pdf_path TEXT,
                     extracted_text_path TEXT,
                     ocr_conversion_success BOOLEAN DEFAULT 0,
                     ocr_processing_time REAL,
                     
                     -- File tracking
                     original_file_path TEXT,
                     temp_file_path TEXT,
                     
                     -- Statistics
                     total_pages INTEGER,
                     total_chunks INTEGER,
                     ocr_confidence_score REAL)"""
    )
    conn.commit()
    conn.close()


def insert_document_record(
    filename, status="pending", file_size=None, original_path=None
):
    """Insert document record with enhanced tracking"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO document_store 
           (filename, file_size, processing_status, original_file_path) 
           VALUES (?, ?, ?, ?)""",
        (filename, file_size, status, original_path),
    )
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Inserted document record: {filename} with file_id {file_id}")
    return file_id


def update_document_processing_status(
    file_id, status, error_message=None, processing_method=None, ocr_data=None
):
    """Update document processing status with OCR information"""
    conn = get_db_connection()

    # Prepare update fields
    update_fields = ["processing_status = ?"]
    params = [status]

    if status == "processing":
        update_fields.append("processing_start_time = ?")
        params.append(datetime.now())
    elif status in ["completed", "failed"]:
        update_fields.append("processing_end_time = ?")
        params.append(datetime.now())

    if error_message:
        update_fields.append("error_message = ?")
        params.append(error_message)

    if processing_method:
        update_fields.append("processing_method = ?")
        params.append(processing_method)

    # Handle OCR-specific data
    if ocr_data:
        if "is_scanned_pdf" in ocr_data:
            update_fields.append("is_scanned_pdf = ?")
            params.append(ocr_data["is_scanned_pdf"])

        if "converted_pdf_path" in ocr_data:
            update_fields.append("converted_pdf_path = ?")
            params.append(ocr_data["converted_pdf_path"])

        if "extracted_text_path" in ocr_data:
            update_fields.append("extracted_text_path = ?")
            params.append(ocr_data["extracted_text_path"])

        if "ocr_conversion_success" in ocr_data:
            update_fields.append("ocr_conversion_success = ?")
            params.append(ocr_data["ocr_conversion_success"])

        if "ocr_processing_time" in ocr_data:
            update_fields.append("ocr_processing_time = ?")
            params.append(ocr_data["ocr_processing_time"])

        if "total_pages" in ocr_data:
            update_fields.append("total_pages = ?")
            params.append(ocr_data["total_pages"])

        if "total_chunks" in ocr_data:
            update_fields.append("total_chunks = ?")
            params.append(ocr_data["total_chunks"])

        if "ocr_confidence_score" in ocr_data:
            update_fields.append("ocr_confidence_score = ?")
            params.append(ocr_data["ocr_confidence_score"])

    params.append(file_id)

    query = f"UPDATE document_store SET {', '.join(update_fields)} WHERE id = ?"

    conn.execute(query, params)
    conn.commit()
    conn.close()
    logger.info(f"Updated document {file_id} status to {status}")


def get_document_processing_status(file_id):
    """Get processing status of a document"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT processing_status FROM document_store WHERE id = ?", (file_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        return result["processing_status"]
    return None


def get_document_details(file_id):
    """Get detailed information about a document including OCR data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM document_store WHERE id = ?""", (file_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return dict(result)
    return None


def delete_document_record(file_id):
    """Delete document record and clean up associated files"""
    conn = get_db_connection()

    # Get document details before deletion for cleanup
    cursor = conn.cursor()
    cursor.execute(
        """SELECT converted_pdf_path, extracted_text_path, temp_file_path 
           FROM document_store WHERE id = ?""",
        (file_id,),
    )
    result = cursor.fetchone()

    if result:
        # Clean up associated files
        files_to_cleanup = [
            result["converted_pdf_path"],
            result["extracted_text_path"],
            result["temp_file_path"],
        ]

        for file_path in files_to_cleanup:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup file {file_path}: {e}")

    # Delete the database record
    conn.execute("DELETE FROM document_store WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()
    logger.info(f"Deleted document record with file_id {file_id}")
    return True


def get_all_documents():
    """Get all documents with enhanced information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, filename, file_size, processing_status, processing_method,
                  error_message, upload_timestamp, processing_start_time, 
                  processing_end_time, is_scanned_pdf, converted_pdf_path,
                  extracted_text_path, ocr_conversion_success, ocr_processing_time,
                  total_pages, total_chunks, ocr_confidence_score
           FROM document_store 
           ORDER BY upload_timestamp DESC"""
    )
    documents = cursor.fetchall()
    conn.close()
    return [dict(doc) for doc in documents]


def get_ocr_statistics():
    """Get OCR processing statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get overall statistics
    cursor.execute(
        """SELECT 
               COUNT(*) as total_documents,
               COUNT(CASE WHEN is_scanned_pdf = 1 THEN 1 END) as scanned_pdfs,
               COUNT(CASE WHEN ocr_conversion_success = 1 THEN 1 END) as successful_ocr,
               COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as completed_docs,
               COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed_docs,
               AVG(ocr_processing_time) as avg_ocr_time,
               AVG(ocr_confidence_score) as avg_confidence,
               SUM(total_pages) as total_pages_processed,
               SUM(total_chunks) as total_chunks_created
           FROM document_store"""
    )
    stats = cursor.fetchone()

    # Get processing method counts
    cursor.execute(
        """SELECT processing_method, COUNT(*) as count 
           FROM document_store 
           WHERE processing_method IS NOT NULL
           GROUP BY processing_method"""
    )
    method_counts = {
        row["processing_method"]: row["count"] for row in cursor.fetchall()
    }

    # Get file size statistics
    cursor.execute(
        """SELECT 
               AVG(file_size) as avg_file_size,
               MIN(file_size) as min_file_size,
               MAX(file_size) as max_file_size,
               SUM(file_size) as total_file_size
           FROM document_store 
           WHERE file_size IS NOT NULL"""
    )
    size_stats = cursor.fetchone()

    conn.close()

    return {
        "overview": dict(stats) if stats else {},
        "processing_methods": method_counts,
        "file_sizes": dict(size_stats) if size_stats else {},
        "ocr_success_rate": (
            (stats["successful_ocr"] / stats["scanned_pdfs"] * 100)
            if stats and stats["scanned_pdfs"] > 0
            else 0
        ),
    }


def get_processing_performance():
    """Get processing performance metrics"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get processing time statistics
    cursor.execute(
        """SELECT 
               AVG(
                   CASE 
                       WHEN processing_start_time IS NOT NULL AND processing_end_time IS NOT NULL
                       THEN (julianday(processing_end_time) - julianday(processing_start_time)) * 86400
                       ELSE NULL
                   END
               ) as avg_processing_time,
               MIN(
                   CASE 
                       WHEN processing_start_time IS NOT NULL AND processing_end_time IS NOT NULL
                       THEN (julianday(processing_end_time) - julianday(processing_start_time)) * 86400
                       ELSE NULL
                   END
               ) as min_processing_time,
               MAX(
                   CASE 
                       WHEN processing_start_time IS NOT NULL AND processing_end_time IS NOT NULL
                       THEN (julianday(processing_end_time) - julianday(processing_start_time)) * 86400
                       ELSE NULL
                   END
               ) as max_processing_time
           FROM document_store
           WHERE processing_status = 'completed'"""
    )
    processing_times = cursor.fetchone()

    # Get recent processing trends (last 10 documents)
    cursor.execute(
        """SELECT 
               processing_method,
               ocr_processing_time,
               processing_status,
               upload_timestamp
           FROM document_store 
           ORDER BY upload_timestamp DESC 
           LIMIT 10"""
    )
    recent_docs = cursor.fetchall()

    conn.close()

    return {
        "processing_times": dict(processing_times) if processing_times else {},
        "recent_documents": [dict(doc) for doc in recent_docs],
    }


def cleanup_old_temp_files():
    """Clean up old temporary files and orphaned processed files"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all file paths from database
    cursor.execute(
        """SELECT converted_pdf_path, extracted_text_path, temp_file_path 
           FROM document_store 
           WHERE converted_pdf_path IS NOT NULL 
           OR extracted_text_path IS NOT NULL 
           OR temp_file_path IS NOT NULL"""
    )
    db_files = cursor.fetchall()

    # Collect all paths that should exist
    valid_paths = set()
    for row in db_files:
        for path in [
            row["converted_pdf_path"],
            row["extracted_text_path"],
            row["temp_file_path"],
        ]:
            if path:
                valid_paths.add(path)

    # Check processed_documents directory for orphaned files
    processed_dir = "./processed_documents"
    cleanup_count = 0

    if os.path.exists(processed_dir):
        for filename in os.listdir(processed_dir):
            file_path = os.path.join(processed_dir, filename)
            if os.path.isfile(file_path) and file_path not in valid_paths:
                try:
                    os.remove(file_path)
                    cleanup_count += 1
                    logger.info(f"Cleaned up orphaned file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup orphaned file {file_path}: {e}")

    conn.close()
    return cleanup_count


def update_document_ocr_results(file_id, ocr_results):
    """Update document with OCR processing results"""
    ocr_data = {
        "is_scanned_pdf": True,
        "converted_pdf_path": ocr_results.get("pdf_path", ""),
        "extracted_text_path": ocr_results.get("text_path", ""),
        "ocr_conversion_success": ocr_results.get("success", False),
        "ocr_processing_time": ocr_results.get("processing_time", 0.0),
    }

    if ocr_results.get("errors"):
        error_message = "; ".join(ocr_results["errors"])
    else:
        error_message = None

    update_document_processing_status(
        file_id,
        "completed" if ocr_results.get("success") else "failed",
        error_message=error_message,
        processing_method=(
            "ocr_converted" if ocr_results.get("success") else "ocr_failed"
        ),
        ocr_data=ocr_data,
    )


def get_documents_by_processing_method(method):
    """Get documents filtered by processing method"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM document_store 
           WHERE processing_method = ? 
           ORDER BY upload_timestamp DESC""",
        (method,),
    )
    documents = cursor.fetchall()
    conn.close()
    return [dict(doc) for doc in documents]


def get_documents_requiring_ocr():
    """Get documents that are scanned PDFs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM document_store 
           WHERE is_scanned_pdf = 1 
           ORDER BY upload_timestamp DESC"""
    )
    documents = cursor.fetchall()
    conn.close()
    return [dict(doc) for doc in documents]


# Initialize the database tables
def initialize_database():
    """Initialize all database tables"""
    create_application_logs()
    create_document_store()
    logger.info("Database initialized successfully")


# Call initialization
initialize_database()
