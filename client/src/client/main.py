import argparse
import logging
import sys
from importlib import resources

from PyQt6.QtWidgets import QApplication

from client.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def load_assets(app: QApplication) -> None:
    try:
        qss_path = resources.files("client.assets").joinpath("style.qss")
        with qss_path.open("r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

        logger.info("Assets loaded successfully.")
    except Exception as e:
        logger.error("Error loading assets: %s", e)


def main() -> None:
    parser = argparse.ArgumentParser(description="Battleship Client")

    parser.add_argument(
        "--debug", action="store_true", help="Enable DEBUG logging level"
    )
    parser.add_argument(
        "--dev-p1-fleet",
        help="Bypass UI and set P1 fleet",
    )
    parser.add_argument(
        "--dev-p2-fleet",
        help="Bypass UI and set P2 fleet (Requires --dev-p1-fleet)",
    )

    args, qt_args = parser.parse_known_args()

    if args.dev_p2_fleet and not args.dev_p1_fleet:
        parser.error("--dev-p2-fleet requires --dev-p1-fleet")

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    app = QApplication([sys.argv[0], *qt_args])

    load_assets(app)

    logger.info("Initializing Main Window and Serial Worker...")
    window = MainWindow(dev_fleet_p1=args.dev_p1_fleet, dev_fleet_p2=args.dev_p2_fleet)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
