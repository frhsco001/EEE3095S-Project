from PyQt6.QtCore import Qt, QTimer, pyqtSignal
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

from client.core.serial_worker import ConnectionState


class StartupScreen(QWidget):
    send_command = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._current_state = ConnectionState.CONNECTING
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._hide_status_bar_if_connected)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Dynamic Status Bar
        self.status_bar = QLabel("CONNECTING: Searching for device...")
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_bar.setFixedHeight(40)
        self._set_status_color("#FF9800")
        root_layout.addWidget(self.status_bar, alignment=Qt.AlignmentFlag.AlignTop)

        center_wrapper = QHBoxLayout()
        center_wrapper.setAlignment(Qt.AlignmentFlag.AlignCenter)

        panel = QFrame()
        panel.setFixedSize(550, 450)
        panel.setObjectName("MainPanel")
        panel.setStyleSheet("""
            QFrame#MainPanel {
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
        panel_layout.setSpacing(20)

        # Title
        title_label = QLabel("BATTLESHIP")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 52px;
            font-weight: 900;
            letter-spacing: 5px;
            background: transparent;
            border: none;
        """)

        # Subtitle
        subtitle_label = QLabel("STM32 TERMINAL")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            color: #00FFCC;
            font-size: 15px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-weight: bold;
            letter-spacing: 3px;
            background: transparent;
            border: none;
        """)

        btn_style = """
            QPushButton {
                background-color: #132a40;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Consolas', 'Courier New', monospace;
                border: 2px solid #1c3d5a;
                border-radius: 6px;
                padding: 10px;
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
            QPushButton:disabled {
                background-color: #060e15;
                color: #3b4e60;
                border: 2px solid #0b1a26;
            }
        """

        self.btn_pvp = QPushButton("PLAYER VS PLAYER (HOTSEAT)")
        self.btn_pvp.setFixedSize(350, 55)
        self.btn_pvp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pvp.setStyleSheet(btn_style)
        self.btn_pvp.clicked.connect(lambda: self._select_mode("PVP"))

        self.btn_ai = QPushButton("PLAYER VS AI (SINGLE PLAYER)")
        self.btn_ai.setFixedSize(350, 55)
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.setStyleSheet(btn_style)
        self.btn_ai.clicked.connect(lambda: self._select_mode("AI"))

        panel_layout.addStretch()
        panel_layout.addWidget(title_label)
        panel_layout.addWidget(subtitle_label)
        panel_layout.addSpacing(40)
        panel_layout.addWidget(self.btn_pvp, alignment=Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.btn_ai, alignment=Qt.AlignmentFlag.AlignCenter)
        panel_layout.addStretch()

        center_wrapper.addWidget(panel)
        root_layout.addLayout(center_wrapper)

        # Start with buttons disabled until hardware connects
        self.btn_pvp.setEnabled(False)
        self.btn_ai.setEnabled(False)

    def update_connection_state(self, state: str, message: str) -> None:
        self._current_state = state
        self.status_bar.show()

        states = {
            ConnectionState.CONNECTING: (f"CONNECTING: {message}", "#FF9800", False),
            ConnectionState.CONNECTED: (f"CONNECTED: {message}", "#4CAF50", True),
            ConnectionState.ERROR: (f"DISCONNECTED: {message}", "#F44336", False),
            ConnectionState.DISCONNECTED: (
                f"DISCONNECTED: {message}",
                "#888888",
                False,
            ),
        }

        config = states.get(
            ConnectionState(state),
            (f"UNKNOWN CONNECTION STATE: {state}", "#F44336", False),
        )

        text, color, enabled = config

        self.status_bar.setText(text)
        self._set_status_color(color)

        self.btn_pvp.setEnabled(enabled)
        self.btn_ai.setEnabled(enabled)

        if enabled:
            self._status_timer.start(2500)
        else:
            self._status_timer.stop()

    def _hide_status_bar_if_connected(self) -> None:
        if self._current_state == ConnectionState.CONNECTED:
            self.status_bar.hide()

    def _set_status_color(self, color: str) -> None:
        self.status_bar.setStyleSheet(
            f"background-color: {color}; color: white;"
            "font-weight: bold; font-size: 14px;"
        )

    def _select_mode(self, mode: str) -> None:
        if self._current_state != ConnectionState.CONNECTED:
            return
        self.btn_pvp.setEnabled(False)
        self.btn_ai.setEnabled(False)
        self.send_command.emit(f"NEW: {mode}")

    def reset_buttons(self) -> None:
        if self._current_state == ConnectionState.CONNECTED:
            self.btn_pvp.setEnabled(True)
            self.btn_ai.setEnabled(True)
