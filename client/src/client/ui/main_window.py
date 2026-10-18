import logging

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from client.core.serial_worker import SerialWorker

# Import your screens
from client.ui.screens.pass_device import PassDeviceScreen
from client.ui.screens.setup import SetupScreen
from client.ui.screens.startup import StartupScreen

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Battleship - STM32 Terminal")
        self.resize(1024, 768)  # 661 583

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.serial_worker = SerialWorker()
        self.serial_worker.message_received.connect(self.handle_server_response)

        self.ai_mode = False

        self.startup_screen = StartupScreen()
        self.setup_screen = SetupScreen()
        self.pass_screen = PassDeviceScreen()
        # self.gameplay_screen = GameplayScreen()

        self.startup_screen.send_command.connect(self.serial_worker.send_command)
        self.setup_screen.send_command.connect(self.serial_worker.send_command)

        self._post_pass_widget: QWidget | None = None
        self.pass_screen.ready.connect(self._complete_hotseat_transition)

        self.stack.addWidget(self.startup_screen)
        self.stack.addWidget(self.setup_screen)
        self.stack.addWidget(self.pass_screen)
        # self.stack.addWidget(self.gameplay_screen)

        self.serial_worker.start()
        self.serial_worker.send_command("CONNECT")

    @pyqtSlot(str)
    def handle_server_response(self, response: str) -> None:
        """
        The central router.
        Triggered whenever the STM32 sends a newline-terminated string.
        Changes the current QStackedWidget screen based on hardware authorization.
        """
        response = response.strip()

        if response in {"OK: NEW_PVP", "OK: NEW_AI"}:
            self.ai_mode = response == "OK: NEW_AI"
            self.setup_screen.reset_for_player(1)
            self.stack.setCurrentWidget(self.setup_screen)
            return
        if response == "OK: SETUP_P2":
            self.setup_screen.reset_for_player(2)
            self.trigger_hotseat_transition(player=2, next_widget=self.setup_screen)
            return
        if response == "OK: IN_PROGRESS":
            # self.gameplay_screen.prepare_for_turn(1)
            # self.trigger_hotseat_transition(player=1, next_widget=self.gameplay_screen)
            return
        if response.startswith("WIN:"):
            return

        current_widget = self.stack.currentWidget()

        # Check if the active screen has a method to process server feedback
        handler = getattr(current_widget, "process_server_response", None)

        if callable(handler) and handler(response):
            return

        logger.warning(
            "Unhandled server response %r while %s is active",
            response,
            type(current_widget).__name__,
        )

    def trigger_hotseat_transition(self, player: int, next_widget: QWidget) -> None:
        """Displays the masking screen so players can swap seats."""
        if not self.ai_mode:
            self._post_pass_widget = next_widget
            self.pass_screen.set_player(player)
            self.stack.setCurrentWidget(self.pass_screen)
        else:
            # Skip the hotseat transition in singleplayer
            self.stack.setCurrentWidget(next_widget)

    def _complete_hotseat_transition(self) -> None:
        """Switches the view to the result of the hotseat transition"""
        if self._post_pass_widget is None:
            logger.error("No destination configured for hot-seat transition")
            return

        self.stack.setCurrentWidget(self._post_pass_widget)
        self._post_pass_widget = None

    def closeEvent(self, event: QCloseEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        self.serial_worker.stop()
        return super().closeEvent(event)
