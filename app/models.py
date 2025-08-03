from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum


class DetectionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiseaseType(str, Enum):
    PNEUMONIA = "pneumonia"
    TUBERCULOSIS = "tuberculosis"
    COVID19 = "covid19"
    LUNG_CANCER = "lung_cancer"
    NORMAL = "normal"


# Persistent models (stored in database)
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(unique=True, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    xray_images: List["XrayImage"] = Relationship(back_populates="user")


class XrayImage(SQLModel, table=True):
    __tablename__ = "xray_images"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255)
    original_filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int = Field(description="File size in bytes")
    mime_type: str = Field(max_length=100, default="image/jpeg")
    width: Optional[int] = Field(default=None, description="Image width in pixels")
    height: Optional[int] = Field(default=None, description="Image height in pixels")
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    user_id: int = Field(foreign_key="users.id")

    # Image metadata
    image_metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    user: User = Relationship(back_populates="xray_images")
    detections: List["DiseaseDetection"] = Relationship(back_populates="xray_image")


class DiseaseDetection(SQLModel, table=True):
    __tablename__ = "disease_detections"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    xray_image_id: int = Field(foreign_key="xray_images.id")
    status: DetectionStatus = Field(default=DetectionStatus.PENDING)

    # Detection results
    detected_disease: Optional[DiseaseType] = Field(default=None)
    confidence_score: Optional[Decimal] = Field(
        default=None, decimal_places=4, max_digits=6, description="Confidence score between 0.0000 and 1.0000"
    )
    is_disease_detected: bool = Field(default=False)

    # Processing information
    processing_started_at: Optional[datetime] = Field(default=None)
    processing_completed_at: Optional[datetime] = Field(default=None)
    processing_duration_seconds: Optional[int] = Field(default=None)

    # AI model information
    model_name: Optional[str] = Field(default=None, max_length=100)
    model_version: Optional[str] = Field(default=None, max_length=50)

    # Additional detection details
    detection_details: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSON), description="Additional detection metadata and results"
    )
    error_message: Optional[str] = Field(default=None, max_length=1000)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    xray_image: XrayImage = Relationship(back_populates="detections")


class DetectionHistory(SQLModel, table=True):
    __tablename__ = "detection_history"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    detection_id: int = Field(foreign_key="disease_detections.id")
    status_from: DetectionStatus
    status_to: DetectionStatus
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(default=None, max_length=500)


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    name: str = Field(max_length=100)
    email: str = Field(max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)


class UserUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)


class XrayImageCreate(SQLModel, table=False):
    filename: str = Field(max_length=255)
    original_filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int
    mime_type: str = Field(max_length=100, default="image/jpeg")
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)
    user_id: int
    image_metadata: Dict[str, Any] = Field(default={})


class DiseaseDetectionCreate(SQLModel, table=False):
    xray_image_id: int
    model_name: Optional[str] = Field(default=None, max_length=100)
    model_version: Optional[str] = Field(default=None, max_length=50)


class DiseaseDetectionUpdate(SQLModel, table=False):
    status: Optional[DetectionStatus] = Field(default=None)
    detected_disease: Optional[DiseaseType] = Field(default=None)
    confidence_score: Optional[Decimal] = Field(default=None, decimal_places=4, max_digits=6)
    is_disease_detected: Optional[bool] = Field(default=None)
    processing_completed_at: Optional[datetime] = Field(default=None)
    processing_duration_seconds: Optional[int] = Field(default=None)
    detection_details: Optional[Dict[str, Any]] = Field(default=None)
    error_message: Optional[str] = Field(default=None, max_length=1000)


class DetectionResult(SQLModel, table=False):
    detection_id: int
    xray_image_id: int
    filename: str
    status: DetectionStatus
    detected_disease: Optional[DiseaseType]
    confidence_score: Optional[Decimal]
    is_disease_detected: bool
    processing_completed_at: Optional[datetime]
    created_at: datetime
