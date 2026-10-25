import logging

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from client.core.coordinates import format_coordinate, iter_coordinate_range
from client.ui.board_utils import (
    apply_cell_style,
    create_empty_board,
    create_grid,
    create_legend,
)
from client.ui.constants import BOARD_SIZE, SHIP_CONFIG, BoardStore

logger = logging.getLogger(__name__)


class GameplayScreen(QWidget):
    send_command = pyqtSignal(str)
    turn_ended = pyqtSignal(int)
    game_over = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self.layouts: BoardStore = {}
        self.shots: BoardStore = {}

        self._reset_game_state()
        self._setup_ui()

    def _reset_game_state(self) -> None:
        self.active_player = 1
        self.input_locked = True
        self.pending_shot: tuple[int, int] | None = None
        self.shots = {1: create_empty_board(), 2: create_empty_board()}

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        self.log_label = QLabel("Awaiting initialization...")
        self.log_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.log_label.setStyleSheet(
            "font-size: 24px; font-weight: bold; margin-bottom: 10px;"
        )
        main_layout.addWidget(self.log_label)

        grids_layout = QHBoxLayout()
        grids_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Left Panel: Radar (Clickable)
        radar_panel = QVBoxLayout()
        radar_title = QLabel("Target Radar")
        radar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        radar_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        radar_panel.addWidget(radar_title)

        self.radar_cells = create_grid(
            radar_panel, clickable=True, on_click=self._on_radar_click
        )
        grids_layout.addLayout(radar_panel)

        grids_layout.addSpacing(60)

        # Right Panel: Home Fleet (Non-Clickable)
        home_panel = QVBoxLayout()
        home_title = QLabel("Home Fleet")
        home_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        home_panel.addWidget(home_title)

        self.home_cells = create_grid(home_panel, clickable=False)
        grids_layout.addLayout(home_panel)

        main_layout.addLayout(grids_layout)
        main_layout.addSpacing(20)

        create_legend(main_layout)
        main_layout.addStretch()

    def initialize_game(self, boards: BoardStore) -> None:
        self._reset_game_state()
        self.layouts = {
            player_id: [row[:] for row in board] for player_id, board in boards.items()
        }
        self._draw_boards()

    def prepare_for_turn(self, player_id: int) -> None:
        self.active_player = player_id
        self.input_locked = False
        self.log_label.setText(f"Player {player_id}: Select a target.")
        self._draw_boards()

    def _on_radar_click(self, r: int, c: int) -> None:
        if self.input_locked:
            return

        target_player = 2 if self.active_player == 1 else 1
        if self.shots[target_player][r][c] is not None:
            return

        self.input_locked = True
        self.pending_shot = (r, c)

        coordinate = format_coordinate(r, c)

        self.send_command.emit(f"SHOOT: {self.active_player},{coordinate}")
        self.log_label.setText(f"Firing at {coordinate}...")

    def _mark_sunk_ship(
        self, target_player: int, start_coord: str, end_coord: str
    ) -> None:
        for row, column in iter_coordinate_range(start_coord, end_coord):
            self.shots[target_player][row][column] = "SUNK"

    def process_server_response(self, response: str) -> bool:
        if response.startswith("NACK:"):
            self.input_locked = False
            reason = response.removeprefix("NACK:").strip()
            self.log_label.setText(f"Shot rejected: {reason}")
            return True

        target_player = 2 if self.active_player == 1 else 1

        if self.pending_shot is None:
            logger.warning("Received shot result without a pending shot: %r", response)
            return False

        r, c = self.pending_shot
        self.pending_shot = None

        if response.startswith("MISS:"):
            self.shots[target_player][r][c] = "MISS"
            self.log_label.setText("Splash! It's a Miss.")
            self._draw_boards()
            self._schedule_turn_end(target_player)
            return True

        if response.startswith("HIT:"):
            self.shots[target_player][r][c] = "HIT"
            self.log_label.setText("Direct Hit!")
            self._draw_boards()
            self._schedule_turn_end(target_player)
            return True

        if response.startswith("SUNK:"):
            parts = response.split(",")
            if len(parts) != 4:
                logger.warning("Malformed SUNK response: %r", response)
                return False

            target_player = int(parts[0].split(":", maxsplit=1)[1].strip())

            ship_char = parts[1].strip()
            if ship_char not in SHIP_CONFIG:
                logger.warning("Malformed SUNK response: %r", response)
                return False
            ship_name = SHIP_CONFIG[ship_char].name
            self._mark_sunk_ship(target_player, parts[2].strip(), parts[3].strip())
            self.log_label.setText(f"Direct Hit! You sunk their {ship_name}!")

            self._draw_boards()
            self._schedule_turn_end(target_player)
            return True

        if response.startswith("WIN:"):
            # WIN: <Winner>,<ShipChar>,<StartCoord>,<EndCoord>
            parts = response.split(",")
            if len(parts) != 4:
                logger.warning("Malformed WIN response: %r", response)
                return False
            winner_id = int(parts[0].split(":", maxsplit=1)[1].strip())

            self._mark_sunk_ship(target_player, parts[2].strip(), parts[3].strip())
            self.log_label.setText("VICTORY! All enemy ships destroyed.")
            self._draw_boards()

            QTimer.singleShot(100, lambda: self.game_over.emit(winner_id))
            return True

        return False

    def _schedule_turn_end(self, next_player: int) -> None:
        QTimer.singleShot(100, lambda: self.turn_ended.emit(next_player))

    def _draw_boards(self) -> None:
        target = 2 if self.active_player == 1 else 1
        home_layout = self.layouts.get(self.active_player)
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                radar_shot = self.shots[target][r][c]
                apply_cell_style(self.radar_cells[r][c], None, radar_shot)

                home_shot = self.shots[self.active_player][r][c]
                home_ship = home_layout[r][c] if home_layout is not None else None
                apply_cell_style(self.home_cells[r][c], home_ship, home_shot)
