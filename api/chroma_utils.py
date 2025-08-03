from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredHTMLLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai

from langchain_core.documents import Document
from mistral_ocr_utils import MistralOCRProcessor
from typing import List
import os
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
)

# Embeddings
embedding_function = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",  # Latest Gemini embedding model
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Vector store initialization
vectorstore = Chroma(
    persist_directory="./chroma_db", embedding_function=embedding_function,
    collection_metadata={"hnsw:space": "cosine"}  # explicitly set
)

# Initialize Mistral OCR processor with custom output directory
try:
    ocr_processor = MistralOCRProcessor(
        api_key=os.getenv("MISTRAL_API_KEY"), output_dir="./processed_documents"
    )
    logger.info("Mistral AI OCR processor initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Mistral OCR processor: {e}")
    ocr_processor = None


def load_and_split_document(file_path: str) -> List[Document]:
    """
    Load and split document with enhanced Mistral AI OCR support and path management

    Args:
        file_path: Path to the document file

    Returns:
        List of split documents with enhanced metadata
    """
    documents = []

    try:
        if file_path.endswith(".pdf"):
            # Check if PDF is scanned
            if ocr_processor and ocr_processor.is_pdf_scanned(file_path):
                logger.info(f"Detected scanned PDF: {file_path}")

                # Convert scanned PDF and save both formats using Mistral AI
                results = ocr_processor.convert_and_save_both(
                    file_path, output_dir_custom="./processed_documents"
                )

                if results["success"]:
                    logger.info(
                        f"Mistral AI OCR conversion successful for: {file_path}"
                    )
                    logger.info(
                        f"Processing time: {results.get('processing_time', 0):.2f}s, Pages: {results.get('pages_processed', 0)}, API calls: {results.get('api_calls_made', 0)}"
                    )

                    # loading extracted text
                    if results["text_path"] and os.path.exists(results["text_path"]):
                        try:
                            with open(results["text_path"], "r", encoding="utf-8") as f:
                                text_content = f.read()

                            if text_content.strip():
                                documents = [
                                    Document(
                                        page_content=text_content,
                                        metadata={
                                            "original_file": file_path,
                                            "converted_pdf_path": results.get(
                                                "pdf_path", ""
                                            ),
                                            "extracted_text_path": results["text_path"],
                                            "processing_method": "mistral_ocr_text_only",
                                            "ocr_conversion_success": True,
                                            "ocr_provider": "Mistral AI",
                                            "processing_time": results.get(
                                                "processing_time", 0
                                            ),
                                            "pages_processed": results.get(
                                                "pages_processed", 0
                                            ),
                                            "api_calls_made": results.get(
                                                "api_calls_made", 0
                                            ),
                                        },
                                    )
                                ]
                                logger.info(
                                    f"Successfully loaded Mistral AI extracted text: {results['text_path']}"
                                )

                        except Exception as e:
                            logger.warning(f"Failed to load extracted text: {e}")

                # If Mistral AI conversion failed, log the errors
                if not documents:
                    logger.error("Mistral AI OCR conversion failed")
                    if results.get("errors"):
                        for error in results["errors"]:
                            logger.error(f"Mistral AI OCR error: {error}")

                    # Create a document with error information
                    documents = [
                        Document(
                            page_content="Failed to extract text using Mistral AI OCR. Please check the document quality and try again.",
                            metadata={
                                "original_file": file_path,
                                "processing_method": "mistral_ocr_failed",
                                "ocr_conversion_success": False,
                                "ocr_provider": "Mistral AI",
                                "errors": results.get("errors", []),
                            },
                        )
                    ]

            else:
                logger.info(f"Detected text-based PDF: {file_path}")
                loader = PyPDFLoader(file_path)
                documents = loader.load()

                # Add metadata for text-based PDFs
                for doc in documents:
                    doc.metadata.update(
                        {
                            "original_file": file_path,
                            "processing_method": "standard_pdf",
                            "ocr_conversion_success": False,
                            "is_text_based": True,
                        }
                    )

        elif file_path.endswith(".docx"):
            logger.info(f"Processing DOCX file: {file_path}")
            loader = Docx2txtLoader(file_path)
            documents = loader.load()

            # Add metadata for DOCX files
            for doc in documents:
                doc.metadata.update(
                    {
                        "original_file": file_path,
                        "processing_method": "docx_standard",
                        "ocr_conversion_success": False,
                        "document_type": "word_document",
                    }
                )

        elif file_path.endswith(".html"):
            logger.info(f"Processing HTML file: {file_path}")
            loader = UnstructuredHTMLLoader(file_path)
            documents = loader.load()

            # Add metadata for HTML files
            for doc in documents:
                doc.metadata.update(
                    {
                        "original_file": file_path,
                        "processing_method": "html_standard",
                        "ocr_conversion_success": False,
                        "document_type": "html_document",
                    }
                )

        else:
            raise ValueError(f"Unsupported file type: {file_path}")

        # Split documents if we have content
        if documents:
            split_documents = text_splitter.split_documents(documents)
            logger.info(
                f"Successfully split {len(documents)} documents into {len(split_documents)} chunks"
            )
            return split_documents
        else:
            logger.warning(f"No content extracted from {file_path}")
            return []

    except Exception as e:
        logger.error(f"Error loading document {file_path}: {e}")
        return []


def index_document_to_chroma(file_path: str, file_id: int) -> bool:
    """
    Index document to Chroma with enhanced Mistral AI OCR support and metadata

    Args:
        file_path: Path to the document file
        file_id: Unique file identifier

    Returns:
        True if indexing successful, False otherwise
    """
    try:
        logger.info(f"Starting to index document: {file_path} with file_id: {file_id}")

        # Load and split document
        splits = load_and_split_document(file_path)

        if not splits:
            logger.warning(f"No content to index from {file_path}")
            return False

        # Enhance metadata for each split
        for i, split in enumerate(splits):
            split.metadata.update(
                {
                    "file_id": file_id,
                    "original_filename": os.path.basename(file_path),
                    "chunk_index": i,
                    "total_chunks": len(splits),
                    "indexed_at": (
                        str(os.path.getctime(file_path))
                        if os.path.exists(file_path)
                        else ""
                    ),
                    "file_size": (
                        os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    ),
                }
            )

        # Add documents to vector store
        vectorstore.add_documents(splits)
        logger.info(
            f"Successfully indexed {len(splits)} document chunks for file_id {file_id}"
        )

        # Log processing method statistics
        processing_methods = set(
            split.metadata.get("processing_method", "unknown") for split in splits
        )
        ocr_providers = set(
            split.metadata.get("ocr_provider", "none")
            for split in splits
            if split.metadata.get("ocr_provider")
        )
        logger.info(f"Processing methods used: {', '.join(processing_methods)}")
        if ocr_providers:
            logger.info(f"OCR providers used: {', '.join(ocr_providers)}")

        return True

    except Exception as e:
        logger.error(f"Error indexing document {file_path}: {e}")
        return False


def delete_doc_from_chroma(file_id: int) -> bool:
    """
    Delete document from Chroma vector store with enhanced cleanup

    Args:
        file_id: Unique file identifier

    Returns:
        True if deletion successful, False otherwise
    """
    try:
        # Get document information before deletion
        docs = vectorstore.get(where={"file_id": file_id})
        logger.info(f"Found {len(docs['ids'])} document chunks for file_id {file_id}")

        if docs["ids"]:
            # Log processing method before deletion
            if docs["metadatas"]:
                processing_methods = set(
                    metadata.get("processing_method", "unknown")
                    for metadata in docs["metadatas"]
                )
                ocr_providers = set(
                    metadata.get("ocr_provider", "none")
                    for metadata in docs["metadatas"]
                    if metadata.get("ocr_provider")
                )
                logger.info(
                    f"Deleting documents processed with methods: {', '.join(processing_methods)}"
                )
                if ocr_providers:
                    logger.info(f"OCR providers: {', '.join(ocr_providers)}")

            # Delete from vector store
            vectorstore._collection.delete(where={"file_id": file_id})
            logger.info(f"Successfully deleted all documents with file_id {file_id}")

            # Optional: Clean up processed files (be careful with this)
            # cleanup_processed_files(file_id, docs['metadatas'])

            return True
        else:
            logger.warning(f"No documents found with file_id {file_id}")
            return True  # Consider it successful if nothing to delete

    except Exception as e:
        logger.error(
            f"Error deleting document with file_id {file_id} from Chroma: {str(e)}"
        )
        return False


def cleanup_processed_files(file_id: int, metadatas: List[dict]) -> bool:
    """
    Clean up processed OCR files when document is deleted

    Args:
        file_id: File identifier
        metadatas: List of metadata dictionaries

    Returns:
        True if cleanup successful
    """
    try:
        files_to_cleanup = set()

        for metadata in metadatas:
            # Collect paths of processed files
            converted_pdf = metadata.get("converted_pdf_path")
            extracted_text = metadata.get("extracted_text_path")

            if converted_pdf and os.path.exists(converted_pdf):
                files_to_cleanup.add(converted_pdf)

            if extracted_text and os.path.exists(extracted_text):
                files_to_cleanup.add(extracted_text)

        # Delete files
        for file_path in files_to_cleanup:
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up processed file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {e}")

        return True

    except Exception as e:
        logger.error(f"Error during cleanup for file_id {file_id}: {e}")
        return False


def get_document_processing_stats(file_id: int) -> dict:
    """
    Get enhanced processing statistics for a document

    Args:
        file_id: Unique file identifier

    Returns:
        Dictionary with detailed processing statistics
    """
    try:
        docs = vectorstore.get(where={"file_id": file_id})

        if not docs["ids"]:
            return {"error": "Document not found"}

        # Get metadata from all chunks
        metadatas = docs["metadatas"]

        # Collect statistics
        processing_methods = set()
        chunk_count = len(docs["ids"])
        original_files = set()
        converted_files = set()
        text_files = set()
        ocr_success_count = 0
        ocr_providers = set()
        total_processing_time = 0
        total_pages_processed = 0
        total_api_calls = 0

        for metadata in metadatas:
            if "processing_method" in metadata:
                processing_methods.add(metadata["processing_method"])

            if "original_file" in metadata:
                original_files.add(metadata["original_file"])

            if "converted_pdf_path" in metadata and metadata["converted_pdf_path"]:
                converted_files.add(metadata["converted_pdf_path"])

            if "extracted_text_path" in metadata and metadata["extracted_text_path"]:
                text_files.add(metadata["extracted_text_path"])

            if metadata.get("ocr_conversion_success"):
                ocr_success_count += 1

            if "ocr_provider" in metadata and metadata["ocr_provider"]:
                ocr_providers.add(metadata["ocr_provider"])

            # Mistral AI specific stats
            if "processing_time" in metadata:
                total_processing_time = max(
                    total_processing_time, metadata.get("processing_time", 0)
                )

            if "pages_processed" in metadata:
                total_pages_processed = max(
                    total_pages_processed, metadata.get("pages_processed", 0)
                )

            if "api_calls_made" in metadata:
                total_api_calls = max(
                    total_api_calls, metadata.get("api_calls_made", 0)
                )

        # Calculate file sizes
        total_converted_size = 0
        for file_path in converted_files:
            if os.path.exists(file_path):
                total_converted_size += os.path.getsize(file_path)

        return {
            "file_id": file_id,
            "chunk_count": chunk_count,
            "processing_methods": list(processing_methods),
            "ocr_providers": list(ocr_providers),
            "original_filename": (
                metadatas[0].get("original_filename", "unknown")
                if metadatas
                else "unknown"
            ),
            "original_files": list(original_files),
            "converted_pdf_files": list(converted_files),
            "extracted_text_files": list(text_files),
            "ocr_success_rate": (
                f"{(ocr_success_count/chunk_count)*100:.1f}%"
                if chunk_count > 0
                else "0%"
            ),
            "total_converted_size_kb": round(total_converted_size / 1024, 2),
            "has_ocr_conversion": len(converted_files) > 0 or len(text_files) > 0,
            "processing_summary": _generate_processing_summary(
                processing_methods, ocr_providers
            ),
            # Mistral AI specific stats
            "mistral_processing_time": total_processing_time,
            "mistral_pages_processed": total_pages_processed,
            "mistral_api_calls_made": total_api_calls,
        }

    except Exception as e:
        logger.error(f"Error getting stats for file_id {file_id}: {e}")
        return {"error": str(e)}


def _generate_processing_summary(
    processing_methods: set, ocr_providers: set = None
) -> str:
    """Generate human-readable processing summary"""
    if not processing_methods:
        return "No processing information available"

    summaries = []
    for method in processing_methods:
        if method == "mistral_ocr_converted_pdf":
            summaries.append("🤖 Mistral AI: Converted to searchable PDF")
        elif method == "mistral_ocr_text_only":
            summaries.append("🤖 Mistral AI: Extracted text only")
        elif method == "mistral_ocr_failed":
            summaries.append("❌ Mistral AI: OCR processing failed")
        elif method == "standard_pdf":
            summaries.append("📄 Standard: Text-based PDF")
        elif method == "docx_standard":
            summaries.append("📄 Standard: Word document")
        elif method == "html_standard":
            summaries.append("🌐 Standard: HTML document")
        else:
            summaries.append(f"❓ Unknown: {method}")

    # Add OCR provider information
    if ocr_providers:
        provider_text = ", ".join(ocr_providers)
        summaries.append(f"🔍 OCR Provider: {provider_text}")

    return "; ".join(summaries)


def get_mistral_ocr_processor_info() -> dict:
    """
    Get information about Mistral AI OCR processor configuration

    Returns:
        Dictionary with OCR processor information
    """
    try:
        if not ocr_processor:
            return {
                "ocr_available": False,
                "error": "Mistral AI OCR processor not initialized - check API key",
            }

        api_stats = ocr_processor.get_api_usage_stats()
        output_info = ocr_processor.get_output_info("dummy.pdf")  # Get path info

        return {
            "output_directory": ocr_processor.output_dir,
            "ocr_available": True,
            "ocr_provider": "Mistral AI",
            "model_used": ocr_processor.model,
            "api_type": "OCR Process API",
            "supported_formats": api_stats.get("supported_formats", {}),
            "ocr_specific_formats": [
                ".pdf",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".bmp",
                ".tiff",
            ],
            "processing_capabilities": api_stats.get("features", []),
            "advantages": api_stats.get("advantages", []),
            "system_dependencies": "None required (API-based)",
            "naming_convention": {
                "converted_pdf": "filename_mistral_ocr_converted.pdf",
                "extracted_text": "filename_mistral_extracted_text.txt",
            },
            "api_methods": api_stats.get("api_methods", []),
        }
    except Exception as e:
        logger.error(f"Error getting Mistral OCR processor info: {e}")
        return {
            "output_directory": "./processed_documents",
            "ocr_available": False,
            "error": str(e),
        }


def list_processed_files() -> dict:
    """
    List all processed files in the OCR output directory

    Returns:
        Dictionary with processed file information
    """
    try:
        if not ocr_processor:
            return {
                "processed_files": [],
                "total_count": 0,
                "total_size_mb": 0,
                "error": "OCR processor not available",
            }

        output_dir = ocr_processor.output_dir

        if not os.path.exists(output_dir):
            return {"processed_files": [], "total_count": 0, "total_size_mb": 0}

        processed_files = []
        total_size = 0

        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                total_size += file_size

                processed_files.append(
                    {
                        "filename": filename,
                        "path": file_path,
                        "size_kb": round(file_size / 1024, 2),
                        "modified": os.path.getmtime(file_path),
                        "is_converted_pdf": filename.endswith(
                            "_mistral_ocr_converted.pdf"
                        ),
                        "is_extracted_text": filename.endswith(
                            "_mistral_extracted_text.txt"
                        ),
                        "ocr_provider": (
                            "Mistral AI"
                            if ("mistral" in filename.lower())
                            else "Unknown"
                        ),
                    }
                )

        return {
            "processed_files": processed_files,
            "total_count": len(processed_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "output_directory": output_dir,
            "ocr_provider": "Mistral AI",
        }

    except Exception as e:
        logger.error(f"Error listing processed files: {e}")
        return {"error": str(e)}
