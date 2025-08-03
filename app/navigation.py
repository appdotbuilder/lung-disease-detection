"""Navigation module for the application."""

from nicegui import ui, app


def create():
    """Create navigation UI components."""

    @ui.page("/")
    async def index():
        """Landing page with navigation to main features."""
        await ui.context.client.connected()

        # Apply modern theme
        ui.colors(
            primary="#2563eb",
            secondary="#64748b",
            accent="#10b981",
            positive="#10b981",
            negative="#ef4444",
            warning="#f59e0b",
            info="#3b82f6",
        )

        # Check if user exists
        user_id = app.storage.tab.get("current_user_id")

        with ui.column().classes("w-full min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100"):
            # Header
            with ui.row().classes("w-full justify-between items-center p-6 bg-white shadow-sm"):
                ui.label("🫁 X-ray Lung Disease Detection").classes("text-2xl font-bold text-gray-800")

                if user_id:
                    with ui.row().classes("gap-2"):
                        ui.button("Deteksi", on_click=lambda: ui.navigate.to("/detection")).classes(
                            "bg-primary text-white px-4 py-2"
                        )
                        ui.button("Riwayat", on_click=lambda: ui.navigate.to("/history")).classes(
                            "bg-secondary text-white px-4 py-2"
                        )
                        ui.button("Logout", on_click=logout).classes("bg-gray-500 text-white px-4 py-2").props(
                            "outline"
                        )
                else:
                    ui.button("Mulai", on_click=lambda: ui.navigate.to("/user-setup")).classes(
                        "bg-primary text-white px-6 py-2 text-lg"
                    )

            # Main content
            with ui.column().classes("flex-1 max-w-6xl mx-auto p-6 gap-8"):
                # Hero section
                with ui.column().classes("text-center py-16 gap-6"):
                    ui.label("Deteksi Penyakit Paru-paru dari Citra X-ray").classes(
                        "text-5xl font-bold text-gray-800 leading-tight"
                    )
                    ui.label(
                        "Teknologi AI canggih untuk mendeteksi pneumonia, tuberkulosis, COVID-19, dan penyakit paru-paru lainnya"
                    ).classes("text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed")

                    if not user_id:
                        ui.button("Mulai Deteksi Sekarang", on_click=lambda: ui.navigate.to("/user-setup")).classes(
                            "bg-primary text-white px-8 py-4 text-xl font-semibold rounded-lg shadow-lg hover:shadow-xl transition-shadow mt-4"
                        )
                    else:
                        with ui.row().classes("gap-4 mt-4"):
                            ui.button("Upload X-ray", on_click=lambda: ui.navigate.to("/detection")).classes(
                                "bg-primary text-white px-8 py-4 text-xl font-semibold rounded-lg shadow-lg hover:shadow-xl transition-shadow"
                            )
                            ui.button("Lihat Riwayat", on_click=lambda: ui.navigate.to("/history")).classes(
                                "bg-secondary text-white px-8 py-4 text-xl font-semibold rounded-lg shadow-lg hover:shadow-xl transition-shadow"
                            )

                # Features section
                ui.label("Fitur Utama").classes("text-3xl font-bold text-center text-gray-800 mt-16 mb-8")

                with ui.row().classes("gap-8 w-full justify-center"):
                    # Feature 1
                    with ui.card().classes("p-8 text-center max-w-sm shadow-lg hover:shadow-xl transition-shadow"):
                        ui.icon("upload_file").classes("text-6xl text-blue-500 mb-4")
                        ui.label("Upload Mudah").classes("text-xl font-bold text-gray-800 mb-2")
                        ui.label("Drag & drop atau klik untuk upload citra X-ray paru-paru Anda").classes(
                            "text-gray-600 leading-relaxed"
                        )

                    # Feature 2
                    with ui.card().classes("p-8 text-center max-w-sm shadow-lg hover:shadow-xl transition-shadow"):
                        ui.icon("psychology").classes("text-6xl text-green-500 mb-4")
                        ui.label("AI Canggih").classes("text-xl font-bold text-gray-800 mb-2")
                        ui.label(
                            "Teknologi deep learning terdepan untuk deteksi akurat berbagai penyakit paru-paru"
                        ).classes("text-gray-600 leading-relaxed")

                    # Feature 3
                    with ui.card().classes("p-8 text-center max-w-sm shadow-lg hover:shadow-xl transition-shadow"):
                        ui.icon("analytics").classes("text-6xl text-purple-500 mb-4")
                        ui.label("Hasil Detail").classes("text-xl font-bold text-gray-800 mb-2")
                        ui.label("Laporan lengkap dengan tingkat kepercayaan dan rekomendasi tindak lanjut").classes(
                            "text-gray-600 leading-relaxed"
                        )

                # Supported diseases
                ui.label("Penyakit yang Dapat Dideteksi").classes(
                    "text-3xl font-bold text-center text-gray-800 mt-16 mb-8"
                )

                with ui.row().classes("gap-6 w-full justify-center flex-wrap"):
                    diseases = [
                        {"name": "Pneumonia", "icon": "⚠️", "color": "bg-orange-100 text-orange-800"},
                        {"name": "Tuberkulosis", "icon": "🦠", "color": "bg-red-100 text-red-800"},
                        {"name": "COVID-19", "icon": "🦠", "color": "bg-purple-100 text-purple-800"},
                        {"name": "Kanker Paru-paru", "icon": "⚠️", "color": "bg-red-200 text-red-900"},
                        {"name": "Kondisi Normal", "icon": "✅", "color": "bg-green-100 text-green-800"},
                    ]

                    for disease in diseases:
                        with ui.card().classes(f"p-4 {disease['color']} border-0"):
                            ui.label(f"{disease['icon']} {disease['name']}").classes("font-semibold text-lg")

                # Disclaimer
                with ui.card().classes("p-6 bg-yellow-50 border-l-4 border-yellow-400 mt-16"):
                    ui.label("⚠️ Penting").classes("font-bold text-yellow-800 mb-2")
                    ui.label(
                        "Hasil deteksi ini hanya untuk rujukan awal dan tidak menggantikan diagnosis medis profesional. "
                        "Selalu konsultasikan dengan dokter untuk diagnosis dan pengobatan yang tepat."
                    ).classes("text-yellow-700 leading-relaxed")

    def logout():
        """Logout current user."""
        app.storage.tab.clear()
        ui.notify("Berhasil logout", type="info")
        ui.navigate.to("/")

    # Add a header navigation component that can be reused
    def create_navigation_header(current_page: str = ""):
        """Create navigation header for other pages."""
        with ui.row().classes("w-full justify-between items-center p-4 bg-white shadow-sm mb-6"):
            ui.button("🫁", on_click=lambda: ui.navigate.to("/")).classes("text-2xl").props("flat")
            ui.label("X-ray Lung Disease Detection").classes("text-xl font-bold text-gray-800")

            with ui.row().classes("gap-2"):
                nav_items = [{"label": "Deteksi", "path": "/detection"}, {"label": "Riwayat", "path": "/history"}]

                for item in nav_items:
                    classes = "px-4 py-2"
                    if current_page == item["path"]:
                        classes += " bg-primary text-white"
                    else:
                        classes += " text-gray-600"

                    ui.button(item["label"], on_click=lambda _=None, p=item["path"]: ui.navigate.to(p)).classes(classes)

                ui.button("Logout", on_click=logout).classes("bg-gray-500 text-white px-4 py-2").props("outline")

        return True  # Return something to indicate success
