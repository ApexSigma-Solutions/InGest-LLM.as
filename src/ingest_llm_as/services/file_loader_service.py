"""
File Loader Service for InGest-LLM.as

Handles conversion of binary file uploads (bytes) into extracted text strings.
Supports PDF, DOCX, and HTML formats using newly installed libraries.
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional, Union

import pypdf
from docx import Document
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FileLoaderService:
    """
    Service for loading and extracting text from various file formats.

    Supports:
    - PDF files (using pypdf)
    - DOCX files (using python-docx)
    - HTML files (using BeautifulSoup4)

    The extracted text is suitable for feeding into DocumentParser.
    """

    # MIME type mappings
    MIME_TYPE_PDF = "application/pdf"
    MIME_TYPE_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    MIME_TYPE_HTML = "text/html"

    def __init__(self) -> None:
        """Initialize FileLoaderService."""
        logger.info("FileLoaderService initialized")

    def _detect_mime_type(self, file_obj: Optional[dict] = None, bytes_data: Optional[bytes] = None) -> str:
        """
        Detect MIME type from file object or bytes data.

        Args:
            file_obj: File object with 'content_type' or 'type' field
            bytes_data: Raw bytes data

        Returns:
            MIME type string
        """
        # Try to get MIME type from file object first
        if file_obj:
            mime_type = file_obj.get("content_type") or file_obj.get("type")
            if mime_type:
                logger.debug(f"Detected MIME type from file object: {mime_type}")
                return mime_type

        # Fallback to bytes data inspection (basic detection)
        if bytes_data:
            # Check for PDF magic bytes
            if bytes_data.startswith(b"%PDF"):
                logger.debug("Detected PDF from bytes data")
                return self.MIME_TYPE_PDF

            # Check for DOCX magic bytes (PK header)
            if bytes_data.startswith(b"PK\x03\x04"):
                logger.debug("Detected DOCX from bytes data")
                return self.MIME_TYPE_DOCX

            # Check for HTML magic bytes
            if bytes_data.startswith(b"<") or bytes_data.startswith(b"<!DOCTYPE"):
                logger.debug("Detected HTML from bytes data")
                return self.MIME_TYPE_HTML

        # Default fallback
        logger.warning("Could not detect MIME type, defaulting to text/plain")
        return "text/plain"

    def _extract_pdf(self, bytes_data: bytes) -> str:
        """
        Extract text from PDF bytes using pypdf.

        Args:
            bytes_data: PDF file content as bytes

        Returns:
            Extracted text string
        """
        try:
            pdf_file = BytesIO(bytes_data)
            pdf_reader = pypdf.PdfReader(pdf_file)

            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            extracted_text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(text_parts)} pages from PDF")
            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            raise ValueError(f"PDF extraction failed: {e}")

    def _extract_docx(self, bytes_data: bytes) -> str:
        """
        Extract text from DOCX bytes using python-docx.

        Args:
            bytes_data: DOCX file content as bytes

        Returns:
            Extracted text string
        """
        try:
            docx_file = BytesIO(bytes_data)
            doc = Document(docx_file)

            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text_parts.append(paragraph.text)

            extracted_text = "\n".join(text_parts)
            logger.info(f"Extracted {len(text_parts)} paragraphs from DOCX")
            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting DOCX: {e}")
            raise ValueError(f"DOCX extraction failed: {e}")

    def _extract_html(self, bytes_data: bytes) -> str:
        """
        Extract text from HTML bytes using BeautifulSoup4.

        Args:
            bytes_data: HTML file content as bytes

        Returns:
            Extracted text string
        """
        try:
            html_content = bytes_data.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            extracted_text = soup.get_text(separator="\n", strip=True)
            # Clean up whitespace
            extracted_text = "\n".join(line.strip() for line in extracted_text.split("\n") if line.strip())

            logger.info(f"Extracted text from HTML ({len(extracted_text)} characters)")
            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting HTML: {e}")
            raise ValueError(f"HTML extraction failed: {e}")

    def load_from_file(self, file_obj: dict) -> str:
        """
        Load and extract text from a file object.

        Args:
            file_obj: File upload object with 'content' (bytes) and 'content_type' fields

        Returns:
            Extracted text string

        Raises:
            ValueError: If file format is not supported
        """
        # Get bytes data
        bytes_data = file_obj.get("content")
        if not bytes_data:
            raise ValueError("File object missing 'content' field")

        # Detect MIME type
        mime_type = self._detect_mime_type(file_obj=file_obj, bytes_data=bytes_data)

        # Route to appropriate extractor
        if mime_type == self.MIME_TYPE_PDF:
            return self._extract_pdf(bytes_data)
        elif mime_type == self.MIME_TYPE_DOCX:
            return self._extract_docx(bytes_data)
        elif mime_type == self.MIME_TYPE_HTML:
            return self._extract_html(bytes_data)
        else:
            raise ValueError(f"Unsupported MIME type: {mime_type}")

    def load_from_bytes(self, bytes_data: bytes, mime_type: Optional[str] = None) -> str:
        """
        Load and extract text from raw bytes data.

        Args:
            bytes_data: Raw file content as bytes
            mime_type: Optional MIME type override

        Returns:
            Extracted text string

        Raises:
            ValueError: If file format is not supported
        """
        if not bytes_data:
            raise ValueError("bytes_data cannot be empty")

        # Use provided MIME type or detect from bytes
        detected_mime = mime_type or self._detect_mime_type(bytes_data=bytes_data)

        # Route to appropriate extractor
        if detected_mime == self.MIME_TYPE_PDF:
            return self._extract_pdf(bytes_data)
        elif detected_mime == self.MIME_TYPE_DOCX:
            return self._extract_docx(bytes_data)
        elif detected_mime == self.MIME_TYPE_HTML:
            return self._extract_html(bytes_data)
        else:
            raise ValueError(f"Unsupported MIME type: {detected_mime}")

    def load(self, file_input: Union[dict, bytes], mime_type: Optional[str] = None) -> str:
        """
        Main entry point for loading files.

        Accepts either a file object (from upload) or raw bytes data.

        Args:
            file_input: File object with 'content' field OR raw bytes data
            mime_type: Optional MIME type override

        Returns:
            Clean text string suitable for DocumentParser

        Raises:
            ValueError: If file format is not supported or input is invalid
        """
        if isinstance(file_input, dict):
            # File object from upload
            return self.load_from_file(file_input)
        elif isinstance(file_input, bytes):
            # Raw bytes data
            return self.load_from_bytes(file_input, mime_type=mime_type)
        else:
            raise ValueError(f"Unsupported input type: {type(file_input)}")
