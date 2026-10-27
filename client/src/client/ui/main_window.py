import logging

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget, QWidget

from client.core.coordinates import format_coordinate, iter_coordinate_range
from client.core.serial_worker import SerialWorker
from client.ui.board_utils import create_empty_board
from client.ui.constants import (
    PROTOCOL_SHIP_ORDER,
    Board,
    BoardStore,
)
from client.ui.screens.game_over import GameOverScreen
from client.ui.screens.gameplay import GameplayScreen
from client.ui.screens.pass_device import PassDeviceScreen
from client.ui.screens.setup import SetupScreen
from client.ui.screens.startup import StartupScreen

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self, dev_fleet_p1: str | None = None, dev_fleet_p2: str | None = None
    ) -> None:
        super().__init__()
        self.setWindowTitle("Battleship - STM32 Terminal")
        self.resize(1024, 768)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.serial_worker = SerialWorker()
        self.serial_worker.message_received.connect(self.handle_server_response)

        self.ai_mode = False
        self.boards: BoardStore = {}

        self.dev_p1 = dev_fleet_p1
        self.dev_p2 = dev_fleet_p2
        self.use_setup_shortcut = self.dev_p1 is not None
        self.pending_winner = 0
        self.hardware_reset_notice_active = False

        self.startup_screen = StartupScreen()
        self.setup_screen = SetupScreen()
        self.pass_screen = PassDeviceScreen()
        self.gameplay_screen = GameplayScreen()
        self.game_over_screen = GameOverScreen()

        self.startup_screen.send_command.connect(self.serial_worker.send_command)
        self.setup_screen.send_command.connect(self.serial_worker.send_command)
        self.gameplay_screen.send_command.connect(self.serial_worker.send_command)

        self._post_pass_widget: QWidget | None = None
        self.pass_screen.ready.connect(self._complete_hotseat_transition)
        self.gameplay_screen.turn_ended.connect(self._gameplay_transition)
        self.gameplay_screen.game_over.connect(self._show_game_over)
        self.game_over_screen.play_again_requested.connect(self._start_new_game)

        self.setup_screen.main_menu_requested.connect(self._to_main_menu)
        self.gameplay_screen.main_menu_requested.connect(self._to_main_menu)
        self.game_over_screen.main_menu_requested.connect(self._to_main_menu)

        self.stack.addWidget(self.startup_screen)
        self.stack.addWidget(self.setup_screen)
        self.stack.addWidget(self.pass_screen)
        self.stack.addWidget(self.gameplay_screen)
        self.stack.addWidget(self.game_over_screen)

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

        if response == "OK":
            if self.use_setup_shortcut:
                mode = "PVP" if self.dev_p2 else "AI"
                self.serial_worker.send_command(f"NEW: {mode}")
            return
        if response in {"OK: NEW_PVP", "OK: NEW_AI"}:
            self.ai_mode = response == "OK: NEW_AI"
            if self.use_setup_shortcut:
                self.serial_worker.send_command(f"FLEET: 1,{self.dev_p1}")
            else:
                self.setup_screen.reset_for_player(1)
                self.stack.setCurrentWidget(self.setup_screen)
            return
        if response == "OK: SETUP_P2":
            if self.use_setup_shortcut:
                self.serial_worker.send_command(f"FLEET: 2,{self.dev_p2}")
            else:
                self.boards[1] = self.setup_screen.get_board_state()
                self.setup_screen.reset_for_player(2)
                self.trigger_hotseat_transition(player=2, next_widget=self.setup_screen)
            return
        if response == "OK: IN_PROGRESS":
            if self.use_setup_shortcut and self.dev_p1:
                try:
                    self.boards[1] = self._parse_fleet_coordinates(self.dev_p1)
                    if self.dev_p2:
                        self.boards[2] = self._parse_fleet_coordinates(self.dev_p2)
                except ValueError as error:
                    logger.error("Invalid development fleet: %s", error)
                    return
                self.use_setup_shortcut = False
            else:
                setup_player = 1 if self.ai_mode else 2
                self.boards[setup_player] = self.setup_screen.get_board_state()
            self.gameplay_screen.initialize_game(self.boards, ai_mode=self.ai_mode)
            self.gameplay_screen.prepare_for_turn(1)
            self.trigger_hotseat_transition(player=1, next_widget=self.gameplay_screen)
            return
        if response.startswith("STATUS:"):
            if self.pending_winner is None:
                logger.warning("Received unexpected STATUS response: %r", response)
                return
            try:
                _, fleet_str = response.split(":", 1)[1].strip().split(",", 1)

                self.gameplay_screen.layouts[2] = self._parse_fleet_coordinates(
                    fleet_str
                )
                logger.debug("Successfully parsed AI board state.")

            except (ValueError, IndexError) as error:
                logger.error("Failed to parse STATUS response %r: %s", response, error)

            self._render_game_over_screen()
            return
        if response == "EVENT: RESET":
            if self.hardware_reset_notice_active:
                return

            self.hardware_reset_notice_active = True
            self._to_main_menu()

            QMessageBox.information(
                self,
                "Session Reset",
                "The hardware menu button was pressed.\n"
                "The current session has ended.",
            )

            self.hardware_reset_notice_active = False

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

    def _to_main_menu(self) -> None:
        self.pending_winner = None
        self.boards.clear()
        self._post_pass_widget = None
        self.ai_mode = False

        self.gameplay_screen.cancel_pending_transitions()
        self.startup_screen.reset_buttons()

        self.stack.setCurrentWidget(self.startup_screen)
        self.serial_worker.send_command("CONNECT")

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

    def _gameplay_transition(self, player_id: int) -> None:
        if not self.ai_mode:
            self.gameplay_screen.prepare_for_turn(player_id)
            self.trigger_hotseat_transition(player_id, self.gameplay_screen)

    def _show_game_over(self, winner_id: int) -> None:
        self.pending_winner = winner_id

        if self.ai_mode:
            logger.debug("Requesting AI board state...")
            self.serial_worker.send_command("STATE: 2")
        else:
            self._render_game_over_screen()

    def _render_game_over_screen(self) -> None:
        if self.pending_winner is None:
            logger.warning("Unexpected _render_game_over_screen call")
            return
        self.game_over_screen.set_results(
            self.pending_winner,
            self.gameplay_screen.layouts,
            self.gameplay_screen.shots,
            ai_mode=self.ai_mode,
        )
        self.stack.setCurrentWidget(self.game_over_screen)
        self.pending_winner = None

    def _start_new_game(self) -> None:
        self.boards.clear()
        mode = "AI" if self.ai_mode else "PVP"
        self.serial_worker.send_command(f"NEW: {mode}")  # Loops back through handler

    def _parse_fleet_coordinates(self, fleet_str: str) -> Board:
        board: Board = create_empty_board()
        coords = fleet_str.split(",")

        expected_count = len(PROTOCOL_SHIP_ORDER) * 2
        if len(coords) != expected_count:
            raise ValueError(
                f"Expected {expected_count} fleet coordinates, received {len(coords)}"
            )

        for i, ship_id in enumerate(PROTOCOL_SHIP_ORDER):
            start = coords[i * 2]
            end = coords[i * 2 + 1]

            for row, column in iter_coordinate_range(start, end):
                if board[row][column] is not None:
                    raise ValueError(
                        f"Ship {ship_id} overlaps another ship at "
                        f"{format_coordinate(row, column)}"
                    )

                board[row][column] = ship_id

        return board

    def closeEvent(self, event: QCloseEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        self.serial_worker.stop()
        super().closeEvent(event)
