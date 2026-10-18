from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class StartupScreen(QWidget):
    send_command = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        title_label = QLabel("BATTLESHIP")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("STM32 Tactical Terminal")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Mode Selection Buttons
        self.btn_pvp = QPushButton("PLAYER VS PLAYER (HOTSEAT)")
        self.btn_pvp.setFixedSize(300, 60)
        self.btn_pvp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pvp.clicked.connect(lambda: self._select_mode("PVP"))

        self.btn_ai = QPushButton("PLAYER VS AI (SINGLE PLAYER)")
        self.btn_ai.setFixedSize(300, 60)
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.clicked.connect(lambda: self._select_mode("AI"))

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(50)
        layout.addWidget(self.btn_pvp, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(15)
        layout.addWidget(self.btn_ai, alignment=Qt.AlignmentFlag.AlignCenter)

    def _select_mode(self, mode: str) -> None:
        self.btn_pvp.setEnabled(False)
        self.btn_ai.setEnabled(False)
        self.send_command.emit(f"NEW: {mode}")
