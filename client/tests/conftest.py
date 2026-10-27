import os
import time

import pytest
import serial
import serial.tools.list_ports


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--port",
        action="store",
        default=None,
        help="Serial port for the STM32 board (e.g. COM4 or /dev/ttyACM0)",
    )


def detect_stm32_port(cli_port: str | None = None) -> str:
    """Resolves target serial port via CLI flag, env var, auto-discovery, or fallback."""
    if cli_port:
        return cli_port

    env_port = os.environ.get("STM32_PORT")
    if env_port:
        return env_port

    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = f"{p.description} {p.manufacturer}".lower()
        if any(
            keyword in desc
            for keyword in (
                "stlink",
                "stm",
                "vcp",
                "usb-serial",
                "ch340",
                "cp210",
                "ftdi",
            )
        ):
            return p.device

    if len(ports) == 1:
        return ports[0].device

    return "COM4"


@pytest.fixture(scope="session")
def stm32(request: pytest.FixtureRequest):
    port = detect_stm32_port(request.config.getoption("--port"))
    try:
        ser = serial.Serial(port, 115200, timeout=1)
    except serial.SerialException as exc:
        available = [
            f"{p.device} ({p.description})" for p in serial.tools.list_ports.comports()
        ]
        raise pytest.UsageError(
            f"Failed to open STM32 serial port '{port}': {exc}\n"
            f"Available ports: {available or 'None'}\n"
            f"Specify a port with --port <PORT> or set the STM32_PORT environment variable."
        ) from exc

    time.sleep(2)

    yield ser

    ser.close()
