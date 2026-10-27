import logging

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from client.core.coordinates import format_coordinate
from client.ui.board_utils import create_empty_board
from client.ui.constants import (
    BOARD_SIZE,
    CELL_SIZE,
    FLEET_SIZE,
    PROTOCOL_SHIP_ORDER,
    SHIP_CONFIG,
    Board,
)

logger = logging.getLogger(__name__)

type ShipPlacement = tuple[int, int, int, int]


class SetupScreen(QWidget):
    send_command = pyqtSignal(str)
    main_menu_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Game State
        self.player = 1
        self.fleet_placed: dict[str, ShipPlacement] = {}
        self.board_state: Board = create_empty_board()
        self.awaiting_validation = False

        # Drag State
        self.dragging_ship: str | None = None
        self.drag_horizontal: bool = True
        self.drag_original_placement: ShipPlacement | None = None

        self.current_hover_valid: bool = False
        self.current_hover_cells: list[tuple[int, int]] = []
        self.current_hover_origin: tuple[int, int] = (-1, -1)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.addStretch()

        center_block = QHBoxLayout()
        center_block.addStretch()

        left_panel = QVBoxLayout()

        self.status_label = QLabel("Player 1: Draft your fleet")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #00FFCC;
            font-size: 18px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            margin-bottom: 10px;
        """)
        left_panel.addWidget(self.status_label)

        self.grid_container = QFrame()
        self.grid_container.setStyleSheet(
            "QFrame { background-color: #0b1a26; border-radius: 8px; padding: 10px; }"
        )

        grid_shadow = QGraphicsDropShadowEffect()
        grid_shadow.setBlurRadius(20)
        grid_shadow.setColor(QColor(0, 0, 0, 150))
        grid_shadow.setOffset(0, 5)
        self.grid_container.setGraphicsEffect(grid_shadow)

        grid_layout = QGridLayout(self.grid_container)
        grid_layout.setSpacing(2)

        for col in range(BOARD_SIZE):
            lbl = QLabel(chr(65 + col))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #FFFFFF; font-weight: bold;")
            grid_layout.addWidget(lbl, 0, col + 1)

        for row in range(BOARD_SIZE):
            lbl = QLabel(str(row + 1))
            lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            lbl.setStyleSheet("color: #FFFFFF; font-weight: bold; padding-right: 5px;")
            grid_layout.addWidget(lbl, row + 1, 0)

        # Generate 10x10 Cell Array
        self.cells: list[list[QLabel]] = []
        for r in range(BOARD_SIZE):
            row_cells = []
            for c in range(BOARD_SIZE):
                cell = QLabel()
                cell.setFixedSize(CELL_SIZE, CELL_SIZE)
                cell.setProperty("r", r)
                cell.setProperty("c", c)

                cell.installEventFilter(self)

                grid_layout.addWidget(cell, r + 1, c + 1)
                row_cells.append(cell)
            self.cells.append(row_cells)

        left_panel.addWidget(
            self.grid_container, alignment=Qt.AlignmentFlag.AlignCenter
        )
        left_panel.addStretch()

        center_block.addLayout(left_panel)
        center_block.addSpacing(50)

        control_panel = QFrame()
        control_panel.setStyleSheet("""
            QFrame {
                background-color: #0b1a26;
                border: 2px solid #172a3a;
                border-radius: 12px;
            }
        """)

        panel_shadow = QGraphicsDropShadowEffect()
        panel_shadow.setBlurRadius(25)
        panel_shadow.setColor(QColor(0, 0, 0, 180))
        panel_shadow.setOffset(0, 8)
        control_panel.setGraphicsEffect(panel_shadow)

        right_panel = QVBoxLayout(control_panel)
        right_panel.setContentsMargins(20, 20, 20, 20)
        right_panel.setSpacing(15)

        dock_title = QLabel("AVAILABLE SHIPS")
        dock_title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 16px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            border: none;
        """)
        dock_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_panel.addWidget(dock_title)

        self.ship_labels: dict[str, QLabel] = {}
        for ship_id, data in SHIP_CONFIG.items():
            lbl = QLabel(f"{data.name} ({data.length})")
            lbl.setFixedSize(140, CELL_SIZE)
            lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: {data.colour};
                    color: white;
                    font-weight: bold;
                    font-family: 'Consolas', 'Courier New', monospace;
                    border-radius: 4px;
                    border: 2px solid #FFFFFF;
                }}
                QLabel:hover {{
                    border: 2px solid #00FFCC;
                }}
            """)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            sp = lbl.sizePolicy()
            sp.setRetainSizeWhenHidden(True)
            lbl.setSizePolicy(sp)

            lbl.installEventFilter(self)

            self.ship_labels[ship_id] = lbl
            right_panel.addWidget(lbl)

        self.instruction_label = QLabel("Press 'R' to Rotate\nRight-Click to Cancel")
        self.instruction_label.setStyleSheet("""
            color: #FF9800;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            border: none;
        """)
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp_inst = self.instruction_label.sizePolicy()
        sp_inst.setRetainSizeWhenHidden(True)
        self.instruction_label.setSizePolicy(sp_inst)
        self.instruction_label.hide()
        right_panel.addWidget(self.instruction_label)

        right_panel.addSpacing(10)

        btn_base_style = """
            QPushButton {
                font-weight: bold;
                font-size: 14px;
                font-family: 'Consolas', 'Courier New', monospace;
                border-radius: 6px;
                padding: 10px;
            }
        """

        self.btn_reset = QPushButton("RESET BOARD")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet(
            btn_base_style
            + """
            QPushButton {
                background-color: #132a40;
                color: #FFFFFF;
                border: 2px solid #1c3d5a;
            }
            QPushButton:hover {
                background-color: #1c3d5a;
                border: 2px solid #2b5c87;
            }
            QPushButton:pressed {
                background-color: #00FFCC;
                color: #0b1a26;
                border: 2px solid #00FFCC;
            }
        """
        )
        self.btn_reset.clicked.connect(self.reset_board)
        right_panel.addWidget(self.btn_reset)

        self.btn_deploy = QPushButton("DEPLOY FLEET")
        self.btn_deploy.setFixedSize(140, 50)
        self.btn_deploy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deploy.setStyleSheet(
            btn_base_style
            + """
            QPushButton {
                background-color: #1a3320;
                color: #4CAF50;
                border: 2px solid #2e5939;
            }
            QPushButton:hover {
                background-color: #2e5939;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #4CAF50;
                color: #0b1a26;
                border: 2px solid #4CAF50;
            }
            QPushButton:disabled {
                background-color: #060e15;
                color: #3b4e60;
                border: 2px solid #0b1a26;
            }
        """
        )
        self.btn_deploy.setEnabled(False)
        self.btn_deploy.clicked.connect(self.on_deploy_clicked)
        right_panel.addWidget(self.btn_deploy)

        right_panel.addStretch()

        center_block.addWidget(control_panel)
        center_block.addStretch()

        main_layout.addLayout(center_block)
        main_layout.addStretch()

        bottom_layout = QHBoxLayout()
        self.btn_main_menu = QPushButton("ABORT TO MENU")
        self.btn_main_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_main_menu.setStyleSheet("""
            QPushButton {
                background-color: #3a1c1c;
                color: #F44336;
                font-weight: bold;
                font-family: 'Consolas', 'Courier New', monospace;
                padding: 8px 16px;
                border: 2px solid #5a2c2c;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #5a2c2c;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #F44336;
                color: #ffffff;
                border: 2px solid #F44336;
            }
        """)
        self.btn_main_menu.clicked.connect(self._on_main_menu_clicked)

        bottom_layout.addWidget(self.btn_main_menu)
        bottom_layout.addStretch()

        main_layout.addLayout(bottom_layout)

        # The phantom ship which follows the cursor
        self.phantom = QLabel(self)
        self.phantom.hide()
        self.phantom.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        effect = QGraphicsOpacityEffect(self.phantom)
        effect.setOpacity(0.7)
        self.phantom.setGraphicsEffect(effect)

        self.clear_highlights()

    def _set_setup_enabled(self, enabled: bool) -> None:
        self.btn_reset.setEnabled(enabled)
        self.btn_main_menu.setEnabled(enabled)

        for ship_label in self.ship_labels.values():
            ship_label.setEnabled(enabled)

        for row in self.cells:
            for cell in row:
                cell.setEnabled(enabled)

        if not enabled and self.dragging_ship is not None:
            self._finish_drag(restore=True)

        self.clear_highlights()

    def _update_deploy_button(self) -> None:
        enabled = not self.awaiting_validation and len(self.fleet_placed) == FLEET_SIZE

        self.btn_deploy.setEnabled(enabled)
        self.btn_deploy.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    def _begin_validation(self) -> None:
        self.awaiting_validation = True
        self._set_setup_enabled(False)
        self._update_deploy_button()
        self._set_status("Validating fleet geometry with server...")

    def _finish_validation(self) -> None:
        self.awaiting_validation = False
        self._set_setup_enabled(True)
        self._update_deploy_button()

    def _on_main_menu_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            "Return to Main Menu",
            "Are you sure you want to return to the main menu? "
            "This will end the current game.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.main_menu_requested.emit()

    def eventFilter(self, source: QObject | None, event: QEvent) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        if self.awaiting_validation:
            return super().eventFilter(source, event)

        if (
            event.type() == QEvent.Type.MouseButtonPress
            and isinstance(event, QMouseEvent)
            and event.button() == Qt.MouseButton.LeftButton
        ):
            for ship_id, lbl in self.ship_labels.items():
                if source == lbl and ship_id not in self.fleet_placed:
                    self._start_drag(ship_id, from_grid=False)
                    return True

            if isinstance(source, QLabel) and source.property("r") is not None:
                r, c = source.property("r"), source.property("c")
                ship_id = self.board_state[r][c]

                if ship_id is not None and self.dragging_ship is None:
                    self._start_drag(ship_id, from_grid=True)
                    return True

        return super().eventFilter(source, event)

    def _start_drag(self, ship_id: str, from_grid: bool = False) -> None:
        self.dragging_ship = ship_id

        if from_grid:
            self.drag_original_placement = self.fleet_placed[ship_id]
            start_r, start_c, end_r, end_c = self.drag_original_placement

            self.drag_horizontal = start_r == end_r

            del self.fleet_placed[ship_id]
            min_r, max_r = min(start_r, end_r), max(start_r, end_r)
            min_c, max_c = min(start_c, end_c), max(start_c, end_c)

            for row in range(min_r, max_r + 1):
                for column in range(min_c, max_c + 1):
                    self.board_state[row][column] = None

            self._update_deploy_button()
            self.clear_highlights()
        else:
            self.drag_original_placement = None
            self.drag_horizontal = True
            self.ship_labels[ship_id].hide()

        self.instruction_label.show()
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.grabMouse()

        self._update_phantom_size()
        self.phantom.show()
        self.phantom.raise_()
        self._update_phantom_position(QCursor.pos())

    def _finish_drag(self, *, restore: bool) -> None:
        ship_id = self.dragging_ship

        self.releaseMouse()
        self.phantom.hide()
        self.instruction_label.hide()

        if restore and ship_id is not None:
            if self.drag_original_placement is not None:
                start_r, start_c, end_r, end_c = self.drag_original_placement
                self.fleet_placed[ship_id] = self.drag_original_placement

                min_r, max_r = min(start_r, end_r), max(start_r, end_r)
                min_c, max_c = min(start_c, end_c), max(start_c, end_c)

                for r in range(min_r, max_r + 1):
                    for c in range(min_c, max_c + 1):
                        self.board_state[r][c] = ship_id
            else:
                self.ship_labels[ship_id].show()

        self.dragging_ship = None
        self.drag_horizontal = True
        self.drag_original_placement = None
        self.current_hover_origin = (-1, -1)
        self.clear_highlights()
        self.update()

    def cancel_pending_interaction(self) -> None:
        if self.dragging_ship is not None:
            self._finish_drag(restore=True)

        self.awaiting_validation = False
        self._set_setup_enabled(True)
        self._update_deploy_button()

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
            f"background-color: {color}; border: 2px dashed white; border-radius: 4px;"
        )

    def _update_phantom_position(self, global_pos: QPoint) -> None:
        local_pos = self.mapFromGlobal(global_pos)
        self.phantom.move(local_pos.x() + 2, local_pos.y() + 2)
        self.update()  # Fix phantom ghost trails

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
            return
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
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
            return
        if self.dragging_ship and event.key() == Qt.Key.Key_Escape:
            self._finish_drag(restore=True)
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        ship_id = self.dragging_ship

        if ship_id is None:
            super().mouseReleaseEvent(event)
            return

        if event.button() == Qt.MouseButton.RightButton:
            self._finish_drag(restore=True)
            event.accept()
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

        self._finish_drag(restore=not should_place)
        self._update_deploy_button()

        event.accept()

    def _highlight_cells(self, row: int, column: int) -> None:
        if not self.dragging_ship:
            return
        self.clear_highlights()
        length = SHIP_CONFIG[self.dragging_ship].length

        valid = True
        cells_to_paint = []

        for i in range(length):
            candidate_row = row if self.drag_horizontal else row + i
            candidate_col = column + i if self.drag_horizontal else column

            if candidate_row >= BOARD_SIZE or candidate_col >= BOARD_SIZE:
                valid = False
                break

            # Check collision with already placed ships
            if self.board_state[candidate_row][candidate_col] is not None:
                valid = False

            cells_to_paint.append((candidate_row, candidate_col))

        color = "#4CAF50" if valid else "#F44336"  # Green or Red
        for candidate_row, candidate_col in cells_to_paint:
            self.cells[candidate_row][candidate_col].setStyleSheet(
                f"background-color: {color}; border: 1px solid white;"
                "border-radius: 4px;"
            )

        self.current_hover_valid = valid
        self.current_hover_cells = cells_to_paint
        self.current_hover_origin = (row, column)

    def clear_highlights(self) -> None:
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                occupant = self.board_state[r][c]
                color = (
                    SHIP_CONFIG[occupant].colour if occupant is not None else "#1e3d59"
                )
                self.cells[r][c].setStyleSheet(
                    f"background-color: {color}; border: 1px solid #172a3a;"
                    "border-radius: 4px;"
                )

                if occupant is not None:
                    self.cells[r][c].setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    self.cells[r][c].setCursor(Qt.CursorShape.ArrowCursor)

        self.current_hover_cells = []
        self.current_hover_valid = False

    def _set_status(self, text: str, *, error: bool = False) -> None:
        color = "#F44336" if error else "#00FFCC"
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold; "
            f"font-family: 'Consolas', 'Courier New', monospace; margin-bottom: 10px;"
        )

    def reset_board(self) -> None:
        if self.dragging_ship is not None:
            self._finish_drag(restore=True)

        self.awaiting_validation = False
        self.fleet_placed.clear()
        self.board_state = create_empty_board()

        for lbl in self.ship_labels.values():
            lbl.show()

        self._set_setup_enabled(True)
        self.clear_highlights()
        self._update_deploy_button()

        self._set_status(f"Player {self.player}: Draft your fleet")

    def reset_for_player(self, player_id: int) -> None:
        if player_id not in {1, 2}:
            raise ValueError(f"Invalid player ID: {player_id}")

        self.player = player_id
        self.reset_board()

    def get_board_state(self) -> Board:
        """Returns an independent copy of the current board state."""
        return [row[:] for row in self.board_state]

    def on_deploy_clicked(self) -> None:
        if self.awaiting_validation:
            return

        if len(self.fleet_placed) != FLEET_SIZE:
            return

        parts = [f"FLEET: {self.player}"]

        for ship_id in PROTOCOL_SHIP_ORDER:
            start_row, start_column, end_row, end_column = self.fleet_placed[ship_id]

            parts.append(format_coordinate(start_row, start_column))
            parts.append(format_coordinate(end_row, end_column))

        self._begin_validation()
        self.send_command.emit(",".join(parts))

    def process_server_response(self, response: str) -> bool:
        if response.startswith("NACK: BADCOORDS"):
            message = "Rejected: invalid geometry."
        elif response.startswith("NACK: OCCUPIED"):
            message = "Rejected: ships intersect."
        elif response.startswith("NACK: BADCMD"):
            message = "Protocol error: malformed fleet command."
        elif response.startswith("NACK:") and self.awaiting_validation:
            reason = response.removeprefix("NACK:").strip()
            message = f"Fleet rejected: {reason or 'unknown reason'}"
        else:
            return False

        self._finish_validation()
        self._set_status(message, error=True)
        return True
