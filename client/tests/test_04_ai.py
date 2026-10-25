import re

import pytest

from tests.helpers import send_command

# Regex patterns to validate the STM32's formatted responses
CELL_RESP_PATTERN = re.compile(r"^(MISS|HIT): [12],[A-J](10|[1-9])$")
SHIP_RESP_PATTERN = re.compile(
    r"^(SUNK|WIN): [12],[CBDS P],[A-J](10|[1-9]),[A-J](10|[1-9])$"
)


class TestAIMode:
    @pytest.fixture(autouse=True)
    def setup_ai_mode(self, stm32):
        """Start every test in Player 1's AI setup phase."""
        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

        assert send_command(stm32, "CONNECT") == "OK"
        assert send_command(stm32, "NEW: AI") == "OK: NEW_AI"

        yield

        stm32.write(b"DISCONNECT\n")
        stm32.readline()

        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

    # -----------------------------------------------------------------------
    # FSM Progression
    # -----------------------------------------------------------------------

    def test_ai_setup_skips_player_2(self, stm32):
        """
        In AI mode, Player 1 placing their fleet should immediately advance
        the FSM to IN_PROGRESS, completely skipping SETUP_P2.
        """
        cmd = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "OK: IN_PROGRESS"

    def test_ai_rejects_player_2_placement(self, stm32):
        """Player 2 is the AI; manual placements for P2 must be rejected."""
        cmd = "FLEET: 2,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "NACK: NOTURN"

    # -----------------------------------------------------------------------
    # Combat & Retaliation
    # -----------------------------------------------------------------------

    def test_ai_counter_attack(self, stm32):
        """
        A valid shot by Player 1 must yield two responses: the result of
        Player 1's shot, followed immediately by the AI's retaliation.
        """
        # Complete setup
        cmd = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "OK: IN_PROGRESS"

        # Fire a valid shot (manually writing so we can read two lines back)
        stm32.write(b"SHOOT: 1,A1\n")

        # Read Player 1's shot result (targeting Player 2's board)
        p1_result = stm32.readline().decode("ascii").strip()

        # Read AI's retaliation result (targeting Player 1's board)
        ai_result = stm32.readline().decode("ascii").strip()

        # Validate Player 1's result formatting
        is_p1_cell = bool(CELL_RESP_PATTERN.match(p1_result))
        is_p1_ship = bool(SHIP_RESP_PATTERN.match(p1_result))
        assert is_p1_cell or is_p1_ship, f"Malformed P1 response: {p1_result}"
        assert " 2," in p1_result, "P1's shot should target Player 2"

        # Validate AI's retaliation formatting
        is_ai_cell = bool(CELL_RESP_PATTERN.match(ai_result))
        is_ai_ship = bool(SHIP_RESP_PATTERN.match(ai_result))
        assert is_ai_cell or is_ai_ship, f"Malformed AI response: {ai_result}"
        assert " 1," in ai_result, "AI's shot should target Player 1"

    def test_ai_no_retaliation_on_invalid_shot(self, stm32):
        """
        If Player 1 sends an invalid shot, the STM32 must NACK and wait.
        The AI must not fire out of turn.
        """
        cmd = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "OK: IN_PROGRESS"

        # Send an out-of-bounds shot
        stm32.write(b"SHOOT: 1,K1\n")

        # We expect a single NACK.
        response = stm32.readline().decode("ascii").strip()
        assert response == "NACK: BADCMD"

        # Attempt to read a second line with a short timeout.
        # The AI should not have fired.
        timeout_resp = stm32.readline().decode("ascii").strip()
        assert timeout_resp == "", "AI retaliated out of turn after a NACK"

    def test_ai_does_not_fire_on_repeat_shot(self, stm32):
        """
        If Player 1 shoots the same cell twice, the STM32 returns NACK: REPEAT.
        The AI must not consume this turn to fire.
        """
        cmd = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "OK: IN_PROGRESS"

        # First shot (Valid)
        stm32.write(b"SHOOT: 1,A1\n")
        stm32.readline()  # P1 result
        stm32.readline()  # AI result

        # Second shot (Repeat)
        stm32.write(b"SHOOT: 1,A1\n")
        response = stm32.readline().decode("ascii").strip()
        assert response == "NACK: REPEAT"

        # Ensure no AI retaliation follows
        timeout_resp = stm32.readline().decode("ascii").strip()
        assert timeout_resp == "", "AI retaliated on a REPEAT NACK"

    def test_ai_generates_valid_fleet(self, stm32):
        """
        Sweeping the entire 10x10 board must yield exactly 17 hits.
        This proves the C code placed 5 non-overlapping ships of correct lengths.
        """
        send_command(stm32, "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2")

        hit_count = 0
        game_won = False

        # Fire at every single cell on the board
        for r in range(10):
            for c in range(10):
                if game_won:
                    break

                col_char = chr(65 + c)
                row_str = str(r + 1)

                stm32.write(f"SHOOT: 1,{col_char}{row_str}\n".encode("ascii"))

                # Player 1's result
                p1_resp = stm32.readline().decode("ascii").strip()

                if p1_resp.startswith(("HIT:", "SUNK:")):
                    hit_count += 1
                elif p1_resp.startswith("WIN:"):
                    hit_count += 1
                    game_won = True

                # Consume the AI's retaliation response to clear the buffer
                if not game_won:
                    ai_resp = stm32.readline().decode("ascii").strip()

                    # The AI might win during this sweep if it gets lucky
                    if ai_resp.startswith("WIN:"):
                        pytest.skip("AI won the game before sweep completed.")

        assert hit_count == 17, f"Expected 17 hits on AI ships, got {hit_count}"
