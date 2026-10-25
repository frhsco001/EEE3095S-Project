import pytest

from tests.helpers import complete_pvp_setup, send_command


class TestShooting:
    @pytest.fixture(autouse=True)
    def setup_fsm_to_in_progress(self, stm32):
        """
        Fast-forwards the STM32 to the STATE_IN_PROGRESS phase before each test.
        Player 1 is the active turn.
        """
        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

        assert send_command(stm32, "CONNECT") == "OK"
        assert send_command(stm32, "NEW: PVP") == "OK: NEW_PVP"

        complete_pvp_setup(stm32)

        yield

        # Teardown
        stm32.write(b"DISCONNECT\n")
        stm32.readline()
        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

    # -----------------------------------------------------------------------
    # Basic Hits and Misses
    # -----------------------------------------------------------------------

    def test_valid_miss(self, stm32):
        """Shooting an empty cell returns a MISS with the target player and coords."""
        assert send_command(stm32, "SHOOT: 1,J10") == "MISS: 2,J10"

    def test_valid_hit(self, stm32):
        """Shooting an occupied cell returns a HIT with the target player and coords."""
        assert send_command(stm32, "SHOOT: 1,A1") == "HIT: 2,A1"

    # -----------------------------------------------------------------------
    # Turn Enforcement
    # -----------------------------------------------------------------------

    def test_player_two_cannot_shoot_first(self, stm32):
        """Player 2 must be rejected if they try to shoot on Player 1's turn."""
        assert send_command(stm32, "SHOOT: 2,A1") == "NACK: NOTURN"

    def test_turn_swaps_after_miss(self, stm32):
        """A successful MISS must hand the turn over to the other player."""
        assert send_command(stm32, "SHOOT: 1,J10") == "MISS: 2,J10"

        # Player 1 should now be locked out
        assert send_command(stm32, "SHOOT: 1,J9") == "NACK: NOTURN"

        # Player 2 should now be able to shoot
        assert send_command(stm32, "SHOOT: 2,A1") == "HIT: 1,A1"

    def test_turn_swaps_after_hit(self, stm32):
        """A successful HIT must hand the turn over to the other player."""
        assert send_command(stm32, "SHOOT: 1,A1") == "HIT: 2,A1"

        # Player 1 should now be locked out
        assert send_command(stm32, "SHOOT: 1,A2") == "NACK: NOTURN"

        # Player 2 is clear to shoot
        assert send_command(stm32, "SHOOT: 2,A1") == "HIT: 1,A1"

    # -----------------------------------------------------------------------
    # Repeat Shots & Invalid Coordinates
    # -----------------------------------------------------------------------

    def test_repeat_shot_rejected_and_retains_turn(self, stm32):
        """
        Shooting a cell that was already fired upon must return REPEAT
        and not consume the turn.
        """
        assert send_command(stm32, "SHOOT: 1,J10") == "MISS: 2,J10"
        assert send_command(stm32, "SHOOT: 2,J10") == "MISS: 1,J10"

        # Back to Player 1. Try to shoot the exact same cell.
        assert send_command(stm32, "SHOOT: 1,J10") == "NACK: REPEAT"

        # The turn should NOT have swapped to Player 2. It is still P1's turn.
        assert send_command(stm32, "SHOOT: 2,J9") == "NACK: NOTURN"

        # P1 can now make a valid shot
        assert send_command(stm32, "SHOOT: 1,J9") == "MISS: 2,J9"

    @pytest.mark.parametrize(
        "command",
        [
            "SHOOT: 1,K1",  # Column out of bounds
            "SHOOT: 1,A11",  # Row out of bounds
            "SHOOT: 1,A0",  # Row zero
            "SHOOT: 3,A1",  # Invalid player ID
            "SHOOT: 1,A",  # Missing row
            "SHOOT: 1",  # Missing coords
        ],
    )
    def test_malformed_shots_rejected_by_parser(self, stm32, command):
        """Malformed coordinates should be intercepted by Proto_ParseFrame as BADCMD."""
        assert send_command(stm32, command) == "NACK: BADCMD"

    # -----------------------------------------------------------------------
    # Sinking Mechanics
    # -----------------------------------------------------------------------

    def test_sinking_a_ship(self, stm32):
        """
        Hitting the final cell of a ship should return SUNK
        with the correct ship character.
        """
        # P2 Patrol boat is at E1 and E2.

        # Hit 1/2
        assert send_command(stm32, "SHOOT: 1,E1") == "HIT: 2,E1"
        assert send_command(stm32, "SHOOT: 2,J10") == "MISS: 1,J10"

        # Hit 2/2 (Fatal)
        assert send_command(stm32, "SHOOT: 1,E2") == "SUNK: 2,P,E1,E2"

        # Verify turn still swaps after a sink
        assert send_command(stm32, "SHOOT: 1,E3") == "NACK: NOTURN"
        assert send_command(stm32, "SHOOT: 2,J9") == "MISS: 1,J9"

    def test_sinking_large_ship_bounds(self, stm32):
        """
        Sinking a 5-cell Carrier should accurately report its start and end coordinates,
        proving the FindShipCoords C-function evaluates larger bounds correctly.
        """
        # P2 Carrier is at A1 through A5.
        for i in range(1, 5):
            assert send_command(stm32, f"SHOOT: 1,A{i}") == f"HIT: 2,A{i}"
            assert send_command(stm32, f"SHOOT: 2,J{i}") == f"MISS: 1,J{i}"

        # Hit 5/5 (Fatal)
        assert send_command(stm32, "SHOOT: 1,A5") == "SUNK: 2,C,A1,A5"

    def test_win_condition_returns_coordinates(self, stm32):
        """
        Sinking the final ship of the fleet should return WIN, the winner's ID,
        the final ship's character, and its bounding coordinates.
        """
        # To win, P1 must sink the Carrier, Battleship, Destroyer, and Submarine first.
        fleet = [
            ("C", ["A1", "A2", "A3", "A4", "A5"]),
            ("B", ["B1", "B2", "B3", "B4"]),
            ("D", ["C1", "C2", "C3"]),
            ("S", ["D1", "D2", "D3"]),
        ]

        # Generator providing unique empty coordinates for Player 2 to waste turns on
        # (Since P1's ships are in columns A-E, columns I and J are 100% water)
        p2_dummy_shots = (f"{col}{row}" for col in ["J", "I"] for row in range(1, 11))

        for ship_char, coords in fleet:
            for i, coord in enumerate(coords):
                response = send_command(stm32, f"SHOOT: 1,{coord}")

                # Check for HIT or SUNK depending on if it's the last cell of the ship
                if i == len(coords) - 1:
                    assert response == f"SUNK: 2,{ship_char},{coords[0]},{coords[-1]}"
                else:
                    assert response == f"HIT: 2,{coord}"

                # P2 wastes turn into unique empty water so P1 can shoot again
                send_command(stm32, f"SHOOT: 2,{next(p2_dummy_shots)}")

        # Now only the Patrol boat (E1, E2) remains.
        assert send_command(stm32, "SHOOT: 1,E1") == "HIT: 2,E1"
        send_command(stm32, f"SHOOT: 2,{next(p2_dummy_shots)}")

        # The final shot should trigger the WIN state, containing the Patrol coordinates
        assert send_command(stm32, "SHOOT: 1,E2") == "WIN: 1,P,E1,E2"

        # Verify the STM32 transitioned to STATE_GAME_OVER and rejects further gameplay
        assert send_command(stm32, "SHOOT: 2,A1") == "NACK: OUT_OF_STATE,GAME_OVER"

    # -----------------------------------------------------------------------
    # State Integrity
    # -----------------------------------------------------------------------

    def test_place_command_rejected_during_gameplay(self, stm32):
        """
        Attempting to place a ship while the game is running must trigger
        an OUT_OF_STATE NACK.
        """
        cmd = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "NACK: OUT_OF_STATE,IN_PROGRESS"

        # Verify it didn't consume the turn
        assert send_command(stm32, "SHOOT: 1,A1") == "HIT: 2,A1"

    def test_boards_are_independent(self, stm32):
        """A hit on Player 2's board must not affect Player 1's board."""
        # P1 hits P2's Carrier at A1
        assert send_command(stm32, "SHOOT: 1,A1") == "HIT: 2,A1"

        # P2 shooting at A1 on P1's board should not return REPEAT,
        # it should be a fresh HIT
        assert send_command(stm32, "SHOOT: 2,A1") == "HIT: 1,A1"
