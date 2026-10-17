from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QMainWindow, QStackedWidget

from client.core.serial_worker import SerialWorker

# Import your screens
from client.ui.screens.startup import StartupScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Battleship - STM32 Terminal")
        self.resize(1024, 768)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.serial_worker = SerialWorker()
        self.serial_worker.message_received.connect(self.handle_server_response)
        self.serial_worker.start()

        self.startup_screen = StartupScreen()
        # self.setup_screen = SetupScreen()
        # self.gameplay_screen = GameplayScreen()

        self.stack.addWidget(self.startup_screen)
        # self.stack.addWidget(self.setup_screen)
        # self.stack.addWidget(self.gameplay_screen)

        self.startup_screen.mode_selected.connect(self.request_game_mode)

    @pyqtSlot(str)
    def request_game_mode(self, mode: str):
        """
        Triggered when a user clicks a mode button on the StartupScreen.
        Translates the UI intent into a strict protocol command for the STM32.
        """
        if mode == "PVP":
            self.serial_worker.send_command("NEW: PVP")
        elif mode == "AI":
            self.serial_worker.send_command("NEW: AI")

    @pyqtSlot(str)
    def handle_server_response(self, response: str):
        """
        The central router.
        Triggered whenever the STM32 sends a newline-terminated string.
        Changes the current QStackedWidget screen based on hardware authorization.
        """
        response = response.strip()

        if response == "OK: NEW_PVP" or response == "OK: NEW_AI":
            print(
                f"Server acknowledged mode: {response}. Transitioning to Setup Phase..."
            )
            # self.stack.setCurrentWidget(self.setup_screen)

        # Evaluate Setup Phase Responses
        elif response == "OK: PLACED":
            pass
            # self.setup_screen.handle_placement_success()
