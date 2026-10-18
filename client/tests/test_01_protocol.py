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
        return

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
    # FLEET Command Parsing
    # -----------------------------------------------------------------------

    def test_valid_fleet_parsing(self, stm32):
        """
        A correctly formatted FLEET command in the IDLE state should
        survive the parser and be rejected by the FSM with NOGAME.
        """
        cmd = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "NACK: NOGAME"

    @pytest.mark.parametrize(
        "command",
        [
            # Invalid player ID (must be 1 or 2)
            "FLEET: 3,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2",
            # Missing comma delimiter after player ID
            "FLEET: 1A1,A5,B1,B4,C1,C3,D1,D3,E1,E2",
            # Missing final coordinate
            "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,",
            # Invalid coordinates (Z9) rejected by bounds check
            "FLEET: 1,Z9,A5,B1,B4,C1,C3,D1,D3,E1,E2",
            # Missing colon in command header
            "FLEET 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2",
            # Missing comma delimiters between coordinate pairs
            "FLEET: 1,A1A5,B1B4,C1C3,D1D3,E1E2",
        ],
    )
    def test_malformed_fleet_commands(self, stm32, command):
        """Malformed FLEET commands must be caught by the parser as BADCMD."""
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
