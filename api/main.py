from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic_models import (
    QueryInput,
    QueryResponse,
    DocumentInfo,
    DeleteFileRequest,
    ProcessingStatsResponse,
)
from dotenv import load_dotenv
load_dotenv()
from langchain_utils import get_rag_chain
from db_utils import (
    insert_application_logs,
    get_chat_history,
    get_all_documents,
    insert_document_record,
    delete_document_record,
    update_document_processing_status,
    get_document_processing_status,
)
from chroma_utils import (
    index_document_to_chroma,
    delete_doc_from_chroma,
    get_document_processing_stats,
)
import os
import uuid
import logging
import shutil
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

logging.basicConfig(filename="app.log", level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enhanced RAG Chatbot with OCR", version="2.0.0")

# Thread pool for background processing
executor = ThreadPoolExecutor(max_workers=2)


@app.post("/chat", response_model=QueryResponse)
def chat(query_input: QueryInput):
    """
    Chat endpoint with RAG capabilities
    """
    session_id = query_input.session_id
    logger.info(
        f"Session ID: {session_id}, User Query: {query_input.question}, Model: {query_input.model.value}"
    )

    if not session_id:
        session_id = str(uuid.uuid4())

    try:
        chat_history = get_chat_history(session_id)
        rag_chain = get_rag_chain(query_input.model.value)

        start_time = time.time()
        answer = rag_chain.invoke(
            {"input": query_input.question, "chat_history": chat_history}
        )["answer"]
        processing_time = time.time() - start_time

        insert_application_logs(
            session_id, query_input.question, answer, query_input.model.value
        )

        logger.info(
            f"Session ID: {session_id}, AI Response generated in {processing_time:.2f}s"
        )

        return QueryResponse(
            answer=answer,
            session_id=session_id,
            model=query_input.model,
            processing_time=processing_time,
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


def process_document_background(file_path: str, file_id: int, filename: str):
    """
    Background task for document processing
    """
    try:
        logger.info(f"Starting background processing for file_id {file_id}: {filename}")

        # Update status to processing
        update_document_processing_status(file_id, "processing")

        # Process and index document
        success = index_document_to_chroma(file_path, file_id)

        if success:
            update_document_processing_status(file_id, "completed")
            logger.info(f"Successfully processed file_id {file_id}: {filename}")
        else:
            update_document_processing_status(file_id, "failed")
            logger.error(f"Failed to process file_id {file_id}: {filename}")

    except Exception as e:
        logger.error(f"Error in background processing for file_id {file_id}: {e}")
        update_document_processing_status(file_id, "failed")

    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)


@app.post("/upload-doc")
async def upload_and_index_document(file: UploadFile = File(...)):
    """
    Upload and index document with OCR support
    """
    allowed_extensions = [".pdf", ".docx", ".html"]
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types are: {', '.join(allowed_extensions)}",
        )

    # Create a unique temporary file path
    temp_file_path = f"temp_{uuid.uuid4()}_{file.filename}"

    try:
        # Save the uploaded file to a temporary file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Insert document record with pending status
        file_id = insert_document_record(file.filename, "pending")

        # Submit background processing task
        executor.submit(
            process_document_background, temp_file_path, file_id, file.filename
        )

        logger.info(f"Document upload initiated for file_id {file_id}: {file.filename}")

        return {
            "message": f"File {file.filename} has been uploaded and queued for processing.",
            "file_id": file_id,
            "status": "pending",
        }

    except Exception as e:
        # Clean up temporary file if something goes wrong
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}"
        )


@app.get("/list-docs", response_model=list[DocumentInfo])
def list_documents():
    """
    List all uploaded documents with their processing status
    """
    try:
        documents = get_all_documents()
        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list documents: {str(e)}"
        )


@app.get("/doc-status/{file_id}")
def get_document_status(file_id: int):
    """
    Get processing status of a specific document
    """
    try:
        status = get_document_processing_status(file_id)
        if status is None:
            raise HTTPException(
                status_code=404, detail=f"Document with file_id {file_id} not found"
            )

        return {"file_id": file_id, "status": status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@app.get("/doc-stats/{file_id}", response_model=ProcessingStatsResponse)
def get_document_stats(file_id: int):
    """
    Get processing statistics for a document
    """
    try:
        stats = get_document_processing_stats(file_id)
        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])

        return ProcessingStatsResponse(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@app.post("/delete-doc")
def delete_document(request: DeleteFileRequest):
    """
    Delete document from both vector store and database
    """
    try:
        # Delete from Chroma
        chroma_delete_success = delete_doc_from_chroma(request.file_id)

        if chroma_delete_success:
            # If successfully deleted from Chroma, delete from our database
            db_delete_success = delete_document_record(request.file_id)
            if db_delete_success:
                logger.info(
                    f"Successfully deleted document with file_id {request.file_id}"
                )
                return {
                    "message": f"Successfully deleted document with file_id {request.file_id} from the system."
                }
            else:
                logger.warning(
                    f"Deleted from Chroma but failed to delete from database: {request.file_id}"
                )
                return {
                    "error": f"Deleted from Chroma but failed to delete document with file_id {request.file_id} from the database."
                }
        else:
            logger.error(f"Failed to delete document from Chroma: {request.file_id}")
            return {
                "error": f"Failed to delete document with file_id {request.file_id} from Chroma."
            }
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting document: {str(e)}"
        )


@app.get("/health")
def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "ocr_enabled": True,
        "supported_formats": [".pdf", ".docx", ".html"],
        "features": ["OCR", "RAG", "Chat History", "Document Management"],
    }


@app.on_event("shutdown")
def shutdown_event():
    """
    Cleanup on shutdown
    """
    executor.shutdown(wait=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
