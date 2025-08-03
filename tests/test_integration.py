"""Integration tests for the lung disease detection system."""

import pytest
from pathlib import Path
from PIL import Image
import io

from app.services import UserService, ImageService, DetectionService
from app.models import UserCreate, DetectionStatus, DiseaseType
from app.database import reset_db


@pytest.fixture()
def new_db():
    """Reset database for each test."""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def sample_xray_image():
    """Create a sample X-ray image for testing."""
    # Create a realistic chest X-ray sized image
    img = Image.new("L", (1024, 1024), color=128)  # Grayscale
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


class TestLungDiseaseDetectionWorkflow:
    """Test the complete workflow from user creation to detection results."""

    def test_complete_user_workflow(self, new_db, sample_xray_image):
        """Test complete user workflow: create user, upload image, get results."""
        # Step 1: Create user
        user_data = UserCreate(name="Dr. Medical Expert", email="expert@hospital.com", phone="+1-555-0123")
        user = UserService.create_user(user_data)
        assert user.id is not None

        # Step 2: Upload X-ray image
        image = ImageService.save_uploaded_image(sample_xray_image, "patient_xray.png", user.id)
        assert image.id is not None
        assert Path(image.file_path).exists()

        # Step 3: Start detection
        detection = DetectionService.start_detection(image.id, "ResNet50_v2.1")
        assert detection.id is not None
        assert detection.status == DetectionStatus.PENDING
        assert detection.model_name == "ResNet50_v2.1"

        # Step 4: Verify detection history before processing
        history_before = DetectionService.get_user_detection_history(user.id)
        assert len(history_before) == 1
        assert history_before[0].status == DetectionStatus.PENDING

        # Verify we can retrieve the detection
        retrieved_detection = DetectionService.get_detection(detection.id)
        assert retrieved_detection is not None
        assert retrieved_detection.id == detection.id

    @pytest.mark.asyncio
    async def test_complete_detection_processing(self, new_db, sample_xray_image):
        """Test complete detection processing workflow."""
        # Create user and image
        user = UserService.create_user(UserCreate(name="Test Doctor", email="doctor@test.com"))
        assert user.id is not None

        image = ImageService.save_uploaded_image(sample_xray_image, "test_chest_xray.png", user.id)
        assert image.id is not None

        # Start and process detection
        detection = DetectionService.start_detection(image.id)
        assert detection.id is not None

        # Process the detection
        completed_detection = await DetectionService.process_detection(detection.id)

        # Verify processing results
        assert completed_detection.status == DetectionStatus.COMPLETED
        assert completed_detection.detected_disease is not None
        assert completed_detection.confidence_score is not None
        assert completed_detection.processing_completed_at is not None
        assert completed_detection.detection_details is not None

        # Verify disease detection consistency
        is_disease_detected = completed_detection.detected_disease != DiseaseType.NORMAL
        assert completed_detection.is_disease_detected == is_disease_detected

        # Verify detection details structure
        details = completed_detection.detection_details
        assert "regions_analyzed" in details
        assert "abnormal_regions" in details
        assert "processing_algorithm" in details
        assert "image_quality_score" in details

        # Verify history includes completed detection
        history = DetectionService.get_user_detection_history(user.id)
        assert len(history) == 1
        assert history[0].status == DetectionStatus.COMPLETED
        assert history[0].confidence_score is not None

    @pytest.mark.asyncio
    async def test_multiple_detections_for_user(self, new_db, sample_xray_image):
        """Test multiple detections for the same user."""
        # Create user
        user = UserService.create_user(UserCreate(name="Multi Test User", email="multitest@example.com"))
        assert user.id is not None

        # Upload multiple images
        image1 = ImageService.save_uploaded_image(sample_xray_image, "xray1.png", user.id)
        image2 = ImageService.save_uploaded_image(sample_xray_image, "xray2.png", user.id)
        image3 = ImageService.save_uploaded_image(sample_xray_image, "xray3.png", user.id)

        assert image1.id is not None
        assert image2.id is not None
        assert image3.id is not None

        # Start detections
        detection1 = DetectionService.start_detection(image1.id)
        detection2 = DetectionService.start_detection(image2.id)
        detection3 = DetectionService.start_detection(image3.id)

        assert detection1.id is not None
        assert detection2.id is not None
        assert detection3.id is not None

        # Process some detections
        await DetectionService.process_detection(detection1.id)
        await DetectionService.process_detection(detection2.id)
        # Leave detection3 pending

        # Verify history
        history = DetectionService.get_user_detection_history(user.id)
        assert len(history) == 3

        # Count statuses
        completed_count = len([h for h in history if h.status == DetectionStatus.COMPLETED])
        pending_count = len([h for h in history if h.status == DetectionStatus.PENDING])

        assert completed_count == 2
        assert pending_count == 1

    @pytest.mark.asyncio
    async def test_detection_failure_handling(self, new_db, sample_xray_image):
        """Test detection failure handling."""
        # Create user and image
        user = UserService.create_user(UserCreate(name="Failure Test User", email="failure@test.com"))
        assert user.id is not None

        image = ImageService.save_uploaded_image(sample_xray_image, "test.png", user.id)
        assert image.id is not None

        # Start detection
        detection = DetectionService.start_detection(image.id)
        assert detection.id is not None

        # Simulate failure
        error_message = "Processing failed due to corrupted image data"
        failed_detection = await DetectionService.mark_detection_failed(detection.id, error_message)

        # Verify failure state
        assert failed_detection.status == DetectionStatus.FAILED
        assert failed_detection.error_message == error_message
        assert failed_detection.processing_completed_at is not None

        # Verify in history
        history = DetectionService.get_user_detection_history(user.id)
        assert len(history) == 1
        assert history[0].status == DetectionStatus.FAILED

    def test_user_data_isolation(self, new_db, sample_xray_image):
        """Test that user data is properly isolated."""
        # Create two users
        user1 = UserService.create_user(UserCreate(name="User 1", email="user1@test.com"))
        user2 = UserService.create_user(UserCreate(name="User 2", email="user2@test.com"))

        assert user1.id is not None
        assert user2.id is not None

        # Upload images for each user
        image1_u1 = ImageService.save_uploaded_image(sample_xray_image, "u1_xray1.png", user1.id)
        image2_u1 = ImageService.save_uploaded_image(sample_xray_image, "u1_xray2.png", user1.id)
        image1_u2 = ImageService.save_uploaded_image(sample_xray_image, "u2_xray1.png", user2.id)

        assert image1_u1.id is not None
        assert image2_u1.id is not None
        assert image1_u2.id is not None

        # Start detections
        DetectionService.start_detection(image1_u1.id)
        DetectionService.start_detection(image2_u1.id)
        DetectionService.start_detection(image1_u2.id)

        # Verify isolation
        user1_images = ImageService.get_user_images(user1.id)
        user2_images = ImageService.get_user_images(user2.id)

        assert len(user1_images) == 2
        assert len(user2_images) == 1

        user1_history = DetectionService.get_user_detection_history(user1.id)
        user2_history = DetectionService.get_user_detection_history(user2.id)

        assert len(user1_history) == 2
        assert len(user2_history) == 1

        # Verify filenames are correct for each user
        user1_filenames = [h.filename for h in user1_history]
        user2_filenames = [h.filename for h in user2_history]

        assert "u1_xray1.png" in user1_filenames
        assert "u1_xray2.png" in user1_filenames
        assert "u2_xray1.png" in user2_filenames

        # Ensure no cross-contamination
        assert "u2_xray1.png" not in user1_filenames
        assert "u1_xray1.png" not in user2_filenames

    def test_file_storage_management(self, new_db, sample_xray_image):
        """Test file storage and cleanup."""
        # Create user and upload image
        user = UserService.create_user(UserCreate(name="Storage Test", email="storage@test.com"))
        assert user.id is not None

        image = ImageService.save_uploaded_image(sample_xray_image, "storage_test.png", user.id)
        assert image.id is not None

        # Verify file exists
        file_path = Path(image.file_path)
        assert file_path.exists()
        assert file_path.stat().st_size > 0

        # Delete image and verify cleanup
        result = ImageService.delete_image(image.id)
        assert result is True

        # Verify file is deleted
        assert not file_path.exists()

        # Verify database record is deleted
        deleted_image = ImageService.get_image(image.id)
        assert deleted_image is None


class TestDiseaseDetectionLogic:
    """Test the disease detection simulation logic."""

    def test_detection_results_are_consistent(self):
        """Test that detection results follow expected patterns."""
        # Run multiple simulations
        results = [DetectionService._simulate_ai_detection() for _ in range(100)]

        # All results should have required fields
        for result in results:
            assert "disease" in result
            assert "confidence" in result
            assert "details" in result

            # Confidence should be reasonable
            confidence = result["confidence"]
            assert 0.0 <= float(confidence) <= 1.0

            # Normal results should have no abnormal regions
            if result["disease"] == DiseaseType.NORMAL:
                assert result["details"]["abnormal_regions"] == []

        # Should get a mix of results (not all the same)
        diseases = [r["disease"] for r in results]
        unique_diseases = set(diseases)

        # With 100 runs, we should get at least 2 different results
        assert len(unique_diseases) >= 2

        # Normal should be most common (weighted at 60%)
        normal_count = diseases.count(DiseaseType.NORMAL)
        assert normal_count > 30  # Should be roughly 60% of 100

    def test_all_disease_types_can_be_detected(self):
        """Test that all disease types can potentially be detected."""
        # Run many simulations to increase chance of getting all types
        results = [DetectionService._simulate_ai_detection() for _ in range(500)]
        diseases = [r["disease"] for r in results]
        unique_diseases = set(diseases)

        # Should be able to detect various diseases
        assert DiseaseType.NORMAL in unique_diseases
        assert len(unique_diseases) >= 3  # Should get at least 3 different types
