from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PassDeviceScreen(QWidget):
    ready = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        center_wrapper = QHBoxLayout()
        center_wrapper.setAlignment(Qt.AlignmentFlag.AlignCenter)

        panel = QFrame()
        panel.setMinimumSize(550, 350)
        panel.setStyleSheet("""
            QFrame {
                background-color: #0b1a26;
                border: 2px solid #172a3a;
                border-radius: 12px;
            }
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        panel.setGraphicsEffect(shadow)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.setSpacing(25)

        header_label = QLabel("CLASSIFIED")
        header_label.setStyleSheet("""
            color: #F44336;
            font-size: 42px;
            font-weight: 900;
            font-family: 'Consolas', 'Courier New', monospace;
            letter-spacing: 8px;
            border: none;
            background: transparent;
        """)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(header_label)

        self.instruction_label = QLabel("PASS DEVICE TO PLAYER X")
        self.instruction_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 22px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            border: none;
            background: transparent;
        """)
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.instruction_label)

        subtext = QLabel("Do not look at the screen when it is not your turn.")
        subtext.setStyleSheet("""
            color: #00FFCC;
            font-size: 14px;
            font-style: italic;
            font-family: 'Consolas', 'Courier New', monospace;
            border: none;
            background: transparent;
        """)
        subtext.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(subtext)

        panel_layout.addSpacing(15)

        self.btn_ready = QPushButton("I AM PLAYER X - READY")
        self.btn_ready.setFixedSize(350, 60)
        self.btn_ready.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ready.setStyleSheet("""
            QPushButton {
                background-color: #1a3320;
                color: #4CAF50;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Consolas', 'Courier New', monospace;
                border: 2px solid #2e5939;
                border-radius: 6px;
                padding: 12px;
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
        """)
        self.btn_ready.clicked.connect(self.ready)
        panel_layout.addWidget(self.btn_ready, alignment=Qt.AlignmentFlag.AlignCenter)

        center_wrapper.addWidget(panel)
        root_layout.addLayout(center_wrapper)

    def set_player(self, player: int) -> None:
        self.instruction_label.setText(f"PASS DEVICE TO PLAYER {player}")
        self.btn_ready.setText(f"I AM PLAYER {player} - READY")
