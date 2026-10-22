import logging

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from client.core.coordinates import format_coordinate
from client.ui.constants import (
    BOARD_SIZE,
    CELL_SIZE,
    FLEET_SIZE,
    PROTOCOL_SHIP_ORDER,
    SHIP_CONFIG,
    Board,
)

logger = logging.getLogger(__name__)


class SetupScreen(QWidget):
    send_command = pyqtSignal(str)

    type ShipPlacement = tuple[int, int, int, int]

    def __init__(self) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.player = 1

        # Game State
        self.fleet_placed: dict[str, SetupScreen.ShipPlacement] = {}
        self.board_state: Board = [
            [None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
        ]

        # Drag State
        self.dragging_ship: str | None = None
        self.drag_horizontal: bool = True
        self.current_hover_valid: bool = False
        self.current_hover_cells: list[tuple[int, int]] = []
        self.current_hover_origin: tuple[int, int] = (-1, -1)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)

        # Left Side: The 10x10 Grid
        left_panel = QVBoxLayout()
        self.status_label = QLabel("Player 1: Draft your fleet")
        self.status_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; margin-bottom: 10px;"
        )
        left_panel.addWidget(self.status_label)

        self.grid_container = QFrame()
        self.grid_container.setStyleSheet(
            "background-color: #0b1a26; border-radius: 8px; padding: 10px;"
        )
        grid_layout = QGridLayout(self.grid_container)
        grid_layout.setSpacing(2)

        for col in range(BOARD_SIZE):
            lbl = QLabel(chr(65 + col))  # A-J
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid_layout.addWidget(lbl, 0, col + 1)
        for row in range(BOARD_SIZE):
            lbl = QLabel(str(row + 1))  # 1-10
            lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            grid_layout.addWidget(lbl, row + 1, 0)

        # Generate 10x10 Cell Array
        self.cells: list[list[QLabel]] = []
        for r in range(BOARD_SIZE):
            row_cells = []
            for c in range(BOARD_SIZE):
                cell = QLabel()
                cell.setFixedSize(CELL_SIZE, CELL_SIZE)
                cell.setProperty("r", r)  # Store cell coordinates in the widget
                cell.setProperty("c", c)
                grid_layout.addWidget(cell, r + 1, c + 1)
                row_cells.append(cell)
            self.cells.append(row_cells)

        left_panel.addWidget(self.grid_container)
        left_panel.addStretch()
        main_layout.addLayout(left_panel)

        # Right Side: The Dock & Controls
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

        dock_title = QLabel("Available Ships")
        dock_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_panel.addWidget(dock_title)

        self.ship_labels: dict[str, QLabel] = {}
        for ship_id, data in SHIP_CONFIG.items():
            lbl = QLabel(f"{data.name} ({data.length})")
            lbl.setFixedSize(140, CELL_SIZE)
            lbl.setStyleSheet(f"""
                background-color: {data.colour};
                color: white;
                font-weight: bold;
                border-radius: 4px;
                border: 2px solid white;
            """)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)

            # Install event filter so SetupScreen can catch clicks on these labels
            lbl.installEventFilter(self)
            self.ship_labels[ship_id] = lbl
            right_panel.addWidget(lbl)

        # Dynamic Keybind Instruction Label (Hidden by default)
        self.instruction_label = QLabel("Press 'R' to Rotate\nRight-Click to Cancel")
        self.instruction_label.setStyleSheet("color: #00FF00; font-weight: bold;")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_label.hide()
        right_panel.addWidget(self.instruction_label)

        right_panel.addStretch()

        self.btn_reset = QPushButton("Reset Board")
        self.btn_reset.clicked.connect(self.reset_board)
        right_panel.addWidget(self.btn_reset)

        self.btn_deploy = QPushButton("Deploy Fleet")
        self.btn_deploy.setFixedSize(140, 50)
        self.btn_deploy.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        self.btn_deploy.setEnabled(False)
        self.btn_deploy.clicked.connect(self.on_deploy_clicked)
        right_panel.addWidget(self.btn_deploy)

        main_layout.addLayout(right_panel)

        # The phantom ship which follows the cursor
        self.phantom = QLabel(self)
        self.phantom.hide()
        self.phantom.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        effect = QGraphicsOpacityEffect(self.phantom)
        effect.setOpacity(0.7)
        self.phantom.setGraphicsEffect(effect)

        self.clear_highlights()  # Initialize cell colors

    def eventFilter(self, source: QObject | None, event) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            for ship_id, lbl in self.ship_labels.items():
                if source == lbl and ship_id not in self.fleet_placed:
                    self._start_drag(ship_id)
                    return True
        return super().eventFilter(source, event)

    def _start_drag(self, ship_id: str) -> None:
        self.dragging_ship = ship_id
        self.drag_horizontal = True
        self.ship_labels[ship_id].hide()
        self.instruction_label.show()

        # Keep receiving mouse events if the cursor leaves the setup widget.
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.grabMouse()

        self._update_phantom_size()
        self.phantom.show()
        self._update_phantom_position(QCursor.pos())

    def _finish_drag(self, *, restore_ship: bool) -> None:
        ship_id = self.dragging_ship

        self.releaseMouse()
        self.phantom.hide()
        self.instruction_label.hide()

        if restore_ship and ship_id is not None:
            self.ship_labels[ship_id].show()

        self.dragging_ship = None
        self.drag_horizontal = True
        self.current_hover_origin = (-1, -1)
        self.clear_highlights()

    def _update_phantom_size(self) -> None:
        if not self.dragging_ship:
            return
        length = SHIP_CONFIG[self.dragging_ship].length
        color = SHIP_CONFIG[self.dragging_ship].colour

        w = (
            (CELL_SIZE * length) + (2 * (length - 1))
            if self.drag_horizontal
            else CELL_SIZE
        )
        h = (
            CELL_SIZE
            if self.drag_horizontal
            else (CELL_SIZE * length) + (2 * (length - 1))
        )

        self.phantom.setFixedSize(w, h)
        self.phantom.setStyleSheet(
            f"background-color: {color}; border: 2px dashed white;"
        )

    def _update_phantom_position(self, global_pos: QPoint) -> None:
        local_pos = self.mapFromGlobal(global_pos)
        self.phantom.move(local_pos.x() + 2, local_pos.y() + 2)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        if self.dragging_ship:
            self._update_phantom_position(event.globalPosition().toPoint())

            grid_pos = self.grid_container.mapFromGlobal(
                event.globalPosition().toPoint()
            )
            child = self.grid_container.childAt(grid_pos)

            if child and child.property("r") is not None:
                r, c = child.property("r"), child.property("c")
                self._highlight_cells(r, c)
            else:
                self.clear_highlights()
            event.accept()
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Intercepts the 'R' key to rotate the ship in mid-air."""
        if self.dragging_ship and event.key() == Qt.Key.Key_R:
            self.drag_horizontal = not self.drag_horizontal
            self._update_phantom_size()

            # Force a re-highlight in case rotation caused an overlap
            grid_pos = self.grid_container.mapFromGlobal(QCursor.pos())
            child = self.grid_container.childAt(grid_pos)
            if child is not None and child.property("r") is not None:
                self._highlight_cells(child.property("r"), child.property("c"))
            else:
                self.clear_highlights()
            event.accept()
        super().keyPressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        ship_id = self.dragging_ship

        if ship_id is None:
            super().mouseReleaseEvent(event)
            return

        should_place = (
            event.button() == Qt.MouseButton.LeftButton
            and self.current_hover_valid
            and bool(self.current_hover_cells)
        )

        if should_place:
            start_r, start_c = self.current_hover_origin
            length = SHIP_CONFIG[ship_id].length

            end_r = start_r if self.drag_horizontal else start_r + length - 1
            end_c = start_c + length - 1 if self.drag_horizontal else start_c

            self.fleet_placed[ship_id] = (start_r, start_c, end_r, end_c)

            for row, col in self.current_hover_cells:
                self.board_state[row][col] = ship_id

        self._finish_drag(restore_ship=not should_place)
        self.btn_deploy.setEnabled(len(self.fleet_placed) == FLEET_SIZE)

        event.accept()

    def _highlight_cells(self, r: int, c: int) -> None:
        if not self.dragging_ship:
            return
        self.clear_highlights()
        length = SHIP_CONFIG[self.dragging_ship].length

        valid = True
        cells_to_paint = []

        for i in range(length):
            rr = r if self.drag_horizontal else r + i
            cc = c + i if self.drag_horizontal else c

            if rr >= BOARD_SIZE or cc >= BOARD_SIZE:
                valid = False
                break

            # Check collision with already placed ships
            if self.board_state[rr][cc] is not None:
                valid = False

            cells_to_paint.append((rr, cc))

        color = "#4CAF50" if valid else "#F44336"  # Green or Red
        for rr, cc in cells_to_paint:
            self.cells[rr][cc].setStyleSheet(
                f"background-color: {color}; border: 1px solid white;"
            )

        self.current_hover_valid = valid
        self.current_hover_cells = cells_to_paint
        self.current_hover_origin = (r, c)

    def clear_highlights(self) -> None:
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                occupant = self.board_state[r][c]
                color = (
                    SHIP_CONFIG[occupant].colour if occupant is not None else "#1e3d59"
                )
                self.cells[r][c].setStyleSheet(
                    f"background-color: {color}; border: 1px solid #172a3a;"
                )

        self.current_hover_cells = []
        self.current_hover_valid = False

    def _set_status(self, text: str, *, error: bool = False) -> None:
        color = "#F44336" if error else "palette(text)"
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold; margin-bottom: 10px;"
        )

    def reset_board(self) -> None:
        if self.dragging_ship is not None:
            self._finish_drag(restore_ship=True)

        self.fleet_placed.clear()
        self.board_state = [
            [None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
        ]

        for lbl in self.ship_labels.values():
            lbl.show()

        self.clear_highlights()
        self.btn_deploy.setEnabled(False)
        self._set_status(f"Player {self.player}: Draft your fleet")

    def reset_for_player(self, player_id: int) -> None:
        self.player = player_id
        self.reset_board()

    def get_board_state(self) -> Board:
        """Returns a deep copy of the current board state."""
        return [row[:] for row in self.board_state]

    def on_deploy_clicked(self) -> None:
        if len(self.fleet_placed) != FLEET_SIZE:
            return

        # Fleet command format: FLEET: <Player>,<C>,<B>,<D>,<S>,<P>
        # Example: FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2
        parts = [f"FLEET: {self.player}"]

        for ship_id in PROTOCOL_SHIP_ORDER:
            start_row, start_column, end_row, end_column = self.fleet_placed[ship_id]

            parts.append(format_coordinate(start_row, start_column))
            parts.append(format_coordinate(end_row, end_column))

        self.btn_deploy.setEnabled(False)
        self.status_label.setText("Validating fleet geometry with server...")

        self.send_command.emit(",".join(parts))

    def process_server_response(self, response: str) -> bool:
        if response.startswith("NACK: BADCOORDS"):
            self.btn_deploy.setEnabled(True)
            self._set_status("Rejected: invalid geometry.", error=True)
            return True

        if response.startswith("NACK: OCCUPIED"):
            self.btn_deploy.setEnabled(True)
            self._set_status("Rejected: ships intersect.", error=True)
            return True

        if response.startswith("NACK: BADCMD"):
            self.btn_deploy.setEnabled(True)
            self._set_status("Protocol error: malformed fleet command.", error=True)
            return True

        return False
