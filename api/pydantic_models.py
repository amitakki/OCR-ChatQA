from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import List, Optional


class ModelName(str, Enum):
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMENI_2_5_FLASH = "gemini-2.5-flash"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QueryInput(BaseModel):
    question: str
    session_id: str = Field(default=None)
    model: ModelName = Field(default=ModelName.GEMENI_2_5_FLASH)


class QueryResponse(BaseModel):
    answer: str
    session_id: str
    model: ModelName
    processing_time: Optional[float] = Field(
        default=None, description="Response generation time in seconds"
    )


class DocumentInfo(BaseModel):
    id: int
    filename: str
    upload_timestamp: datetime
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    file_size: Optional[int] = Field(default=None, description="File size in bytes")


class DeleteFileRequest(BaseModel):
    file_id: int


class ProcessingStatsResponse(BaseModel):
    file_id: int
    chunk_count: int
    processing_methods: List[str]
    filename: str


class DocumentStatusResponse(BaseModel):
    file_id: int
    status: ProcessingStatus
    message: Optional[str] = None


class UploadResponse(BaseModel):
    message: str
    file_id: int
    status: ProcessingStatus


class HealthResponse(BaseModel):
    status: str
    ocr_enabled: bool
    supported_formats: List[str]
    features: List[str]


class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
