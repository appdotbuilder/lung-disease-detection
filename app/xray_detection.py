"""Main X-ray detection UI module."""

import asyncio
from typing import Optional
from nicegui import ui, events, app
from app.services import UserService, ImageService, DetectionService
from app.models import User, DiseaseType, DetectionStatus


def create():
    """Create X-ray detection UI module."""

    # Apply modern theme
    ui.colors(
        primary="#2563eb",  # Professional blue
        secondary="#64748b",  # Subtle gray
        accent="#10b981",  # Success green
        positive="#10b981",
        negative="#ef4444",  # Error red
        warning="#f59e0b",  # Warning amber
        info="#3b82f6",  # Info blue
    )

    @ui.page("/detection")
    async def detection_page():
        """Main detection page."""
        await ui.context.client.connected()

        # Get or create user from session
        user = await get_or_create_user()
        if user is None:
            ui.navigate.to("/user-setup")
            return

        if user.id is None:
            ui.navigate.to("/user-setup")
            return

        # Store user in tab storage
        app.storage.tab["current_user_id"] = user.id

        # Page layout
        with ui.column().classes("w-full max-w-4xl mx-auto p-6 gap-6"):
            # Header
            ui.label("🫁 Deteksi Penyakit Paru-paru dari X-ray").classes(
                "text-3xl font-bold text-center text-gray-800 mb-2"
            )
            ui.label("Upload citra X-ray paru-paru untuk mendapatkan deteksi otomatis penyakit").classes(
                "text-lg text-center text-gray-600 mb-8"
            )

            # User info
            with ui.card().classes("p-4 bg-blue-50 border-l-4 border-blue-500"):
                ui.label(f"👤 Pengguna: {user.name}").classes("font-semibold text-blue-800")
                ui.label(f"📧 Email: {user.email}").classes("text-blue-600")

            # Upload section
            await create_upload_section(user.id)

            # Results section
            results_container = ui.column().classes("w-full")
            await refresh_results(user.id, results_container)

    @ui.page("/user-setup")
    def user_setup_page():
        """User setup page for new users."""
        with ui.column().classes("w-full max-w-md mx-auto p-6 gap-4"):
            ui.label("👤 Setup Pengguna").classes("text-2xl font-bold text-center mb-6")

            with ui.card().classes("p-6 shadow-lg"):
                name_input = ui.input("Nama Lengkap", placeholder="Masukkan nama lengkap").classes("w-full")
                email_input = ui.input("Email", placeholder="Masukkan email").classes("w-full")
                phone_input = ui.input("Nomor Telepon (Opsional)", placeholder="Masukkan nomor telepon").classes(
                    "w-full"
                )

                async def create_user():
                    """Create new user and redirect to detection page."""
                    if not name_input.value or not email_input.value:
                        ui.notify("Nama dan email harus diisi", type="negative")
                        return

                    try:
                        # Check if user already exists
                        existing_user = UserService.get_user_by_email(email_input.value)
                        if existing_user:
                            app.storage.tab["current_user_id"] = existing_user.id
                            ui.notify("Pengguna sudah ada, melanjutkan...", type="info")
                        else:
                            from app.models import UserCreate

                            user_data = UserCreate(
                                name=name_input.value,
                                email=email_input.value,
                                phone=phone_input.value if phone_input.value else None,
                            )
                            user = UserService.create_user(user_data)
                            app.storage.tab["current_user_id"] = user.id
                            ui.notify("Pengguna berhasil dibuat!", type="positive")

                        ui.navigate.to("/detection")
                    except Exception as e:
                        import logging

                        logging.error(f"Error creating user: {str(e)}")
                        ui.notify(f"Error membuat pengguna: {str(e)}", type="negative")

                ui.button("Buat Pengguna", on_click=create_user).classes(
                    "w-full bg-primary text-white py-3 text-lg font-semibold"
                )

    async def get_or_create_user() -> Optional[User]:
        """Get current user or return None if not set."""
        user_id = app.storage.tab.get("current_user_id")
        if user_id:
            return UserService.get_user(user_id)
        return None

    async def create_upload_section(user_id: int):
        """Create upload section UI."""
        with ui.card().classes("p-6 shadow-lg"):
            ui.label("📤 Upload Citra X-ray").classes("text-xl font-bold mb-4")

            # Upload instructions
            with ui.row().classes("gap-4 mb-4"):
                ui.icon("info").classes("text-blue-500 text-2xl")
                with ui.column().classes("flex-1"):
                    ui.label("Petunjuk Upload:").classes("font-semibold text-gray-700")
                    ui.label("• Format yang didukung: JPG, JPEG, PNG").classes("text-sm text-gray-600")
                    ui.label("• Ukuran maksimal: 10MB").classes("text-sm text-gray-600")
                    ui.label("• Pastikan citra X-ray berkualitas baik").classes("text-sm text-gray-600")

            # Upload component
            upload = (
                ui.upload(on_upload=lambda e: handle_upload(e, user_id), auto_upload=True, multiple=False)
                .classes("w-full")
                .props('accept=".jpg,.jpeg,.png" max-file-size="10485760"')
            )

            upload.classes(
                "border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors"
            )

    def handle_upload(e: events.UploadEventArguments, user_id: int):
        """Handle X-ray image upload."""
        try:
            ui.notify("Memulai upload...", type="info")

            # Validate file
            if not e.name.lower().endswith((".jpg", ".jpeg", ".png")):
                ui.notify("Format file tidak didukung. Gunakan JPG, JPEG, atau PNG.", type="negative")
                return

            content_bytes = e.content.read()
            if len(content_bytes) > 10 * 1024 * 1024:  # 10MB limit
                ui.notify("Ukuran file terlalu besar. Maksimal 10MB.", type="negative")
                return

            # Save image
            xray_image = ImageService.save_uploaded_image(content_bytes, e.name, user_id)

            ui.notify("✅ Citra berhasil diupload!", type="positive")

            # Start detection
            if xray_image.id is not None:
                detection = DetectionService.start_detection(xray_image.id)
                ui.notify("🔍 Memulai proses deteksi...", type="info")

                # Process detection asynchronously
                if detection.id is not None:
                    asyncio.create_task(process_detection_async(detection.id, user_id))
            else:
                ui.notify("❌ Error: ID gambar tidak valid", type="negative")

        except Exception as ex:
            import logging

            logging.error(f"Error during upload: {str(ex)}")
            ui.notify(f"Error upload: {str(ex)}", type="negative")

    async def process_detection_async(detection_id: int, user_id: int):
        """Process detection asynchronously and refresh results."""
        try:
            await DetectionService.process_detection(detection_id)
            ui.notify("✅ Deteksi selesai!", type="positive")

            # Find and refresh results container
            # Note: In a real app, you'd use a more robust way to refresh the UI
            ui.navigate.to("/detection")  # Simple refresh approach

        except Exception as e:
            import logging

            logging.error(f"Detection processing failed for detection {detection_id}: {str(e)}")
            await DetectionService.mark_detection_failed(detection_id, str(e))
            ui.notify(f"❌ Deteksi gagal: {str(e)}", type="negative")

    async def refresh_results(user_id: int, container: ui.column):
        """Refresh detection results display."""
        with container:
            container.clear()

            # Get detection history
            detection_history = DetectionService.get_user_detection_history(user_id)

            if not detection_history:
                with ui.card().classes("p-6 text-center"):
                    ui.icon("image_search").classes("text-6xl text-gray-400 mb-4")
                    ui.label("Belum ada deteksi").classes("text-xl text-gray-500 mb-2")
                    ui.label("Upload citra X-ray untuk memulai deteksi").classes("text-gray-400")
                return

            ui.label("📊 Riwayat Deteksi").classes("text-xl font-bold mb-4")

            # Display results
            for result in detection_history:
                await create_result_card(result)

    async def create_result_card(result):
        """Create a result card for detection result."""
        # Status colors
        status_colors = {
            DetectionStatus.PENDING: "border-yellow-400 bg-yellow-50",
            DetectionStatus.PROCESSING: "border-blue-400 bg-blue-50",
            DetectionStatus.COMPLETED: "border-green-400 bg-green-50",
            DetectionStatus.FAILED: "border-red-400 bg-red-50",
        }

        # Disease colors and icons
        disease_info = {
            DiseaseType.NORMAL: {"color": "text-green-600", "icon": "✅", "label": "Normal"},
            DiseaseType.PNEUMONIA: {"color": "text-orange-600", "icon": "⚠️", "label": "Pneumonia"},
            DiseaseType.TUBERCULOSIS: {"color": "text-red-600", "icon": "🦠", "label": "Tuberkulosis"},
            DiseaseType.COVID19: {"color": "text-purple-600", "icon": "🦠", "label": "COVID-19"},
            DiseaseType.LUNG_CANCER: {"color": "text-red-800", "icon": "⚠️", "label": "Kanker Paru-paru"},
        }

        card_class = f"p-6 border-l-4 {status_colors.get(result.status, 'border-gray-400 bg-gray-50')}"

        with ui.card().classes(card_class):
            # Header
            with ui.row().classes("w-full justify-between items-start mb-3"):
                with ui.column():
                    ui.label(result.filename).classes("font-semibold text-lg")
                    ui.label(f"Diupload: {result.created_at.strftime('%d/%m/%Y %H:%M')}").classes(
                        "text-sm text-gray-500"
                    )

                # Status badge
                status_labels = {
                    DetectionStatus.PENDING: ("⏳", "Menunggu"),
                    DetectionStatus.PROCESSING: ("🔄", "Memproses"),
                    DetectionStatus.COMPLETED: ("✅", "Selesai"),
                    DetectionStatus.FAILED: ("❌", "Gagal"),
                }
                icon, label = status_labels.get(result.status, ("❓", "Unknown"))
                ui.label(f"{icon} {label}").classes("px-3 py-1 rounded-full text-sm font-medium bg-white")

            # Results
            if result.status == DetectionStatus.COMPLETED and result.detected_disease:
                disease_data = disease_info.get(
                    result.detected_disease, {"color": "text-gray-600", "icon": "❓", "label": "Unknown"}
                )

                with ui.row().classes("gap-6 mb-4"):
                    # Disease result
                    with ui.column():
                        ui.label("Hasil Deteksi:").classes("text-sm font-medium text-gray-700")
                        ui.label(f"{disease_data['icon']} {disease_data['label']}").classes(
                            f"text-xl font-bold {disease_data['color']}"
                        )

                    # Confidence score
                    if result.confidence_score:
                        with ui.column():
                            ui.label("Tingkat Kepercayaan:").classes("text-sm font-medium text-gray-700")
                            confidence_pct = float(result.confidence_score) * 100
                            ui.label(f"{confidence_pct:.1f}%").classes("text-xl font-bold")

                # Health status
                if result.is_disease_detected:
                    with ui.card().classes("p-4 bg-red-50 border border-red-200"):
                        ui.label("⚠️ Terdeteksi Indikasi Penyakit").classes("font-semibold text-red-700 mb-2")
                        ui.label("Silakan konsultasi dengan dokter untuk diagnosis lebih lanjut.").classes(
                            "text-red-600 text-sm"
                        )
                else:
                    with ui.card().classes("p-4 bg-green-50 border border-green-200"):
                        ui.label("✅ Tidak Terdeteksi Penyakit").classes("font-semibold text-green-700 mb-2")
                        ui.label("Hasil menunjukkan kondisi paru-paru normal.").classes("text-green-600 text-sm")

            elif result.status == DetectionStatus.FAILED:
                ui.label("❌ Proses deteksi gagal").classes("text-red-600 font-medium")

            elif result.status in [DetectionStatus.PENDING, DetectionStatus.PROCESSING]:
                ui.label("🔄 Sedang memproses...").classes("text-blue-600 font-medium")

                # Auto-refresh for pending/processing results
                ui.timer(3.0, lambda: ui.navigate.to("/detection"))
