import time


def test_connect_command(stm32):
    """The server should respond to the baseline CONNECT command."""
    stm32.write(b"CONNECT\n")
    response = stm32.readline().decode("ascii").strip()
    assert response == "OK"


def test_malformed_command_rejection(stm32):
    """The parser should reject unknown commands before game logic."""
    stm32.write(b"GARBAGE_DATA\n")
    response = stm32.readline().decode("ascii").strip()
    assert response == "NACK: BADCMD"


def test_invalid_coordinates(stm32):
    """The parser should catch out-of-bounds coordinates (e.g., Z99)."""
    stm32.write(b"MOVE: 1,Z99\n")
    response = stm32.readline().decode("ascii").strip()
    assert response == "NACK: BADCMD"


def test_missing_comma_in_move(stm32):
    """The parser should reject commands missing required delimiters."""
    stm32.write(b"MOVE: 1B4\n")
    response = stm32.readline().decode("ascii").strip()
    assert response == "NACK: BADCMD"


def test_incomplete_frame_timeout_recovery(stm32):
    """The server must clear incomplete frames after a timeout[cite: 3]."""
    # Send a partial command without a newline
    stm32.write(b"CON")

    # Wait for the STM32's 500ms HAL_GetTick() timeout to clear the buffer
    time.sleep(0.6)

    # Send a fresh, complete command; it should work if the buffer cleared properly
    stm32.write(b"CONNECT\n")
    response = stm32.readline().decode("ascii").strip()

    # If the buffer didn't clear, the STM32 would see "CONCONNECT\n" and fail
    assert response == "OK"
