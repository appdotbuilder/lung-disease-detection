from app.database import create_tables
import app.navigation
import app.xray_detection
import app.history


def startup() -> None:
    """Initialize the application."""
    # Create database tables
    create_tables()

    # Register all UI modules
    app.navigation.create()
    app.xray_detection.create()
    app.history.create()
