from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from client.ui.board_utils import apply_cell_style, create_grid, create_legend
from client.ui.constants import BOARD_SIZE, BoardStore


class GameOverScreen(QWidget):
    play_again_requested = pyqtSignal()
    main_menu_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        self.winner_label = QLabel("VICTORY!")
        self.winner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.winner_label.setStyleSheet("""
            color: #4CAF50;
            font-size: 42px;
            font-weight: 900;
            font-family: 'Consolas', 'Courier New', monospace;
            letter-spacing: 5px;
        """)
        main_layout.addWidget(self.winner_label)
        main_layout.addSpacing(20)

        grids_layout = QHBoxLayout()
        grids_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        p1_panel = QVBoxLayout()
        p1_title = QLabel("PLAYER 1'S FLEET")
        p1_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p1_title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 18px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            margin-bottom: 5px;
        """)
        p1_panel.addWidget(p1_title)

        self.p1_cells = create_grid(p1_panel, clickable=False)

        p1_item = p1_panel.itemAt(p1_panel.count() - 1)
        assert p1_item is not None
        p1_container = p1_item.widget()
        assert p1_container is not None

        p1_shadow = QGraphicsDropShadowEffect()
        p1_shadow.setBlurRadius(20)
        p1_shadow.setColor(QColor(0, 0, 0, 150))
        p1_shadow.setOffset(0, 5)
        p1_container.setGraphicsEffect(p1_shadow)

        grids_layout.addLayout(p1_panel)

        grids_layout.addSpacing(60)

        p2_panel = QVBoxLayout()
        self.p2_title = QLabel("PLAYER 2'S FLEET")
        self.p2_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.p2_title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 18px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            margin-bottom: 5px;
        """)
        p2_panel.addWidget(self.p2_title)

        self.p2_cells = create_grid(p2_panel, clickable=False)

        p2_item = p2_panel.itemAt(p2_panel.count() - 1)
        assert p2_item is not None
        p2_container = p2_item.widget()
        assert p2_container is not None

        p2_shadow = QGraphicsDropShadowEffect()
        p2_shadow.setBlurRadius(20)
        p2_shadow.setColor(QColor(0, 0, 0, 150))
        p2_shadow.setOffset(0, 5)
        p2_container.setGraphicsEffect(p2_shadow)

        grids_layout.addLayout(p2_panel)

        main_layout.addLayout(grids_layout)
        main_layout.addSpacing(20)

        create_legend(main_layout)
        main_layout.addSpacing(30)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(20)

        self.btn_play_again = QPushButton("PLAY AGAIN")
        self.btn_play_again.setFixedSize(220, 55)
        self.btn_play_again.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play_again.setStyleSheet("""
            QPushButton {
                background-color: #1a3320;
                color: #4CAF50;
                font-weight: bold;
                font-size: 16px;
                font-family: 'Consolas', 'Courier New', monospace;
                border: 2px solid #2e5939;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #2e5939; color: #ffffff; }
            QPushButton:pressed {
                background-color: #4CAF50; color: #0b1a26; border: 2px solid #4CAF50;
            }
        """)
        self.btn_play_again.clicked.connect(self.play_again_requested.emit)

        self.btn_main_menu = QPushButton("MAIN MENU")
        self.btn_main_menu.setFixedSize(220, 55)
        self.btn_main_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_main_menu.setStyleSheet("""
            QPushButton {
                background-color: #3a1c1c;
                color: #F44336;
                font-weight: bold;
                font-size: 16px;
                font-family: 'Consolas', 'Courier New', monospace;
                border: 2px solid #5a2c2c;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #5a2c2c; color: #ffffff; }
            QPushButton:pressed {
                background-color: #F44336; color: #ffffff; border: 2px solid #F44336;
            }
        """)
        self.btn_main_menu.clicked.connect(self.main_menu_requested.emit)

        btn_layout.addWidget(self.btn_play_again)
        btn_layout.addWidget(self.btn_main_menu)
        main_layout.addLayout(btn_layout)

    def set_results(
        self, winner_id: int, layouts: BoardStore, shots: BoardStore, *, ai_mode: bool
    ) -> None:
        if winner_id not in {1, 2}:
            raise ValueError(f"Invalid winner ID: {winner_id}")

        base_title_style = (
            "font-size: 42px; font-weight: 900;"
            "font-family: 'Consolas', 'Courier New', monospace; letter-spacing: 5px;"
        )

        if winner_id == 1:
            self.winner_label.setText("VICTORY! PLAYER 1 WINS")
            self.winner_label.setStyleSheet(f"color: #4CAF50; {base_title_style}")
        else:
            text = "DEFEAT! AI WINS" if ai_mode else "VICTORY! PLAYER 2 WINS"
            color = "#F44336" if ai_mode else "#4CAF50"
            self.winner_label.setText(text)
            self.winner_label.setStyleSheet(f"color: {color}; {base_title_style}")

        self.p2_title.setText("AI'S FLEET" if ai_mode else "PLAYER 2'S FLEET")

        p1_layout = layouts.get(1)
        p2_layout = layouts.get(2)
        p1_shots = shots.get(1)
        p2_shots = shots.get(2)

        for row in range(BOARD_SIZE):
            for column in range(BOARD_SIZE):
                p1_ship = p1_layout[row][column] if p1_layout is not None else None
                p1_shot = p1_shots[row][column] if p1_shots is not None else None
                apply_cell_style(
                    self.p1_cells[row][column],
                    p1_ship,
                    p1_shot,
                    interactive=False,
                )

                p2_ship = p2_layout[row][column] if p2_layout is not None else None
                p2_shot = p2_shots[row][column] if p2_shots is not None else None
                apply_cell_style(
                    self.p2_cells[row][column],
                    p2_ship,
                    p2_shot,
                    interactive=False,
                )
