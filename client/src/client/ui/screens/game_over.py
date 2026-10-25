from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
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
        self.winner_label.setStyleSheet(
            "font-size: 36px; font-weight: bold; color: #4CAF50;"
        )
        main_layout.addWidget(self.winner_label)
        main_layout.addSpacing(20)

        grids_layout = QHBoxLayout()
        grids_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        p1_panel = QVBoxLayout()
        p1_title = QLabel("Player 1's Fleet")
        p1_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p1_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        p1_panel.addWidget(p1_title)
        self.p1_cells = create_grid(p1_panel, clickable=False)
        grids_layout.addLayout(p1_panel)

        grids_layout.addSpacing(60)

        p2_panel = QVBoxLayout()
        self.p2_title = QLabel("Player 2's Fleet")
        self.p2_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.p2_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        p2_panel.addWidget(self.p2_title)
        self.p2_cells = create_grid(p2_panel, clickable=False)
        grids_layout.addLayout(p2_panel)

        main_layout.addLayout(grids_layout)
        main_layout.addSpacing(20)

        create_legend(main_layout)
        main_layout.addSpacing(30)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(20)

        self.btn_play_again = QPushButton("Play Again")
        self.btn_play_again.setFixedSize(200, 50)
        self.btn_play_again.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-weight: bold; font-size: 16px;"
        )
        self.btn_play_again.clicked.connect(self.play_again_requested.emit)

        self.btn_main_menu = QPushButton("Main Menu")
        self.btn_main_menu.setFixedSize(200, 50)
        self.btn_main_menu.setStyleSheet(
            "background-color: #5D8AA8; color: white;"
            "font-weight: bold; font-size: 16px;"
        )
        self.btn_main_menu.clicked.connect(self.main_menu_requested.emit)

        btn_layout.addWidget(self.btn_play_again)
        btn_layout.addWidget(self.btn_main_menu)
        main_layout.addLayout(btn_layout)

    def set_results(
        self, winner_id: int, layouts: BoardStore, shots: BoardStore, *, ai_mode: bool
    ) -> None:
        if winner_id not in {1, 2}:
            raise ValueError(f"Invalid winner ID: {winner_id}")
        if winner_id == 1:
            self.winner_label.setText("VICTORY! Player 1 Wins!")
        else:
            self.winner_label.setText(
                "DEFEAT! The AI Wins!" if ai_mode else "VICTORY! Player 2 Wins!"
            )

        self.p2_title.setText("AI's Fleet" if ai_mode else "Player 2's Fleet")

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
                )

                p2_ship = p2_layout[row][column] if p2_layout is not None else None
                p2_shot = p2_shots[row][column] if p2_shots is not None else None
                apply_cell_style(
                    self.p2_cells[row][column],
                    p2_ship,
                    p2_shot,
                )
