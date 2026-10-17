from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class StartupScreen(QWidget):
    # Emit 'PVP' or 'AI' when the user makes a selection
    mode_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
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
        self.btn_pvp.clicked.connect(lambda: self.mode_selected.emit("PVP"))

        self.btn_ai = QPushButton("PLAYER VS AI (SINGLE PLAYER)")
        self.btn_ai.setFixedSize(300, 60)
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.clicked.connect(lambda: self.mode_selected.emit("AI"))

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(50)
        layout.addWidget(self.btn_pvp, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(15)
        layout.addWidget(self.btn_ai, alignment=Qt.AlignmentFlag.AlignCenter)
