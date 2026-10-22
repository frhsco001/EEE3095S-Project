import logging

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from client.core.coordinates import format_coordinate, iter_coordinate_range
from client.ui.constants import (
    BOARD_SIZE,
    CELL_SIZE,
    COLOR_HIT,
    COLOR_MISS,
    COLOR_WATER,
    SHIP_CONFIG,
    BoardStore,
    _empty_board,
)

logger = logging.getLogger(__name__)


class GameplayScreen(QWidget):
    send_command = pyqtSignal(str)
    turn_ended = pyqtSignal(int)

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
        self.shots = {1: _empty_board(), 2: _empty_board()}

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

        self.radar_cells = self._create_grid(radar_panel, clickable=True)
        grids_layout.addLayout(radar_panel)

        grids_layout.addSpacing(60)

        # Right Panel: Home Fleet (Non-Clickable)
        home_panel = QVBoxLayout()
        home_title = QLabel("Home Fleet")
        home_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        home_panel.addWidget(home_title)

        self.home_cells = self._create_grid(home_panel, clickable=False)
        grids_layout.addLayout(home_panel)

        main_layout.addLayout(grids_layout)
        main_layout.addSpacing(20)

        self._create_legend(main_layout)
        main_layout.addStretch()

    def _create_legend(self, parent_layout: QVBoxLayout) -> None:
        legend_container = QFrame()
        legend_container.setStyleSheet(
            "QFrame { background-color: #0b1a26; border-radius: 8px; padding: 10px; }"
        )

        legend_layout = QHBoxLayout(legend_container)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend_layout.setSpacing(25)

        title = QLabel("KEY:")
        title.setStyleSheet(
            "font-weight: bold; font-size: 16px;"
            "color: #FFFFFF; background: transparent;"
        )
        legend_layout.addWidget(title)

        items = [
            ("Water", COLOR_WATER, "1px solid #172a3a", "", "#FFFFFF"),
            ("Ship", SHIP_CONFIG["C"].colour, "1px solid #172a3a", "", "#FFFFFF"),
            ("Miss", COLOR_MISS, "1px solid #172a3a", "O", "#000000"),
            ("Hit", COLOR_WATER, f"2px solid {COLOR_HIT}", "X", COLOR_HIT),
            ("Sunk", COLOR_WATER, f"2px solid {COLOR_HIT}", "S", COLOR_HIT),
        ]

        for label_text, bg, border, txt, txt_color in items:
            row = QHBoxLayout()
            row.setSpacing(8)

            icon = QLabel(txt)
            icon.setFixedSize(CELL_SIZE, CELL_SIZE)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet(
                f"background-color: {bg};"
                f"border: {border};"
                f"color: {txt_color};"
                f"font-weight: bold;"
                f"font-size: 16px;"
            )

            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                "font-weight: bold; font-size: 14px;"
                "color: #FFFFFF; background: transparent;"
            )
            row.addWidget(icon)
            row.addWidget(lbl)
            legend_layout.addLayout(row)

        parent_layout.addWidget(
            legend_container, alignment=Qt.AlignmentFlag.AlignCenter
        )

    def _create_grid(
        self, parent: QVBoxLayout, clickable: bool
    ) -> list[list[QPushButton | QLabel]]:
        container = QFrame()
        container.setStyleSheet(
            "background-color: #0b1a26; border-radius: 8px; padding: 10px;"
        )
        layout = QGridLayout(container)
        layout.setSpacing(2)

        for col in range(BOARD_SIZE):
            lbl = QLabel(chr(65 + col))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl, 0, col + 1)

        for row in range(BOARD_SIZE):
            lbl = QLabel(str(row + 1))
            lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            layout.addWidget(lbl, row + 1, 0)

        cells: list[list[QPushButton | QLabel]] = []
        for r in range(BOARD_SIZE):
            row_cells: list[QPushButton | QLabel] = []
            for c in range(BOARD_SIZE):
                if clickable:
                    btn = QPushButton()
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.clicked.connect(
                        lambda _, rr=r, cc=c: self._on_radar_click(rr, cc)
                    )
                    widget: QWidget = btn
                else:
                    widget = QLabel()
                    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

                widget.setFixedSize(CELL_SIZE, CELL_SIZE)
                layout.addWidget(widget, r + 1, c + 1)
                row_cells.append(widget)
            cells.append(row_cells)

        parent.addWidget(container)
        return cells

    def initialize_game(self, boards: BoardStore) -> None:
        self._reset_game_state()
        self.layouts = boards
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
            # Format: SUNK: <TargetPlayer>,<ShipChar>,<StartCoord>,<EndCoord>
            parts = response.split(",")
            if len(parts) != 4:
                logger.warning("Malformed SUNK response: %r", response)
                return False

            _, target_text = parts[0].split(":", maxsplit=1)
            target_player = int(target_text.strip())

            ship_char = parts[1].strip()
            start_coord = parts[2].strip()
            end_coord = parts[3].strip()

            self._mark_sunk_ship(target_player, start_coord, end_coord)

            if ship_char not in SHIP_CONFIG:
                logger.warning("Malformed SUNK response: %r", response)
                return False
            ship_name = SHIP_CONFIG[ship_char].name
            self.log_label.setText(f"Direct Hit! You sunk their {ship_name}!")
            self._draw_boards()
            self._schedule_turn_end(target_player)
            return True

        if response.startswith("WIN:"):
            # Format: WIN: <Winner>,<ShipChar>,<StartCoord>,<EndCoord>
            parts = response.split(",")
            start_coord = parts[2].strip()
            end_coord = parts[3].strip()

            self._mark_sunk_ship(target_player, start_coord, end_coord)

            self.log_label.setText("VICTORY! All enemy ships destroyed.")
            self._draw_boards()
            return True

        return False

    def _schedule_turn_end(self, next_player: int) -> None:
        QTimer.singleShot(1500, lambda: self.turn_ended.emit(next_player))

    def _draw_boards(self) -> None:
        target = 2 if self.active_player == 1 else 1

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                radar_shot = self.shots[target][r][c]
                self._apply_style(self.radar_cells[r][c], None, radar_shot)

                home_shot = self.shots[self.active_player][r][c]
                home_ship = None
                if self.layouts.get(self.active_player):
                    home_ship = self.layouts[self.active_player][r][c]

                self._apply_style(self.home_cells[r][c], home_ship, home_shot)

    def _apply_style(
        self, widget: QWidget, ship_id: str | None, shot_type: str | None
    ) -> None:
        bg_color = COLOR_WATER
        border = "1px solid #172a3a"
        text = ""
        text_color = "#FFFFFF"
        hover_css = ""

        if ship_id is not None:
            bg_color = SHIP_CONFIG[ship_id].colour

        if shot_type == "MISS":
            bg_color = COLOR_MISS
            text_color = "#000000"
            text = "O"
        elif shot_type == "HIT":
            text_color = COLOR_HIT
            text = "X"
            border = f"2px solid {COLOR_HIT}"
        elif shot_type == "SUNK":
            text_color = COLOR_HIT
            text = "S"
            border = f"2px solid {COLOR_HIT}"

        if isinstance(widget, QPushButton):
            if shot_type is None:
                hover_css = "QPushButton:hover { background-color: #2c5987; }"
                widget.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                widget.setCursor(Qt.CursorShape.ArrowCursor)

        widget_type = "QPushButton" if isinstance(widget, QPushButton) else "QLabel"

        widget.setStyleSheet(f"""
            {widget_type} {{
                background-color: {bg_color};
                color: {text_color};
                font-weight: bold;
                font-size: 16px;
                border: {border};
            }}
            {hover_css}
        """)

        if isinstance(widget, (QPushButton, QLabel)):
            widget.setText(text)
