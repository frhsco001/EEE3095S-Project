from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from client.ui.constants import (
    BOARD_SIZE,
    CELL_SIZE,
    COLOR_HIT,
    COLOR_MISS,
    COLOR_WATER,
    SHIP_CONFIG,
    Board,
)

type BoardCell = QPushButton | QLabel
type CellClickHandler = Callable[[int, int], None]


def create_legend(parent_layout: QVBoxLayout | QHBoxLayout) -> None:
    legend_container = QFrame()
    legend_container.setStyleSheet(
        "QFrame { background-color: #0b1a26; border-radius: 8px; padding: 10px; }"
    )

    legend_layout = QHBoxLayout(legend_container)
    legend_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    legend_layout.setSpacing(25)

    title = QLabel("KEY:")
    title.setStyleSheet(
        "font-weight: bold; font-size: 16px; color: #FFFFFF; background: transparent;"
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
            f"background-color: {bg}; border: {border}; color: {txt_color}; "
            f"font-weight: bold; font-size: 16px;"
        )

        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            "font-weight: bold; font-size: 14px;"
            "color: #FFFFFF; background: transparent;"
        )
        row.addWidget(icon)
        row.addWidget(lbl)
        legend_layout.addLayout(row)

    parent_layout.addWidget(legend_container, alignment=Qt.AlignmentFlag.AlignCenter)


def create_grid(
    parent: QVBoxLayout | QHBoxLayout,
    *,
    clickable: bool,
    on_click: CellClickHandler | None = None,
) -> list[list[BoardCell]]:
    if clickable and on_click is None:
        raise ValueError("Clickable grids require an on_click callback")
    container = QFrame()
    container.setStyleSheet(
        "QFrame { background-color: #0b1a26; border-radius: 8px; padding: 10px; }"
    )
    layout = QGridLayout(container)
    layout.setSpacing(2)

    for col in range(BOARD_SIZE):
        lbl = QLabel(chr(65 + col))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl, 0, col + 1)

    for row in range(BOARD_SIZE):
        lbl = QLabel(str(row + 1))
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl, row + 1, 0)

    cells: list[list[BoardCell]] = []
    for r in range(BOARD_SIZE):
        row_cells: list[BoardCell] = []
        for c in range(BOARD_SIZE):
            if clickable:
                btn = QPushButton()
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                if on_click:
                    btn.clicked.connect(lambda _, rr=r, cc=c: on_click(rr, cc))
                widget = btn
            else:
                widget = QLabel()
                widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

            widget.setFixedSize(CELL_SIZE, CELL_SIZE)
            layout.addWidget(widget, r + 1, c + 1)
            row_cells.append(widget)
        cells.append(row_cells)

    parent.addWidget(container)
    return cells


def apply_cell_style(
    widget: BoardCell,
    ship_id: str | None,
    shot_type: str | None,
    *,
    interactive: bool = True,
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
    elif shot_type is not None and shot_type.startswith("SUNK:"):
        _, sunk_id = shot_type.split(":", maxsplit=1)
        bg_color = SHIP_CONFIG[sunk_id].colour
        text_color = COLOR_HIT
        text = "S"
        border = f"2px solid {COLOR_HIT}"

    if isinstance(widget, QPushButton):
        if shot_type is None and interactive:
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
            border-radius: 8px;
        }}
        {hover_css}
    """)

    if isinstance(widget, (QPushButton, QLabel)):
        widget.setText(text)


def create_empty_board() -> Board:
    return [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
