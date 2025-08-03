"""Detection history module for viewing past results."""

from typing import List
from nicegui import ui, app
from app.services import DetectionService, UserService
from app.models import DetectionResult, DiseaseType, DetectionStatus


def create():
    """Create history UI module."""

    @ui.page("/history")
    async def history_page():
        """Detection history page."""
        await ui.context.client.connected()

        # Get current user
        user_id = app.storage.tab.get("current_user_id")
        if not user_id:
            ui.navigate.to("/user-setup")
            return

        user = UserService.get_user(user_id)
        if user is None:
            ui.navigate.to("/user-setup")
            return

        # Page layout
        with ui.column().classes("w-full max-w-6xl mx-auto p-6 gap-6"):
            # Header
            with ui.row().classes("w-full justify-between items-center mb-6"):
                ui.label("📊 Riwayat Deteksi Penyakit Paru-paru").classes("text-3xl font-bold text-gray-800")
                ui.button("← Kembali", on_click=lambda: ui.navigate.to("/detection")).classes(
                    "bg-gray-500 text-white px-4 py-2"
                ).props("outline")

            # User info
            with ui.card().classes("p-4 bg-blue-50 border-l-4 border-blue-500 mb-6"):
                ui.label(f"👤 {user.name}").classes("font-semibold text-blue-800")
                ui.label(f"📧 {user.email}").classes("text-blue-600")

            # Get detection history
            detection_history = DetectionService.get_user_detection_history(user_id)

            if not detection_history:
                create_empty_history()
            else:
                create_history_summary(detection_history)
                create_detailed_history(detection_history)

    def create_empty_history():
        """Create empty history display."""
        with ui.card().classes("p-8 text-center"):
            ui.icon("history").classes("text-6xl text-gray-400 mb-4")
            ui.label("Belum Ada Riwayat Deteksi").classes("text-2xl text-gray-500 mb-2")
            ui.label("Upload citra X-ray untuk memulai deteksi pertama Anda").classes("text-gray-400 mb-6")
            ui.button("Mulai Deteksi", on_click=lambda: ui.navigate.to("/detection")).classes(
                "bg-primary text-white px-6 py-3 text-lg"
            )

    def create_history_summary(history: List[DetectionResult]):
        """Create summary statistics."""
        total_detections = len(history)
        completed_detections = len([h for h in history if h.status == DetectionStatus.COMPLETED])
        diseases_detected = len([h for h in history if h.is_disease_detected])
        normal_results = completed_detections - diseases_detected

        with ui.card().classes("p-6 mb-6"):
            ui.label("📈 Ringkasan Statistik").classes("text-xl font-bold mb-4")

            with ui.row().classes("gap-6 w-full"):
                # Total detections
                with ui.card().classes("p-4 bg-blue-50 flex-1 text-center"):
                    ui.label(str(total_detections)).classes("text-3xl font-bold text-blue-600")
                    ui.label("Total Deteksi").classes("text-blue-800 font-medium")

                # Completed detections
                with ui.card().classes("p-4 bg-green-50 flex-1 text-center"):
                    ui.label(str(completed_detections)).classes("text-3xl font-bold text-green-600")
                    ui.label("Selesai").classes("text-green-800 font-medium")

                # Normal results
                with ui.card().classes("p-4 bg-emerald-50 flex-1 text-center"):
                    ui.label(str(normal_results)).classes("text-3xl font-bold text-emerald-600")
                    ui.label("Normal").classes("text-emerald-800 font-medium")

                # Disease detected
                with ui.card().classes("p-4 bg-orange-50 flex-1 text-center"):
                    ui.label(str(diseases_detected)).classes("text-3xl font-bold text-orange-600")
                    ui.label("Indikasi Penyakit").classes("text-orange-800 font-medium")

    def create_detailed_history(history: List[DetectionResult]):
        """Create detailed history table."""
        with ui.card().classes("p-6"):
            ui.label("📋 Detail Riwayat").classes("text-xl font-bold mb-4")

            # Disease type colors and labels
            disease_info = {
                DiseaseType.NORMAL: {"color": "#10b981", "label": "✅ Normal"},
                DiseaseType.PNEUMONIA: {"color": "#f59e0b", "label": "⚠️ Pneumonia"},
                DiseaseType.TUBERCULOSIS: {"color": "#ef4444", "label": "🦠 Tuberkulosis"},
                DiseaseType.COVID19: {"color": "#8b5cf6", "label": "🦠 COVID-19"},
                DiseaseType.LUNG_CANCER: {"color": "#dc2626", "label": "⚠️ Kanker Paru-paru"},
            }

            # Status colors (referenced for potential future use)
            # status_colors = {
            #     DetectionStatus.PENDING: '#f59e0b',
            #     DetectionStatus.PROCESSING: '#3b82f6',
            #     DetectionStatus.COMPLETED: '#10b981',
            #     DetectionStatus.FAILED: '#ef4444'
            # }

            # Prepare table data
            columns = [
                {"name": "filename", "label": "File", "field": "filename", "align": "left"},
                {"name": "status", "label": "Status", "field": "status", "align": "center"},
                {"name": "result", "label": "Hasil", "field": "result", "align": "left"},
                {"name": "confidence", "label": "Kepercayaan", "field": "confidence", "align": "center"},
                {"name": "date", "label": "Tanggal", "field": "date", "align": "center"},
            ]

            rows = []
            for result in history:
                # Format status
                status_labels = {
                    DetectionStatus.PENDING: "⏳ Menunggu",
                    DetectionStatus.PROCESSING: "🔄 Memproses",
                    DetectionStatus.COMPLETED: "✅ Selesai",
                    DetectionStatus.FAILED: "❌ Gagal",
                }

                # Format result
                result_text = ""
                if result.status == DetectionStatus.COMPLETED and result.detected_disease:
                    disease_data = disease_info.get(result.detected_disease, {"label": "❓ Unknown"})
                    result_text = disease_data["label"]
                elif result.status == DetectionStatus.FAILED:
                    result_text = "❌ Gagal"
                elif result.status in [DetectionStatus.PENDING, DetectionStatus.PROCESSING]:
                    result_text = "⏳ Menunggu"

                # Format confidence
                confidence_text = ""
                if result.confidence_score:
                    confidence_pct = float(result.confidence_score) * 100
                    confidence_text = f"{confidence_pct:.1f}%"

                rows.append(
                    {
                        "filename": result.filename,
                        "status": status_labels.get(result.status, "Unknown"),
                        "result": result_text,
                        "confidence": confidence_text,
                        "date": result.created_at.strftime("%d/%m/%Y %H:%M"),
                        "detection_id": result.detection_id,
                    }
                )

            # Create table
            table = ui.table(columns=columns, rows=rows).classes("w-full")
            table.props("flat bordered")

            # Add custom styling for better appearance
            table.add_slot(
                "body-cell-status",
                """
                <q-td :props="props">
                    <div class="text-center">{{ props.value }}</div>
                </q-td>
            """,
            )

            table.add_slot(
                "body-cell-result",
                """
                <q-td :props="props">
                    <div class="font-medium">{{ props.value }}</div>
                </q-td>
            """,
            )

            table.add_slot(
                "body-cell-confidence",
                """
                <q-td :props="props">
                    <div class="text-center font-mono font-bold">{{ props.value }}</div>
                </q-td>
            """,
            )

            # Add click handler for row selection
            def handle_row_click(e):
                """Handle table row click for detailed view."""
                row_data = e.args[1]  # Get the row data
                detection_id = row_data["detection_id"]
                show_detection_details(detection_id)

            table.on("rowClick", handle_row_click)

    def show_detection_details(detection_id: int):
        """Show detailed detection information in a dialog."""
        detection = DetectionService.get_detection(detection_id)
        if detection is None:
            ui.notify("Detail deteksi tidak ditemukan", type="negative")
            return

        with ui.dialog() as dialog, ui.card().classes("w-96 max-w-full"):
            ui.label("🔍 Detail Deteksi").classes("text-xl font-bold mb-4")

            # Basic info
            with ui.column().classes("gap-2 mb-4"):
                ui.label(f"ID Deteksi: {detection.id}").classes("text-sm")
                ui.label(f"Status: {detection.status.value}").classes("text-sm")
                ui.label(f"Model: {detection.model_name} v{detection.model_version}").classes("text-sm")

                if detection.processing_started_at:
                    ui.label(f"Dimulai: {detection.processing_started_at.strftime('%d/%m/%Y %H:%M:%S')}").classes(
                        "text-sm"
                    )

                if detection.processing_completed_at:
                    ui.label(f"Selesai: {detection.processing_completed_at.strftime('%d/%m/%Y %H:%M:%S')}").classes(
                        "text-sm"
                    )

                if detection.processing_duration_seconds:
                    ui.label(f"Durasi: {detection.processing_duration_seconds} detik").classes("text-sm")

            # Results
            if detection.status == DetectionStatus.COMPLETED:
                ui.separator()
                ui.label("📊 Hasil Deteksi").classes("font-bold mb-2")

                if detection.detected_disease:
                    disease_labels = {
                        DiseaseType.NORMAL: "Normal",
                        DiseaseType.PNEUMONIA: "Pneumonia",
                        DiseaseType.TUBERCULOSIS: "Tuberkulosis",
                        DiseaseType.COVID19: "COVID-19",
                        DiseaseType.LUNG_CANCER: "Kanker Paru-paru",
                    }
                    ui.label(f"Penyakit: {disease_labels.get(detection.detected_disease, 'Unknown')}").classes(
                        "text-sm"
                    )

                if detection.confidence_score:
                    confidence_pct = float(detection.confidence_score) * 100
                    ui.label(f"Kepercayaan: {confidence_pct:.2f}%").classes("text-sm")

                ui.label(f"Ada Penyakit: {'Ya' if detection.is_disease_detected else 'Tidak'}").classes("text-sm")

                # Detection details
                if detection.detection_details:
                    ui.separator()
                    ui.label("🔬 Detail Teknis").classes("font-bold mb-2")

                    details = detection.detection_details
                    if "regions_analyzed" in details:
                        ui.label(f"Region Dianalisis: {', '.join(details['regions_analyzed'])}").classes("text-xs")

                    if "abnormal_regions" in details:
                        abnormal = details["abnormal_regions"]
                        if abnormal:
                            ui.label(f"Region Abnormal: {', '.join(abnormal)}").classes("text-xs")
                        else:
                            ui.label("Region Abnormal: Tidak ada").classes("text-xs")

                    if "image_quality_score" in details:
                        quality = details["image_quality_score"]
                        ui.label(f"Kualitas Citra: {quality:.1%}").classes("text-xs")

            elif detection.status == DetectionStatus.FAILED and detection.error_message:
                ui.separator()
                ui.label("❌ Error").classes("font-bold text-red-600 mb-2")
                ui.label(detection.error_message).classes("text-sm text-red-600")

            # Close button
            with ui.row().classes("justify-end mt-4"):
                ui.button("Tutup", on_click=dialog.close).props("outline")

        dialog.open()
