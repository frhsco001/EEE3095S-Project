import time

import pytest
import serial


@pytest.fixture(scope="session")
def stm32():
    ser = serial.Serial("COM4", 115200, timeout=1)
    time.sleep(2)

    yield ser

    ser.close()
