from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class PassDeviceScreen(QWidget):
    ready = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(30)

        header_label = QLabel("CLASSIFIED")
        header_label.setStyleSheet(
            "color: #F44336; font-size: 36px; font-weight: bold; letter-spacing: 5px;"
        )
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        self.instruction_label = QLabel("Pass the device to Player X")
        self.instruction_label.setStyleSheet("font-size: 24px;")
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.instruction_label)

        subtext = QLabel("Do not look at the screen when it is not your turn.")
        subtext.setStyleSheet("color: #888888; font-size: 14px; font-style: italic;")
        subtext.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtext)

        layout.addSpacing(20)

        self.btn_ready = QPushButton("I am Player X - Ready")
        self.btn_ready.setFixedSize(300, 60)
        self.btn_ready.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ready.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.btn_ready.clicked.connect(self.ready)
        layout.addWidget(self.btn_ready, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_player(self, player: int) -> None:
        self.instruction_label.setText(f"Pass the device to Player {player}")
        self.btn_ready.setText(f"I am Player {player} - Ready")
