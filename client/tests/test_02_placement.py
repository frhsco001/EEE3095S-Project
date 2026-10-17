import pytest

from tests.helpers import complete_player_1_setup, complete_pvp_setup, send_command

# ---------------------------------------------------------------------------
# Placement tests
# ---------------------------------------------------------------------------


class TestPlacement:
    @pytest.fixture(autouse=True)
    def setup_fsm_to_placement(self, stm32):
        """
        Start every test in Player 1's PVP setup phase.

        The fixture also clears buffered serial data before and after each
        test so one failed test does not contaminate the next test.
        """
        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

        assert send_command(stm32, "CONNECT") == "OK"

        assert send_command(stm32, "NEW: PVP") == "OK: NEW_PVP"

        yield

        # Teardown is deliberately tolerant because a test may already have
        # disconnected or may leave the FSM in a different state.
        stm32.write(b"DISCONNECT\n")
        stm32.readline()

        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

    # -----------------------------------------------------------------------
    # Basic valid placement
    # -----------------------------------------------------------------------

    def test_valid_horizontal_placement(self, stm32):
        """A valid horizontal placement should be accepted."""
        assert send_command(stm32, "PLACE: 1,C,A1,E1") == "OK: PLACED"

    def test_valid_vertical_placement(self, stm32):
        """A valid vertical placement should be accepted."""
        assert send_command(stm32, "PLACE: 1,C,A1,A5") == "OK: PLACED"

    @pytest.mark.parametrize(
        "ship,start,end",
        [
            ("C", "A1", "A5"),  # Carrier, length 5
            ("B", "B1", "B4"),  # Battleship, length 4
            ("D", "C1", "C3"),  # Destroyer, length 3
            ("S", "D1", "D3"),  # Submarine, length 3
            ("P", "E1", "E2"),  # Patrol, length 2
        ],
    )
    def test_valid_length_for_each_ship(
        self,
        stm32,
        ship,
        start,
        end,
    ):
        """Each ship should accept its required length."""
        assert send_command(stm32, f"PLACE: 1,{ship},{start},{end}") == "OK: PLACED"

    # -----------------------------------------------------------------------
    # Board boundaries
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize(
        "command",
        [
            "PLACE: 1,C,J1,J5",  # Left or right board edge
            "PLACE: 1,C,A10,E10",  # Bottom board edge
            "PLACE: 1,P,J9,J10",  # Ends at J10 vertically
            "PLACE: 1,P,I10,J10",  # Ends at J10 horizontally
        ],
    )
    def test_valid_placement_on_board_edges(self, stm32, command):
        """Valid placements may touch any board boundary."""
        assert send_command(stm32, command) == "OK: PLACED"

    @pytest.mark.parametrize(
        "command",
        [
            "PLACE: 1,C,K1,K5",
            "PLACE: 1,C,A0,A4",
            "PLACE: 1,C,A7,A11",
            "PLACE: 1,P,K9,K10",
        ],
    )
    def test_out_of_bounds_rejection(self, stm32, command):
        """
        Coordinates outside A-J and 1-10 should be rejected.

        If malformed coordinates are classified as BADCMD by the parser,
        change the expected response to match the protocol specification.
        """
        assert send_command(stm32, command) == "NACK: BADCMD"

    # -----------------------------------------------------------------------
    # Reversed endpoints
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize(
        "command",
        [
            "PLACE: 1,C,A5,A1",
            "PLACE: 1,C,E1,A1",
            "PLACE: 1,B,D1,A1",
            "PLACE: 1,P,J10,I10",
        ],
    )
    def test_reversed_endpoint_placement(self, stm32, command):
        """Placement endpoints should be accepted in either order."""
        assert send_command(stm32, command) == "OK: PLACED"

    # -----------------------------------------------------------------------
    # Orientation and length checking
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize(
        "command",
        [
            "PLACE: 1,C,A1,B5",
            "PLACE: 1,B,C2,F5",
            "PLACE: 1,D,A1,C3",
            "PLACE: 1,S,H2,J4",
            "PLACE: 1,P,D4,E5",
        ],
    )
    def test_diagonal_rejection(self, stm32, command):
        """Diagonal placements must be rejected."""
        assert send_command(stm32, command) == "NACK: BADCOORDS"

    @pytest.mark.parametrize(
        "command",
        [
            "PLACE: 1,C,A1,A4",  # Carrier too short
            "PLACE: 1,C,A1,A6",  # Carrier too long
            "PLACE: 1,B,A1,A3",  # Battleship too short
            "PLACE: 1,B,A1,A5",  # Battleship too long
            "PLACE: 1,D,A1,A2",  # Destroyer too short
            "PLACE: 1,D,A1,A4",  # Destroyer too long
            "PLACE: 1,S,A1,A2",  # Submarine too short
            "PLACE: 1,S,A1,A4",  # Submarine too long
            "PLACE: 1,P,A1,A1",  # Patrol too short
            "PLACE: 1,P,A1,A3",  # Patrol too long
        ],
    )
    def test_wrong_ship_length_rejection(self, stm32, command):
        """Each ship must be placed using its exact defined length."""
        assert send_command(stm32, command) == "NACK: BADCOORDS"

    @pytest.mark.parametrize("ship", ["C", "B", "D", "S", "P"])
    def test_single_cell_placement_rejected(self, stm32, ship):
        """No ship may occupy only one cell."""
        assert send_command(stm32, f"PLACE: 1,{ship},A1,A1") == "NACK: BADCOORDS"

    # -----------------------------------------------------------------------
    # Duplicate ship checking
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize(
        "ship,first_start,first_end,second_start,second_end",
        [
            ("C", "A1", "A5", "B1", "B5"),
            ("B", "A1", "A4", "B1", "B4"),
            ("D", "A1", "A3", "B1", "B3"),
            ("S", "A1", "A3", "B1", "B3"),
            ("P", "A1", "A2", "B1", "B2"),
        ],
    )
    def test_duplicate_ship_rejection(
        self,
        stm32,
        ship,
        first_start,
        first_end,
        second_start,
        second_end,
    ):
        """A player may not place the same ship type twice."""
        first_response = send_command(
            stm32,
            f"PLACE: 1,{ship},{first_start},{first_end}",
        )
        assert first_response == "OK: PLACED"

        second_response = send_command(
            stm32,
            f"PLACE: 1,{ship},{second_start},{second_end}",
        )
        assert second_response == "NACK: PLACED"

    # -----------------------------------------------------------------------
    # Overlap checking
    # -----------------------------------------------------------------------

    def test_perpendicular_overlap_rejection(self, stm32):
        """A ship may not intersect an already placed ship."""
        assert send_command(stm32, "PLACE: 1,C,A1,A5") == "OK: PLACED"
        assert send_command(stm32, "PLACE: 1,B,A3,D3") == "NACK: OCCUPIED"

    def test_parallel_overlap_rejection(self, stm32):
        """A ship may not overlap another ship along the same axis."""
        assert send_command(stm32, "PLACE: 1,C,A1,E1") == "OK: PLACED"
        assert send_command(stm32, "PLACE: 1,B,C1,F1") == "NACK: OCCUPIED"

    def test_complete_overlap_rejection(self, stm32):
        """A shorter ship may not be placed entirely inside another ship."""
        assert send_command(stm32, "PLACE: 1,C,A1,A5") == "OK: PLACED"
        assert send_command(stm32, "PLACE: 1,P,A2,A3") == "NACK: OCCUPIED"

    def test_adjacent_ships_are_allowed(self, stm32):
        """
        Adjacent ships should be accepted if the game rules only prohibit
        occupied cells and do not require a gap between ships.
        """
        assert send_command(stm32, "PLACE: 1,C,A1,A5") == "OK: PLACED"
        assert send_command(stm32, "PLACE: 1,B,B1,B4") == "OK: PLACED"

    # -----------------------------------------------------------------------
    # Turn enforcement
    # -----------------------------------------------------------------------

    def test_wrong_player_turn(self, stm32):
        """Player 2 cannot place during Player 1's setup phase."""
        assert send_command(stm32, "PLACE: 2,C,A1,A5") == "NACK: NOTURN"

    def test_wrong_player_attempt_does_not_place_ship(self, stm32):
        """A rejected out-of-turn command must not modify Player 2's fleet."""
        assert send_command(stm32, "PLACE: 2,C,A1,A5") == "NACK: NOTURN"

        complete_player_1_setup(stm32)

        # The rejected command must not have marked Player 2's carrier as already placed
        assert send_command(stm32, "PLACE: 2,C,A1,A5") == "OK: PLACED"

    def test_player_one_cannot_place_during_player_two_setup(self, stm32):
        """After Player 1 finishes, only Player 2 may place ships."""
        complete_player_1_setup(stm32)

        assert send_command(stm32, "PLACE: 1,C,F1,F5") == "NACK: NOTURN"

    def test_player_two_cannot_place_before_player_one_finishes(self, stm32):
        """Partially completing Player 1 setup must not change the turn."""
        assert send_command(stm32, "PLACE: 1,C,A1,A5") == "OK: PLACED"

        assert send_command(stm32, "PLACE: 2,C,A1,A5") == "NACK: NOTURN"

    # -----------------------------------------------------------------------
    # State-integrity tests
    # -----------------------------------------------------------------------

    def test_failed_overlap_does_not_mark_ship_as_placed(self, stm32):
        """A failed overlap must not set the ship's is_placed flag."""
        assert send_command(stm32, "PLACE: 1,C,A1,A5") == "OK: PLACED"

        assert send_command(stm32, "PLACE: 1,B,A3,D3") == "NACK: OCCUPIED"

        # The battleship should still be available after the failed attempt.
        assert send_command(stm32, "PLACE: 1,B,B6,E6") == "OK: PLACED"

    def test_failed_overlap_does_not_partially_modify_board(self, stm32):
        """A rejected placement must not write any cells to the board."""
        assert send_command(stm32, "PLACE: 1,C,A1,A5") == "OK: PLACED"

        # Battleship would occupy A3, B3, C3, and D3.
        # It must fail before writing B3, C3, or D3.
        assert send_command(stm32, "PLACE: 1,B,A3,D3") == "NACK: OCCUPIED"

        # This destroyer uses B3, C3, and D3. It should succeed if the failed
        # battleship did not partially modify the board.
        assert send_command(stm32, "PLACE: 1,D,B3,D3") == "OK: PLACED"

    def test_bad_length_does_not_mark_ship_as_placed(self, stm32):
        """A ship remains available after an invalid-length attempt."""
        assert send_command(stm32, "PLACE: 1,B,A1,A3") == "NACK: BADCOORDS"

        assert send_command(stm32, "PLACE: 1,B,A1,A4") == "OK: PLACED"

    def test_diagonal_attempt_does_not_mark_ship_as_placed(self, stm32):
        """A ship remains available after a diagonal attempt."""
        assert send_command(stm32, "PLACE: 1,D,A1,C3") == "NACK: BADCOORDS"

        assert send_command(stm32, "PLACE: 1,D,A1,A3") == "OK: PLACED"

    def test_duplicate_attempt_does_not_damage_existing_board(self, stm32):
        """Rejecting a duplicate ship must not alter other board cells."""
        assert send_command(stm32, "PLACE: 1,B,A1,A4") == "OK: PLACED"

        assert send_command(stm32, "PLACE: 1,B,C5,F5") == "NACK: PLACED"

        # These cells should remain empty because the duplicate was rejected.
        assert send_command(stm32, "PLACE: 1,D,C5,E5") == "OK: PLACED"

    # -----------------------------------------------------------------------
    # Player-board independence
    # -----------------------------------------------------------------------

    def test_players_may_use_identical_coordinates(self, stm32):
        """Player 1 and Player 2 must have independent boards."""
        complete_player_1_setup(stm32)

        assert send_command(stm32, "PLACE: 2,C,A1,A5") == "OK: PLACED"

    def test_player_two_duplicate_check_is_independent(self, stm32):
        """
        Placing a ship for Player 1 must not mark the corresponding
        Player 2 ship as placed.
        """
        complete_player_1_setup(stm32)

        assert send_command(stm32, "PLACE: 2,C,F1,F5") == "OK: PLACED"
        assert send_command(stm32, "PLACE: 2,C,A1,A5") == "NACK: PLACED"

    # -----------------------------------------------------------------------
    # FSM progression
    # -----------------------------------------------------------------------

    def test_player_one_final_ship_advances_to_player_two(self, stm32):
        """Player 1's final ship should advance setup to Player 2."""
        for command in [
            "PLACE: 1,C,A1,A5",
            "PLACE: 1,B,B1,B4",
            "PLACE: 1,D,C1,C3",
            "PLACE: 1,S,D1,D3",
        ]:
            assert send_command(stm32, command) == "OK: PLACED"

        assert send_command(stm32, "PLACE: 1,P,E1,E2") == "OK: SETUP_P2"

    def test_player_two_final_ship_enters_in_progress(self, stm32):
        """Player 2's final ship should start the game."""
        complete_player_1_setup(stm32)

        for command in [
            "PLACE: 2,C,A1,A5",
            "PLACE: 2,B,B1,B4",
            "PLACE: 2,D,C1,C3",
            "PLACE: 2,S,D1,D3",
        ]:
            assert send_command(stm32, command) == "OK: PLACED"

        assert send_command(stm32, "PLACE: 2,P,E1,E2") == "OK: IN_PROGRESS"

    def test_full_setup_fsm_progression(self, stm32):
        """A complete PVP setup should enter STATE_IN_PROGRESS."""
        complete_pvp_setup(stm32)

        # A valid shooting command should now be processed by the
        # in-progress state rather than the setup state.
        response = send_command(stm32, "SHOOT: 1,J10")

        assert response in {
            "MISS: 2,J10",
            "HIT: 2,J10",
            "SUNK: 2,C",
            "SUNK: 2,B",
            "SUNK: 2,D",
            "SUNK: 2,S",
            "SUNK: 2,P",
            "WIN: 1",
        }

    def test_placement_rejected_after_setup_complete(self, stm32):
        """PLACE commands must be rejected after entering IN_PROGRESS."""
        complete_pvp_setup(stm32)

        assert (
            send_command(stm32, "PLACE: 1,C,F1,F5") == "NACK: OUT_OF_STATE,IN_PROGRESS"
        )

    def test_setup_does_not_advance_before_all_ships_are_placed(self, stm32):
        """Four valid ships are insufficient to complete setup."""
        for command in [
            "PLACE: 1,C,A1,A5",
            "PLACE: 1,B,B1,B4",
            "PLACE: 1,D,C1,C3",
            "PLACE: 1,S,D1,D3",
        ]:
            assert send_command(stm32, command) == "OK: PLACED"

        # Player 2 must still be rejected because Player 1 has not placed
        # the patrol boat.
        assert send_command(stm32, "PLACE: 2,C,A1,A5") == "NACK: NOTURN"

    # -----------------------------------------------------------------------
    # Out-of-state behaviour
    # -----------------------------------------------------------------------

    def test_place_when_no_game_is_active(self, stm32):
        """Placements should be rejected after disconnecting."""
        disconnect_response = send_command(stm32, "DISCONNECT")

        # Adjust this if the protocol uses a more specific OK response.
        assert disconnect_response == "OK"

        assert send_command(stm32, "PLACE: 1,C,A1,A5") == "NACK: NOGAME"

    def test_non_place_command_during_setup(self, stm32):
        """Unsupported commands should receive the setup-state NACK."""
        assert send_command(stm32, "SHOOT: 1,A1") == "NACK: OUT_OF_STATE,SETUP"

    # -----------------------------------------------------------------------
    # Invalid ship and command parsing
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize(
        "command",
        [
            "PLACE: 1,X,A1,A5",
            "PLACE: 1,Z,A1,A5",
        ],
    )
    def test_invalid_ship_type_rejected(self, stm32, command):
        """Unknown ship identifiers must be rejected."""
        assert send_command(stm32, command) == "NACK: BADCMD"

    @pytest.mark.parametrize(
        "command",
        [
            "PLACE:",
            "PLACE: 1",
            "PLACE: 1,C",
            "PLACE: 1,C,A1",
            "PLACE: X,C,A1,A5",
            "PLACE: 1,C,AA1,A5",
        ],
    )
    def test_malformed_place_command_rejected(self, stm32, command):
        """Malformed PLACE commands must be rejected without changing state."""
        assert send_command(stm32, command) == "NACK: BADCMD"
