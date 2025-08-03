import os
import tempfile
import time
import logging
from typing import List, Tuple, Dict, Any
from pdf2image import convert_from_path
from PIL import Image
import fitz  # PyMuPDF
from mistralai import Mistral
from mistralai.models import UserMessage, ImageURLChunk, DocumentURLChunk, TextChunk
import base64
import mimetypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MistralOCRProcessor:
    def __init__(self, api_key: str = None, output_dir: str = "./processed_documents"):
        """
        Initialize Mistral AI OCR processor using the ocr.process API

        Args:
            api_key: Mistral AI API key
            output_dir: Directory to save converted text PDFs
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Mistral API key is required. Set MISTRAL_API_KEY environment variable or pass api_key parameter."
            )

        # Initialize Mistral client
        self.client = Mistral(api_key=self.api_key)
        self.model = "mistral-ocr-latest"  # Mistral's vision model for OCR

        # Create output directory if it doesn't exist
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Mistral AI OCR output directory: {self.output_dir}")

        # Test API availability
        self._test_api_connection()

    def _test_api_connection(self):
        """Test Mistral API connection"""
        if not self.api_key:
            raise ValueError("Mistral API key is not set")
        logger.info("Testing Mistral AI API connection...")

        try:
            self.client.models.list()  # Simple call to check API availability
            logger.info("Mistral AI API connection successful")
        except Exception as e:
            logger.error(f"Mistral AI API not available: {e}")
            raise

    def _encode_file_to_base64(self, file_path: str) -> str:
        """
        Encode file to base64 for URL chunks

        Args:
            file_path: Path to the file

        Returns:
            Base64 encoded file data with data URL format
        """
        try:
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                # Default MIME types for common files
                ext = os.path.splitext(file_path)[1].lower()
                mime_types = {
                    ".pdf": "application/pdf",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".bmp": "image/bmp",
                    ".tiff": "image/tiff",
                }
                mime_type = mime_types.get(ext, "application/octet-stream")

            # Read and encode file
            with open(file_path, "rb") as file:
                file_data = file.read()
                base64_data = base64.b64encode(file_data).decode("utf-8")
                return f"data:{mime_type};base64,{base64_data}"

        except Exception as e:
            logger.error(f"Failed to encode file to base64: {e}")
            raise

    def _extract_text_using_ocr_process(
        self, file_path: str, is_pdf: bool = False
    ) -> str:
        """
        Extract text from file using Mistral AI OCR process API

        Args:
            file_path: Path to the file
            is_pdf: Whether the file is a PDF

        Returns:
            Extracted text
        """
        try:
            # Encode file to base64 data URL
            data_url = self._encode_file_to_base64(file_path)

            if is_pdf:
                # Use DocumentURLChunk for PDF files
                content_chunk = DocumentURLChunk(document_url=data_url)
            else:
                # Use ImageURLChunk for image files
                content_chunk = ImageURLChunk(image_url=data_url)

            # Use the OCR process API
            ocr_response = self.client.ocr.process(
                model=self.model,
                document=content_chunk,
                include_image_base64=True
            )

            if ocr_response and ocr_response.pages:
                raw_content = []
                for page in ocr_response.pages:
                    page_content = page.markdown.strip()
                    if page_content:
                        raw_content.append(page_content)
                return "\n\n".join(raw_content)
            else:
                logger.error("Mistral AI OCR process returned empty response")
                return ""

        except Exception as e:
            logger.error(f"Mistral AI OCR process extraction failed: {e}")
            return ""

    def _extract_text_from_image_file(self, image_path: str) -> str:
        """
        Extract text from image file using Mistral AI OCR process

        Args:
            image_path: Path to image file

        Returns:
            Extracted text
        """
        return self._extract_text_using_ocr_process(image_path, is_pdf=False)

    def _extract_text_from_pdf_direct(self, pdf_path: str) -> str:
        """
        Extract text from PDF using Mistral AI OCR process directly

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        return self._extract_text_using_ocr_process(pdf_path, is_pdf=True)

    def is_pdf_scanned(self, pdf_path: str) -> bool:
        """
        Check if PDF is scanned (image-based) or text-based

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if PDF is scanned, False if text-based
        """
        try:
            doc = fitz.open(pdf_path)

            # Check first few pages
            pages_to_check = min(3, len(doc))
            text_found = False

            for page_num in range(pages_to_check):
                page = doc[page_num]
                text = page.get_text().strip()

                if text and len(text) > 50:  # Arbitrary threshold
                    text_found = True
                    break

            doc.close()
            return not text_found

        except Exception as e:
            logger.error(f"Error checking PDF type: {e}")
            return False

    def generate_output_path(self, input_pdf_path: str, custom_path: str = None) -> str:
        """
        Generate output path for converted PDF

        Args:
            input_pdf_path: Path to input PDF
            custom_path: Custom output path (optional)

        Returns:
            Output path for converted PDF
        """
        if custom_path:
            if os.path.isdir(custom_path):
                base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
                return os.path.join(
                    custom_path, f"{base_name}_mistral_ocr_converted.pdf"
                )
            else:
                return custom_path
        else:
            base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
            return os.path.join(
                self.output_dir, f"{base_name}_mistral_ocr_converted.pdf"
            )

    def save_extracted_text_to_file(
        self, input_pdf_path: str, output_text_path: str = None
    ) -> Tuple[bool, str]:
        """
        Extract text from scanned PDF and save to text file using Mistral AI OCR process

        Args:
            input_pdf_path: Path to input scanned PDF
            output_text_path: Path to save extracted text (optional)

        Returns:
            Tuple of (success: bool, output_path: str)
        """
        try:
            # Generate output path for text file
            if not output_text_path:
                base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
                output_text_path = os.path.join(
                    self.output_dir, f"{base_name}_mistral_extracted_text.txt"
                )

            # Ensure output directory exists
            output_dir = os.path.dirname(output_text_path)
            os.makedirs(output_dir, exist_ok=True)

            # Extract text
            extracted_text = self.extract_text_from_scanned_pdf(input_pdf_path)

            if extracted_text:
                # Save to text file
                with open(output_text_path, "w", encoding="utf-8") as f:
                    f.write(extracted_text)

                logger.info(f"Text extracted and saved to: {output_text_path}")
                return True, output_text_path
            else:
                logger.warning("No text could be extracted from the PDF")
                return False, ""

        except Exception as e:
            logger.error(f"Error saving extracted text: {e}")
            return False, ""

    def convert_and_save_both(
        self, input_pdf_path: str, output_dir_custom: str = None
    ) -> Dict[str, Any]:
        """
        Convert scanned PDF and save extracted text using Mistral AI OCR process

        Args:
            input_pdf_path: Path to input scanned PDF
            output_dir_custom: Custom output directory (optional)

        Returns:
            Dictionary with conversion results
        """
        results = {
            "success": False,
            "text_path": "",
            "errors": [],
            "processing_time": 0.0,
            "pages_processed": 0,
            "api_calls_made": 0,
            "successful_pages": 0,
        }

        try:
            start_time = time.time()

            # Use custom directory if provided
            if output_dir_custom:
                os.makedirs(output_dir_custom, exist_ok=True)
                base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
                pdf_output = os.path.join(
                    output_dir_custom, f"{base_name}_mistral_ocr_converted.pdf"
                )
                text_output = os.path.join(
                    output_dir_custom, f"{base_name}_mistral_extracted_text.txt"
                )
            else:
                pdf_output = None
                text_output = None

            # Count pages for statistics
            try:
                pages = convert_from_path(input_pdf_path, dpi=200)
                results["pages_processed"] = len(pages)
                # API calls depend on method used (1 for direct PDF, or 1 per page)
                results["api_calls_made"] = 1  # Will be updated based on actual method
            except Exception as e:
                logger.warning(f"Could not count pages: {e}")

            # Extract and save text
            text_success, text_path = self.save_extracted_text_to_file(
                input_pdf_path, text_output
            )
            if text_success:
                results["text_path"] = text_path
            else:
                results["errors"].append(
                    "Failed to extract text to file with Mistral AI OCR process"
                )

            # Overall success if at least one conversion worked
            results["success"] = text_success
            results["processing_time"] = time.time() - start_time

            if results["success"]:
                logger.info(
                    f"Mistral AI OCR process conversion completed in {results['processing_time']:.2f}s"
                )
                logger.info(f"PDF: {results['pdf_path']}, Text: {results['text_path']}")

        except Exception as e:
            logger.error(
                f"Error in convert_and_save_both with Mistral AI OCR process: {e}"
            )
            results["errors"].append(str(e))
            results["processing_time"] = (
                time.time() - start_time if "start_time" in locals() else 0.0
            )

        return results

    def extract_text_from_scanned_pdf(self, pdf_path: str) -> str:
        """
        Extract text from scanned PDF using Mistral AI OCR process

        Args:
            pdf_path: Path to scanned PDF

        Returns:
            Extracted text
        """
        try:
            # First try direct PDF processing
            logger.info(
                f"Attempting direct PDF text extraction using OCR process: {pdf_path}"
            )
            direct_text = self._extract_text_from_pdf_direct(pdf_path)

            if direct_text and len(direct_text.strip()) > 100:
                logger.info("Direct PDF OCR process successful")
                return direct_text

            # Fallback to page-by-page processing
            logger.info(
                "Direct PDF processing insufficient, falling back to page-by-page"
            )

            # Convert PDF to images
            pages = convert_from_path(pdf_path, dpi=200)
            extracted_text = ""

            for page_num, page_image in enumerate(pages):
                logger.info(
                    f"Extracting text from page {page_num + 1}/{len(pages)} using Mistral AI OCR process"
                )

                try:
                    # Save page as temporary image file
                    with tempfile.NamedTemporaryFile(
                        suffix=".png", delete=False
                    ) as temp_img:
                        page_image.save(temp_img.name, "PNG")
                        temp_img_path = temp_img.name

                    try:
                        # Extract text using Mistral AI OCR process
                        page_text = self._extract_text_from_image_file(temp_img_path)

                        if page_text:
                            extracted_text += (
                                f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                            )

                    finally:
                        # Clean up temporary image file
                        if os.path.exists(temp_img_path):
                            os.unlink(temp_img_path)

                    # Rate limiting
                    time.sleep(0.2)

                except Exception as e:
                    logger.error(
                        f"Failed to extract text from page {page_num + 1}: {e}"
                    )
                    continue

            return extracted_text

        except Exception as e:
            logger.error(
                f"Error extracting text from scanned PDF with Mistral AI OCR process: {e}"
            )
            return ""

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image file using Mistral AI OCR process

        Args:
            image_path: Path to image file

        Returns:
            Extracted text
        """
        try:
            logger.info(
                f"Extracting text from image using Mistral AI OCR process: {image_path}"
            )
            return self._extract_text_from_image_file(image_path)
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return ""

    def get_output_info(self, input_pdf_path: str) -> Dict[str, str]:
        """
        Get information about output paths that would be generated

        Args:
            input_pdf_path: Path to input PDF

        Returns:
            Dictionary with output path information
        """
        base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]

        return {
            "default_pdf_output": os.path.join(
                self.output_dir, f"{base_name}_mistral_ocr_converted.pdf"
            ),
            "default_text_output": os.path.join(
                self.output_dir, f"{base_name}_mistral_extracted_text.txt"
            ),
            "output_directory": self.output_dir,
            "base_filename": base_name,
            "ocr_provider": "Mistral AI OCR Process",
            "model_used": self.model,
            "api_type": "OCR Process API",
        }

    def get_api_usage_stats(self) -> Dict[str, Any]:
        """
        Get API usage statistics

        Returns:
            Dictionary with API usage information
        """
        return {
            "provider": "Mistral AI",
            "api_type": "OCR Process API",
            "model": self.model,
            "features": [
                "Direct PDF OCR processing",
                "Image OCR processing",
                "DocumentURLChunk support",
                "ImageURLChunk support",
                "Multi-language support",
                "High accuracy OCR",
            ],
            "advantages": [
                "No system dependencies required",
                "Superior accuracy with OCR process API",
                "Direct PDF processing capability",
                "Efficient handling of both PDFs and images",
                "Built-in rate limiting and error handling",
                "Base64 encoding for secure transmission",
            ],
            "supported_formats": {
                "documents": ["PDF"],
                "images": ["PNG", "JPEG", "JPG", "GIF", "BMP", "TIFF"],
            },
            "api_methods": [
                "client.ocr.process with DocumentURLChunk for PDFs",
                "client.ocr.process with ImageURLChunk for images",
            ],
        }
