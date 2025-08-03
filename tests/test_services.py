"""Tests for service layer components with proper type safety."""

import pytest
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from PIL import Image
import io

from app.services import UserService, ImageService, DetectionService
from app.models import UserCreate, DiseaseType, DetectionStatus
from app.database import reset_db


@pytest.fixture()
def new_db():
    """Reset database for each test."""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def sample_user_data():
    """Sample user data for testing."""
    return UserCreate(name="Dr. John Smith", email="john.smith@hospital.com", phone="+1234567890")


@pytest.fixture()
def sample_image_bytes():
    """Generate sample image bytes for testing."""
    # Create a simple test image
    img = Image.new("RGB", (512, 512), color="gray")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    return img_bytes.getvalue()


class TestUserService:
    """Test UserService functionality."""

    def test_create_user(self, new_db, sample_user_data):
        """Test user creation."""
        user = UserService.create_user(sample_user_data)

        assert user.id is not None
        assert user.name == sample_user_data.name
        assert user.email == sample_user_data.email
        assert user.phone == sample_user_data.phone
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)

    def test_get_user(self, new_db, sample_user_data):
        """Test getting user by ID."""
        created_user = UserService.create_user(sample_user_data)
        assert created_user.id is not None

        retrieved_user = UserService.get_user(created_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.name == created_user.name

    def test_get_user_not_found(self, new_db):
        """Test getting non-existent user."""
        user = UserService.get_user(999)
        assert user is None

    def test_get_user_by_email(self, new_db, sample_user_data):
        """Test getting user by email."""
        created_user = UserService.create_user(sample_user_data)
        assert created_user.id is not None

        retrieved_user = UserService.get_user_by_email(sample_user_data.email)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == sample_user_data.email

    def test_get_user_by_email_not_found(self, new_db):
        """Test getting user by non-existent email."""
        user = UserService.get_user_by_email("nonexistent@example.com")
        assert user is None


class TestImageService:
    """Test ImageService functionality."""

    def test_save_uploaded_image(self, new_db, sample_user_data, sample_image_bytes):
        """Test saving uploaded image."""
        user = UserService.create_user(sample_user_data)
        assert user.id is not None

        image = ImageService.save_uploaded_image(sample_image_bytes, "chest_xray.jpg", user.id)

        assert image.id is not None
        assert image.original_filename == "chest_xray.jpg"
        assert image.filename.endswith(".jpg")
        assert image.file_size == len(sample_image_bytes)
        assert image.mime_type == "image/jpeg"
        assert image.width == 512
        assert image.height == 512
        assert image.user_id == user.id

        # Check file was saved
        assert Path(image.file_path).exists()

    def test_get_image(self, new_db, sample_user_data, sample_image_bytes):
        """Test getting image by ID."""
        user = UserService.create_user(sample_user_data)
        assert user.id is not None

        saved_image = ImageService.save_uploaded_image(sample_image_bytes, "test.jpg", user.id)
        assert saved_image.id is not None

        retrieved_image = ImageService.get_image(saved_image.id)

        assert retrieved_image is not None
        assert retrieved_image.id == saved_image.id
        assert retrieved_image.filename == saved_image.filename

    def test_get_image_not_found(self, new_db):
        """Test getting non-existent image."""
        image = ImageService.get_image(999)
        assert image is None

    def test_get_user_images(self, new_db, sample_user_data, sample_image_bytes):
        """Test getting all images for a user."""
        user = UserService.create_user(sample_user_data)
        assert user.id is not None

        # Save multiple images
        image1 = ImageService.save_uploaded_image(sample_image_bytes, "xray1.jpg", user.id)
        image2 = ImageService.save_uploaded_image(sample_image_bytes, "xray2.jpg", user.id)

        assert image1.id is not None
        assert image2.id is not None

        user_images = ImageService.get_user_images(user.id)

        assert len(user_images) == 2
        image_ids = [img.id for img in user_images]
        assert image1.id in image_ids
        assert image2.id in image_ids


class TestDetectionService:
    """Test DetectionService functionality."""

    def test_start_detection(self, new_db, sample_user_data, sample_image_bytes):
        """Test starting detection process."""
        user = UserService.create_user(sample_user_data)
        assert user.id is not None

        image = ImageService.save_uploaded_image(sample_image_bytes, "xray.jpg", user.id)
        assert image.id is not None

        detection = DetectionService.start_detection(image.id, "TestModel")

        assert detection.id is not None
        assert detection.xray_image_id == image.id
        assert detection.status == DetectionStatus.PENDING
        assert detection.model_name == "TestModel"
        assert detection.model_version == "1.0"
        assert detection.processing_started_at is not None
        assert detection.detected_disease is None
        assert detection.confidence_score is None
        assert not detection.is_disease_detected

    @pytest.mark.asyncio
    async def test_process_detection(self, new_db, sample_user_data, sample_image_bytes):
        """Test processing detection."""
        user = UserService.create_user(sample_user_data)
        assert user.id is not None

        image = ImageService.save_uploaded_image(sample_image_bytes, "xray.jpg", user.id)
        assert image.id is not None

        detection = DetectionService.start_detection(image.id)
        assert detection.id is not None

        # Process detection
        completed_detection = await DetectionService.process_detection(detection.id)

        assert completed_detection.status == DetectionStatus.COMPLETED
        assert completed_detection.detected_disease is not None
        assert completed_detection.confidence_score is not None
        assert isinstance(completed_detection.confidence_score, Decimal)
        assert completed_detection.processing_completed_at is not None
        assert completed_detection.processing_duration_seconds == 2
        assert completed_detection.detection_details is not None

        # Check if disease detection flag is consistent
        is_disease = completed_detection.detected_disease != DiseaseType.NORMAL
        assert completed_detection.is_disease_detected == is_disease

    def test_get_detection(self, new_db, sample_user_data, sample_image_bytes):
        """Test getting detection by ID."""
        user = UserService.create_user(sample_user_data)
        assert user.id is not None

        image = ImageService.save_uploaded_image(sample_image_bytes, "xray.jpg", user.id)
        assert image.id is not None

        created_detection = DetectionService.start_detection(image.id)
        assert created_detection.id is not None

        retrieved_detection = DetectionService.get_detection(created_detection.id)

        assert retrieved_detection is not None
        assert retrieved_detection.id == created_detection.id
        assert retrieved_detection.xray_image_id == image.id

    @pytest.mark.asyncio
    async def test_get_user_detection_history(self, new_db, sample_user_data, sample_image_bytes):
        """Test getting detection history for user."""
        user = UserService.create_user(sample_user_data)
        assert user.id is not None

        image1 = ImageService.save_uploaded_image(sample_image_bytes, "xray1.jpg", user.id)
        image2 = ImageService.save_uploaded_image(sample_image_bytes, "xray2.jpg", user.id)

        assert image1.id is not None
        assert image2.id is not None

        # Create and process detections
        detection1 = DetectionService.start_detection(image1.id)
        DetectionService.start_detection(image2.id)  # Second detection for history

        assert detection1.id is not None
        await DetectionService.process_detection(detection1.id)

        history = DetectionService.get_user_detection_history(user.id)

        assert len(history) == 2

        # Check result format
        for result in history:
            assert result.detection_id is not None
            assert result.xray_image_id is not None
            assert result.filename in ["xray1.jpg", "xray2.jpg"]
            assert result.status in [DetectionStatus.COMPLETED, DetectionStatus.PENDING]
            assert isinstance(result.created_at, datetime)


def test_simulate_ai_detection_returns_valid_disease():
    """Test that simulation returns valid disease types."""
    result = DetectionService._simulate_ai_detection()

    assert "disease" in result
    assert "confidence" in result
    assert "details" in result

    # Check disease type is valid
    assert result["disease"] in [
        DiseaseType.NORMAL,
        DiseaseType.PNEUMONIA,
        DiseaseType.TUBERCULOSIS,
        DiseaseType.COVID19,
        DiseaseType.LUNG_CANCER,
    ]

    # Check confidence is valid Decimal between 0 and 1
    confidence = result["confidence"]
    assert isinstance(confidence, Decimal)
    assert Decimal("0") <= confidence <= Decimal("1")

    # Check details structure
    details = result["details"]
    assert "regions_analyzed" in details
    assert "abnormal_regions" in details
    assert "processing_algorithm" in details
    assert "image_quality_score" in details
