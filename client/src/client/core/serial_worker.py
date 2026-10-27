import logging
import queue
import time
from enum import StrEnum

import serial
import serial.tools.list_ports
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


class ConnectionState(StrEnum):
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class SerialWorker(QThread):
    """Manages non-blocking serial communication with the STM32."""

    message_received = pyqtSignal(str)
    connection_state = pyqtSignal(str, str)

    def __init__(
        self,
        port: str | None = None,
        baudrate: int = 115200,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate

        self._running = False
        self._tx_queue: queue.Queue[str] = queue.Queue()
        self._serial: serial.Serial | None = None

    @pyqtSlot(str)
    def send_command(self, command: str) -> None:
        """Thread-safe slot to enqueue an outbound command frame."""
        self._tx_queue.put(command)

    def stop(self) -> None:
        """Signals the worker loop to terminate and closes the serial port."""
        self._running = False
        self.wait(1000)

    def run(self) -> None:
        """Main thread loop handling serial polling and outbound writing."""
        self._running = True

        while self._running:
            # Ensure serial port is connected
            if self._serial is None or not self._serial.is_open:  # noqa: SIM102
                if not self._init_connection():
                    # Wait briefly before attempting re-discovery/connection
                    time.sleep(1.0)
                    continue

            try:
                self._drain_tx_queue()

                # Read incoming lines (STM32 transmits \n terminated strings)
                if self._serial and self._serial.in_waiting > 0:
                    raw_line = self._serial.readline()
                    if raw_line:
                        line = (
                            raw_line.decode("utf-8", errors="replace")
                            .strip("\r\n")
                            .strip()
                        )
                        if line:
                            logger.debug("RX <-- %s", line)
                            self.message_received.emit(line)

            except serial.SerialException as exc:
                logger.error("Serial hardware error: %s", exc)
                self._close_connection()
                self.connection_state.emit(ConnectionState.ERROR, str(exc))
            except Exception as exc:
                logger.exception("Unexpected error in serial thread: %s", exc)

            # Yield thread slice briefly to prevent 100% CPU core saturation
            time.sleep(0.005)

        self._close_connection()
        self.connection_state.emit(ConnectionState.DISCONNECTED, "Disconnected")

    def _init_connection(self) -> bool:
        """Attempts to establish connection to specified or auto-detected port."""
        self.connection_state.emit(
            ConnectionState.CONNECTING, "Searching for device..."
        )
        target_port = self.port or self._detect_port()

        if not target_port:
            logger.debug("No active serial port target detected.")
            self.connection_state.emit(ConnectionState.ERROR, "No device detected")
            return False

        try:
            self.connection_state.emit(
                ConnectionState.CONNECTING, f"Opening {target_port}..."
            )
            logger.info("Connecting to %s at %d baud...", target_port, self.baudrate)
            self._serial = serial.Serial(
                port=target_port,
                baudrate=self.baudrate,
                timeout=0.05,
                write_timeout=0.5,
            )
            self.connection_state.emit(
                ConnectionState.CONNECTED, f"Ready on {target_port}"
            )
            logger.info("Serial connection established on %s", target_port)
            return True
        except serial.SerialException as exc:
            logger.warning("Failed to open %s: %s", target_port, exc)
            self._close_connection()
            self.connection_state.emit(ConnectionState.ERROR, str(exc))
            return False

    def _detect_port(self) -> str | None:
        """Scans available COM/tty ports for ST-LINK or standard USB-UART bridges."""
        ports = serial.tools.list_ports.comports()
        for p in ports:
            desc = f"{p.description} {p.manufacturer}".lower()
            if "stlink" in desc or "stm" in desc or "vcp" in desc:
                logger.info(
                    "Discovered STM32 device on port: %s (%s)", p.device, p.description
                )
                return p.device

        # If only one serial port is active on the machine, fall back to it
        if len(ports) == 1:
            return ports[0].device

        return None

    def _drain_tx_queue(self) -> None:
        """Sends all pending commands over UART with newline termination."""
        while not self._tx_queue.empty() and self._serial and self._serial.is_open:
            cmd = self._tx_queue.get_nowait().strip()
            # Clean string and append mandatory protocol newline delimiter
            frame = f"{cmd}\n".encode("utf-8")

            logger.debug("TX --> %s", cmd)
            self._serial.write(frame)
            self._serial.flush()
            self._tx_queue.task_done()

    def _close_connection(self) -> None:
        """Closes the active serial handle and emits a disconnection signal."""
        if self._serial:
            try:
                if self._serial.is_open:
                    self._serial.close()
            except Exception as exc:
                logger.error("Error closing serial handle: %s", exc)
            finally:
                self._serial = None
