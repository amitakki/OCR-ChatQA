import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
import fitz  # PyMuPDF
import os
import tempfile
from typing import List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRProcessor:
    def __init__(self, tesseract_path=None, output_dir="./processed_pdfs"):
        """
        Initialize OCR processor

        Args:
            tesseract_path: Path to tesseract executable (optional)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Create output directory if it doesn't exist

        self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(f"OCR output directory: {self.output_dir}")

        # Test tesseract availability
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR is available")
        except Exception as e:
            logger.error(f"Tesseract OCR not available: {e}")
            raise

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results

        Args:
            image: Input image as numpy array

        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)

        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Apply morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        return cleaned

    def extract_text_from_image(self, image: np.ndarray) -> str:
        """
        Extract text from image using OCR

        Args:
            image: Input image as numpy array

        Returns:
            Extracted text
        """
        # Preprocess the image
        processed_image = self.preprocess_image(image)

        # Configure OCR
        custom_config = r"--oem 3 --psm 6 -c preserve_interword_spaces=1"

        try:
            # Extract text
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

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
        """Generate output path for converted PDF

        Args:

            input_pdf_path: Path to input PDF

            custom_path: Custom output path (optional)

        Returns:

            Output path for converted PDF

        """

        if custom_path:

            # Use custom path if provided

            if os.path.isdir(custom_path):

                # If custom_path is a directory, generate filename

                base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]

                return os.path.join(custom_path, f"{base_name}_ocr_converted.txt")

            else:

                # Use custom_path as full file path

                return custom_path

        else:

            # Use default output directory

            base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]

            return os.path.join(self.output_dir, f"{base_name}_ocr_converted.pdf")

    def convert_scanned_pdf_to_text_pdf(
        self, input_pdf_path: str, output_pdf_path: str
    ) -> Tuple[bool, str]:
        """
        Convert scanned PDF to searchable text PDF

        Args:
            input_pdf_path: Path to input scanned PDF
            output_pdf_path: Path to output text PDF

        Returns:
            Tuple of (success: bool, output_path: str)
        """
        try:
            # Convert PDF pages to images
            logger.info(f"Converting PDF to images: {input_pdf_path}")
            pages = convert_from_path(input_pdf_path, dpi=300)

            # Create a new PDF document
            doc = fitz.open()

            for page_num, page_image in enumerate(pages):
                logger.info(f"Processing page {page_num + 1}/{len(pages)}")

                # Convert PIL image to numpy array
                img_array = np.array(page_image)

                # Extract text using OCR
                extracted_text = self.extract_text_from_image(img_array)

                # Create a new page in the PDF
                page = doc.new_page(width=page_image.width, height=page_image.height)

                # Add the original image as background
                with tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                ) as temp_img:
                    page_image.save(temp_img.name)
                    page.insert_image(
                        fitz.Rect(0, 0, page_image.width, page_image.height),
                        filename=temp_img.name,
                    )
                    os.unlink(temp_img.name)

                # Add extracted text as invisible text layer
                if extracted_text:
                    # Split text into lines and add with appropriate positioning
                    lines = extracted_text.split("\n")
                    y_position = 50

                    for line in lines:
                        if line.strip():
                            try:
                                page.insert_text(
                                    (50, y_position),
                                    line,
                                    fontsize=10,
                                    color=(1, 1, 1),  # White text (invisible)
                                    overlay=False,
                                )
                                y_position += 15
                            except Exception as e:
                                logger.warning(f"Failed to insert text line: {e}")
                                continue

            # Save the new PDF
            doc.save(output_pdf_path)
            doc.close()

            logger.info(
                f"Successfully converted scanned PDF to text PDF: {output_pdf_path}"
            )

            return True, output_pdf_path

        except Exception as e:
            logger.error(f"Error converting scanned PDF: {e}")
            return False, ""

    def save_extracted_text_to_file(
        self, input_pdf_path: str, output_text_path: str = None
    ) -> Tuple[bool, str]:
        """
        Extract text from scanned PDF and save to text file

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
                    self.output_dir, f"{base_name}_extracted_text.txt"
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
    ) -> dict:
        """
        Convert scanned PDF and save both searchable PDF and extracted text

        Args:

            input_pdf_path: Path to input scanned PD
            output_dir_custom: Custom output directory (optional)

        Returns:
            Dictionary with conversion results
        """
        results = {"success": False, "pdf_path": "", "text_path": "", "errors": []}
        try:
            # Use custom directory if provided
            if output_dir_custom:
                os.makedirs(output_dir_custom, exist_ok=True)
                base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
                pdf_output = os.path.join(
                    output_dir_custom, f"{base_name}_ocr_converted.pdf"
                )
                text_output = os.path.join(
                    output_dir_custom, f"{base_name}_extracted_text.txt"
                )
            else:
                pdf_output = None
                text_output = None

            # Convert to searchable PDF
            pdf_success, pdf_path = self.convert_scanned_pdf_to_text_pdf(
                input_pdf_path, pdf_output
            )
            if pdf_success:
                results["pdf_path"] = pdf_path
            else:
                results["errors"].append("Failed to create searchable PDF")

            # Extract and save text
            text_success, text_path = self.save_extracted_text_to_file(
                input_pdf_path, text_output
            )
            if text_success:
                results["text_path"] = text_path
            else:
                results["errors"].append("Failed to extract text to file")

            # Overall success if at least one conversion worked
            results["success"] = pdf_success or text_success

            if results["success"]:
                logger.info(
                    f"Conversion completed. PDF: {results['pdf_path']}, Text: {results['text_path']}"
                )

        except Exception as e:
            logger.error(f"Error in convert_and_save_both: {e}")
            results["errors"].append(str(e))

        return results

    def extract_text_from_scanned_pdf(self, pdf_path: str) -> str:
        """
        Extract text from scanned PDF using OCR

        Args:
            pdf_path: Path to scanned PDF

        Returns:
            Extracted text
        """
        try:
            # Convert PDF to images
            pages = convert_from_path(pdf_path, dpi=300)

            extracted_text = ""

            for page_num, page_image in enumerate(pages):
                logger.info(f"Extracting text from page {page_num + 1}/{len(pages)}")

                # Convert PIL image to numpy array
                img_array = np.array(page_image)

                # Extract text using OCR
                page_text = self.extract_text_from_image(img_array)

                if page_text:
                    extracted_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"

            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting text from scanned PDF: {e}")
            return ""

    def get_output_info(self, input_pdf_path: str) -> dict:
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
                self.output_dir, f"{base_name}_ocr_converted.pdf"
            ),
            "default_text_output": os.path.join(
                self.output_dir, f"{base_name}_extracted_text.txt"
            ),
            "output_directory": self.output_dir,
            "base_filename": base_name,
        }
