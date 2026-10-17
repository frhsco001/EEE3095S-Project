import time

import pytest

from tests.helpers import send_command


class TestProtocol:
    @pytest.fixture(autouse=True)
    def reset_buffers(self, stm32):
        """Ensure the serial buffer is clean before every test."""
        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

        # Put the STM32 into a known idle state
        send_command(stm32, "DISCONNECT")
        yield

    # -----------------------------------------------------------------------
    # Baseline Session Commands
    # -----------------------------------------------------------------------

    def test_connect_and_disconnect(self, stm32):
        """The server should respond to baseline connection commands."""
        assert send_command(stm32, "CONNECT") == "OK"
        assert send_command(stm32, "DISCONNECT") == "OK"

    def test_new_pvp_command(self, stm32):
        """The parser should recognize PVP game initialization."""
        assert send_command(stm32, "NEW: PVP") == "OK: NEW_PVP"

    def test_new_ai_command(self, stm32):
        """The parser should recognize AI game initialization."""
        assert send_command(stm32, "NEW: AI") == "OK: NEW_AI"

    # -----------------------------------------------------------------------
    # Unknown & Deprecated Commands
    # -----------------------------------------------------------------------

    def test_malformed_command_rejection(self, stm32):
        """The parser should reject pure garbage data."""
        assert send_command(stm32, "GARBAGE_DATA") == "NACK: BADCMD"

    # -----------------------------------------------------------------------
    # SHOOT Command Parsing
    # -----------------------------------------------------------------------

    def test_valid_shoot_parsing(self, stm32):
        """
        A correctly formatted SHOOT command in the IDLE state should
        survive the parser and be rejected by the FSM with NOGAME.
        """
        assert send_command(stm32, "SHOOT: 1,A1") == "NACK: NOGAME"
        assert send_command(stm32, "SHOOT: 2,J10") == "NACK: NOGAME"

    @pytest.mark.parametrize(
        "command",
        [
            "SHOOT: 1,Z99",  # Invalid coordinates
            "SHOOT: 3,A1",  # Invalid player ID (must be 1 or 2)
            "SHOOT: 1A1",  # Missing comma
            "SHOOT: 1, A1",  # Illegal space
            "SHOOT: 1,1",  # Missing letter
            "SHOOT: 1,A",  # Missing number
            "SHOOT:",  # Truncated
            "SHOOT:1,A1",  # Missing space after colon
        ],
    )
    def test_malformed_shoot_commands(self, stm32, command):
        """Malformed SHOOT commands must be caught by the parser as BADCMD."""
        assert send_command(stm32, command) == "NACK: BADCMD"

    # -----------------------------------------------------------------------
    # PLACE Command Parsing
    # -----------------------------------------------------------------------

    def test_valid_place_parsing(self, stm32):
        """
        A correctly formatted PLACE command in the IDLE state should
        survive the parser and be rejected by the FSM with NOGAME.
        """
        assert send_command(stm32, "PLACE: 1,C,A1,A5") == "NACK: NOGAME"

    @pytest.mark.parametrize(
        "command",
        [
            "PLACE: 1,X,A1,A5",  # Unknown ship type 'X'
            "PLACE: 3,C,A1,A5",  # Invalid player ID
            "PLACE: 1,C,A1A5",  # Missing comma delimiter
            "PLACE: 1,C,A1,",  # Missing second coordinate
            "PLACE: 1,C,Z9,A5",  # Invalid coordinates
            "PLACE 1,C,A1,A5",  # Missing colon
        ],
    )
    def test_malformed_place_commands(self, stm32, command):
        """Malformed PLACE commands must be caught by the parser as BADCMD."""
        assert send_command(stm32, command) == "NACK: BADCMD"

    # -----------------------------------------------------------------------
    # Framing, Timeouts, and Edge Cases
    # -----------------------------------------------------------------------

    def test_incomplete_frame_timeout_recovery(self, stm32):
        """The server must clear incomplete frames after a 500ms timeout."""
        # Send a partial command using raw write (no newline)
        stm32.write(b"CON")

        # Wait for the STM32's HAL_GetTick() timeout to clear the buffer
        time.sleep(0.6)

        # Send a fresh, complete command. If the buffer didn't clear,
        # the MCU would see "CONCONNECT" and return BADCMD.
        assert send_command(stm32, "CONNECT") == "OK"

    def test_buffer_overflow_protection(self, stm32):
        """The parser should not crash when sent excessively long strings."""
        # Send a string much larger than the typical 64-byte RX buffer
        stm32.write(b"GARBAGE_" * 20 + b"\n")

        # We don't strictly care if it returns BADCMD or silently clears it,
        # what matters is that the system doesn't HardFault and can recover.
        time.sleep(0.1)
        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

        assert send_command(stm32, "CONNECT") == "OK"
