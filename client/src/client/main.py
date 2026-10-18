import logging
import sys
from importlib import resources

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from client.ui.main_window import MainWindow

logger = logging.getLogger(__name__)

# Configure root logger format and handlers
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def load_assets(app: QApplication) -> None:
    try:
        font_path = str(
            resources.files("client.assets.fonts").joinpath("RobotoMono-Regular.ttf")
        )
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            logger.warning("Failed to load custom font: RobotoMono-Regular.ttf")

        qss_path = resources.files("client.assets").joinpath("style.qss")
        with qss_path.open("r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

        logger.info("Assets loaded successfully.")
    except Exception as e:
        logger.error("Error loading assets: %s", e)


def main() -> None:
    app = QApplication(sys.argv)

    load_assets(app)

    logger.info("Initializing Main Window and Serial Worker...")
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
