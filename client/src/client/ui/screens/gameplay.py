import logging
from collections.abc import Iterable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from client.core.coordinates import (
    Coordinate,
    format_coordinate,
    iter_coordinate_range,
    parse_coordinate,
)
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
        self.ai_mode = False
        self.last_result: str | None = None

        self._reset_game_state()
        self._setup_ui()

    def _reset_game_state(self) -> None:
        self.active_player = 1
        self.input_locked = True
        self.shots = {1: create_empty_board(), 2: create_empty_board()}
        self.last_result = None

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

    def initialize_game(self, boards: BoardStore, *, ai_mode: bool) -> None:
        self._reset_game_state()
        self.layouts = {
            player_id: [row[:] for row in board] for player_id, board in boards.items()
        }
        self.ai_mode = ai_mode
        self._draw_boards()

    def prepare_for_turn(self, player_id: int) -> None:
        if player_id not in {1, 2}:
            raise ValueError(f"Invalid player ID: {player_id}")

        self.active_player = player_id
        self.input_locked = False
        self.last_result = None
        self.log_label.setText(f"Player {player_id}: Select a target.")
        self._draw_boards()

    def _on_radar_click(self, row: int, column: int) -> None:
        if self.input_locked:
            return

        target_player = 2 if self.active_player == 1 else 1

        if self.shots[target_player][row][column] is not None:
            return

        self.input_locked = True

        coordinate = format_coordinate(row, column)
        self.send_command.emit(f"SHOOT: {self.active_player},{coordinate}")
        self.log_label.setText(f"Firing at {coordinate}...")

    @staticmethod
    def _parse_player_field(field: str) -> int:
        try:
            _, player_text = field.split(":", maxsplit=1)
            player_id = int(player_text.strip())
        except (ValueError, IndexError) as error:
            raise ValueError(f"Invalid player field: {field!r}") from error

        if player_id not in {1, 2}:
            raise ValueError(f"Player ID must be 1 or 2, received {player_id}")

        return player_id

    @staticmethod
    def _parse_shot_response(response: str) -> tuple[int, Coordinate]:
        parts = response.split(",")

        if len(parts) != 2:
            raise ValueError(f"Expected 2 fields, received {len(parts)}")

        target_player = GameplayScreen._parse_player_field(parts[0])
        coordinate = parse_coordinate(parts[1].strip())

        return target_player, coordinate

    @staticmethod
    def _parse_ship_response(response: str) -> tuple[int, str, list[Coordinate]]:
        parts = response.split(",")

        if len(parts) != 4:
            raise ValueError(f"Expected 4 fields, received {len(parts)}")

        player_id = GameplayScreen._parse_player_field(parts[0])
        ship_id = parts[1].strip()

        if ship_id not in SHIP_CONFIG:
            raise ValueError(f"Unknown ship ID: {ship_id!r}")

        start_coordinate = parts[2].strip()
        end_coordinate = parts[3].strip()

        cells = list(iter_coordinate_range(start_coordinate, end_coordinate))

        expected_length = SHIP_CONFIG[ship_id].length

        if len(cells) != expected_length:
            raise ValueError(
                f"Ship {ship_id!r} should occupy "
                f"{expected_length} cells, received {len(cells)}"
            )

        return player_id, ship_id, cells

    def _mark_sunk_ship(self, target_player: int, cells: Iterable[Coordinate]) -> None:
        for row, column in cells:
            self.shots[target_player][row][column] = "SUNK"

    def process_server_response(self, response: str) -> bool:
        if response.startswith("NACK:"):
            self.input_locked = False
            self.last_result = None

            reason = response.removeprefix("NACK:").strip()
            self.log_label.setText(f"Shot rejected: {reason or 'unknown reason'}")
            return True

        if response.startswith("WIN:"):
            return self._process_win_response(response)

        if response.startswith(("MISS:", "HIT:")):
            return self._process_shot_response(response)

        if response.startswith("SUNK:"):
            return self._process_sunk_response(response)

        return False

    def _process_shot_response(self, response: str) -> bool:
        try:
            target_player, coordinate = self._parse_shot_response(response)
        except ValueError as error:
            self._handle_malformed_response(response, error)
            return True

        row, column = coordinate
        is_hit = response.startswith("HIT:")

        self.shots[target_player][row][column] = "HIT" if is_hit else "MISS"

        shot_was_ours = target_player != self.active_player
        formatted_coordinate = format_coordinate(row, column)

        if shot_was_ours:
            self.last_result = "Direct hit!" if is_hit else "Miss."
            self.log_label.setText(self.last_result)
        else:
            result = "Hit!" if is_hit else "Miss."
            self._combine_log(
                f"Enemy fired at {formatted_coordinate}: {result}",
                ready=self.ai_mode,
            )

        self._draw_boards()
        self._complete_shot_response(target_player, shot_was_ours=shot_was_ours)
        return True

    def _process_sunk_response(self, response: str) -> bool:
        try:
            target_player, ship_id, cells = self._parse_ship_response(response)
        except ValueError as error:
            self._handle_malformed_response(response, error)
            return True

        self._mark_sunk_ship(target_player, cells)

        ship_name = SHIP_CONFIG[ship_id].name
        shot_was_ours = target_player != self.active_player

        if shot_was_ours:
            self.last_result = f"Sunk their {ship_name}!"
            self.log_label.setText(self.last_result)
        else:
            self._combine_log(
                f"Enemy sunk your {ship_name}!",
                ready=self.ai_mode,
            )

        self._draw_boards()
        self._complete_shot_response(target_player, shot_was_ours=shot_was_ours)
        return True

    def _process_win_response(self, response: str) -> bool:
        try:
            winner_id, _ship_id, cells = self._parse_ship_response(response)
        except ValueError as error:
            self._handle_malformed_response(response, error)
            return True

        target_player = 2 if winner_id == 1 else 1
        self._mark_sunk_ship(target_player, cells)

        self.input_locked = True
        self.last_result = None

        if winner_id == self.active_player:
            self.log_label.setText("VICTORY! All enemy ships destroyed.")
        else:
            self.log_label.setText("DEFEAT! All your ships were destroyed.")

        self._draw_boards()

        QTimer.singleShot(1500, lambda: self.game_over.emit(winner_id))
        return True

    def _complete_shot_response(
        self, target_player: int, *, shot_was_ours: bool
    ) -> None:
        if shot_was_ours:
            if self.ai_mode:
                # Keep input locked while waiting for the AI response.
                return

            self._schedule_turn_end(target_player)
            return

        if self.ai_mode:
            self.input_locked = False

    def _handle_malformed_response(self, response: str, error: ValueError) -> None:
        logger.warning("Malformed gameplay response %r: %s", response, error)
        self.log_label.setText("Received an invalid response from the server.")

    def _combine_log(self, enemy_message: str, *, ready: bool) -> None:
        messages: list[str] = []

        if self.last_result is not None:
            messages.append(f"You: {self.last_result}")

        messages.append(enemy_message)

        if ready:
            messages.append("Select a target.")

        self.log_label.setText("  |  ".join(messages))
        self.last_result = None

    def _schedule_turn_end(self, next_player: int) -> None:
        QTimer.singleShot(1500, lambda: self.turn_ended.emit(next_player))

    def _draw_boards(self) -> None:
        target_player = 2 if self.active_player == 1 else 1
        home_layout = self.layouts.get(self.active_player)

        for row in range(BOARD_SIZE):
            for column in range(BOARD_SIZE):
                radar_shot = self.shots[target_player][row][column]
                apply_cell_style(self.radar_cells[row][column], None, radar_shot)

                home_shot = self.shots[self.active_player][row][column]
                home_ship = (
                    home_layout[row][column] if home_layout is not None else None
                )
                apply_cell_style(self.home_cells[row][column], home_ship, home_shot)
