"""Core services for lung disease detection application."""

import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from PIL import Image
import asyncio
import random

from sqlmodel import select
from app.database import get_session
from app.models import (
    User,
    UserCreate,
    XrayImage,
    XrayImageCreate,
    DiseaseDetection,
    DiseaseDetectionCreate,
    DiseaseDetectionUpdate,
    DetectionStatus,
    DiseaseType,
    DetectionResult,
)


# Directory for storing uploaded X-ray images
UPLOAD_DIR = Path("uploads/xray_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class UserService:
    """Service for managing users."""

    @staticmethod
    def create_user(user_data: UserCreate) -> User:
        """Create a new user."""
        with get_session() as session:
            user = User(**user_data.model_dump())
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    @staticmethod
    def get_user(user_id: int) -> Optional[User]:
        """Get user by ID."""
        with get_session() as session:
            return session.get(User, user_id)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email."""
        with get_session() as session:
            statement = select(User).where(User.email == email)
            return session.exec(statement).first()

    @staticmethod
    def get_all_users() -> List[User]:
        """Get all users."""
        with get_session() as session:
            statement = select(User).where(User.is_active)
            return list(session.exec(statement).all())


class ImageService:
    """Service for handling X-ray image operations."""

    @staticmethod
    def save_uploaded_image(file_content: bytes, original_filename: str, user_id: int) -> XrayImage:
        """Save uploaded image file and create database record."""
        # Generate unique filename
        file_hash = hashlib.md5(file_content).hexdigest()
        file_extension = Path(original_filename).suffix.lower()
        unique_filename = f"{file_hash}_{int(datetime.now().timestamp())}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename

        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Get image dimensions
        width, height = None, None
        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception as e:
            # Log but continue without dimensions
            import logging

            logging.info(f"Could not read image dimensions for {original_filename}: {e}")
            pass

        # Create database record
        image_data = XrayImageCreate(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=str(file_path),
            file_size=len(file_content),
            mime_type="image/jpeg" if file_extension in [".jpg", ".jpeg"] else "image/png",
            width=width,
            height=height,
            user_id=user_id,
            image_metadata={"upload_timestamp": datetime.now().isoformat()},
        )

        with get_session() as session:
            xray_image = XrayImage(**image_data.model_dump())
            session.add(xray_image)
            session.commit()
            session.refresh(xray_image)
            return xray_image

    @staticmethod
    def get_image(image_id: int) -> Optional[XrayImage]:
        """Get X-ray image by ID."""
        with get_session() as session:
            return session.get(XrayImage, image_id)

    @staticmethod
    def get_user_images(user_id: int) -> List[XrayImage]:
        """Get all X-ray images for a user."""
        with get_session() as session:
            statement = select(XrayImage).where(XrayImage.user_id == user_id)
            return list(session.exec(statement).all())

    @staticmethod
    def delete_image(image_id: int) -> bool:
        """Delete X-ray image and associated file."""
        with get_session() as session:
            image = session.get(XrayImage, image_id)
            if image is None:
                return False

            # Delete file from disk
            try:
                os.remove(image.file_path)
            except FileNotFoundError:
                import logging

                logging.info(f"File already deleted: {image.file_path}")
            except Exception as e:
                import logging

                logging.error(f"Error deleting file {image.file_path}: {e}")

            # Delete from database
            session.delete(image)
            session.commit()
            return True


class DetectionService:
    """Service for disease detection operations."""

    @staticmethod
    def start_detection(xray_image_id: int, model_name: str = "CNN_v1.0") -> DiseaseDetection:
        """Start disease detection process."""
        detection_data = DiseaseDetectionCreate(xray_image_id=xray_image_id, model_name=model_name, model_version="1.0")

        with get_session() as session:
            detection = DiseaseDetection(
                **detection_data.model_dump(), status=DetectionStatus.PENDING, processing_started_at=datetime.now()
            )
            session.add(detection)
            session.commit()
            session.refresh(detection)
            return detection

    @staticmethod
    async def process_detection(detection_id: int) -> DiseaseDetection:
        """Process disease detection (simulated AI analysis)."""
        with get_session() as session:
            detection = session.get(DiseaseDetection, detection_id)
            if detection is None:
                raise ValueError(f"Detection with ID {detection_id} not found")

            # Update status to processing
            detection.status = DetectionStatus.PROCESSING
            session.add(detection)
            session.commit()

        # Simulate AI processing time
        await asyncio.sleep(2)

        # Simulate AI detection results
        detection_result = DetectionService._simulate_ai_detection()

        # Update detection with results
        update_data = DiseaseDetectionUpdate(
            status=DetectionStatus.COMPLETED,
            detected_disease=detection_result["disease"],
            confidence_score=detection_result["confidence"],
            is_disease_detected=detection_result["disease"] != DiseaseType.NORMAL,
            processing_completed_at=datetime.now(),
            processing_duration_seconds=2,
            detection_details=detection_result["details"],
        )

        with get_session() as session:
            detection = session.get(DiseaseDetection, detection_id)
            if detection is None:
                raise ValueError(f"Detection with ID {detection_id} not found")

            for field, value in update_data.model_dump(exclude_unset=True).items():
                setattr(detection, field, value)

            detection.updated_at = datetime.now()
            session.add(detection)
            session.commit()
            session.refresh(detection)
            return detection

    @staticmethod
    def _simulate_ai_detection() -> Dict[str, Any]:
        """Simulate AI detection results."""
        # Random disease detection for demonstration
        diseases = [
            DiseaseType.NORMAL,
            DiseaseType.PNEUMONIA,
            DiseaseType.TUBERCULOSIS,
            DiseaseType.COVID19,
            DiseaseType.LUNG_CANCER,
        ]

        # Weight towards normal for realistic simulation
        weights = [0.6, 0.15, 0.1, 0.1, 0.05]
        detected_disease = random.choices(diseases, weights=weights)[0]

        # Generate confidence score based on disease type
        if detected_disease == DiseaseType.NORMAL:
            confidence = Decimal(str(round(random.uniform(0.7, 0.95), 4)))
        else:
            confidence = Decimal(str(round(random.uniform(0.6, 0.9), 4)))

        details = {
            "regions_analyzed": ["left_lung", "right_lung", "heart_area"],
            "abnormal_regions": [] if detected_disease == DiseaseType.NORMAL else ["lower_left_lobe"],
            "processing_algorithm": "Deep CNN with ResNet architecture",
            "image_quality_score": round(random.uniform(0.8, 1.0), 3),
        }

        return {"disease": detected_disease, "confidence": confidence, "details": details}

    @staticmethod
    def get_detection(detection_id: int) -> Optional[DiseaseDetection]:
        """Get detection by ID."""
        with get_session() as session:
            return session.get(DiseaseDetection, detection_id)

    @staticmethod
    def get_image_detections(xray_image_id: int) -> List[DiseaseDetection]:
        """Get all detections for an X-ray image."""
        with get_session() as session:
            statement = select(DiseaseDetection).where(DiseaseDetection.xray_image_id == xray_image_id)
            return list(session.exec(statement).all())

    @staticmethod
    def get_user_detection_history(user_id: int) -> List[DetectionResult]:
        """Get detection history for a user."""
        with get_session() as session:
            from sqlmodel import desc

            statement = (
                select(DiseaseDetection, XrayImage)
                .join(XrayImage)
                .where(XrayImage.user_id == user_id)
                .order_by(desc(DiseaseDetection.created_at))
            )
            results = session.exec(statement).all()

            return [
                DetectionResult(
                    detection_id=detection.id or 0,
                    xray_image_id=detection.xray_image_id,
                    filename=image.original_filename,
                    status=detection.status,
                    detected_disease=detection.detected_disease,
                    confidence_score=detection.confidence_score,
                    is_disease_detected=detection.is_disease_detected,
                    processing_completed_at=detection.processing_completed_at,
                    created_at=detection.created_at,
                )
                for detection, image in results
            ]

    @staticmethod
    async def mark_detection_failed(detection_id: int, error_message: str) -> DiseaseDetection:
        """Mark detection as failed with error message."""
        with get_session() as session:
            detection = session.get(DiseaseDetection, detection_id)
            if detection is None:
                raise ValueError(f"Detection with ID {detection_id} not found")

            detection.status = DetectionStatus.FAILED
            detection.error_message = error_message
            detection.processing_completed_at = datetime.now()
            detection.updated_at = datetime.now()

            session.add(detection)
            session.commit()
            session.refresh(detection)
            return detection
