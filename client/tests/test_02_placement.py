import pytest

from tests.helpers import complete_player_1_setup, complete_pvp_setup, send_command

# ---------------------------------------------------------------------------
# Fleet Placement Tests
# ---------------------------------------------------------------------------


class TestPlacement:
    @pytest.fixture(autouse=True)
    def setup_fsm_to_placement(self, stm32):
        """Start every test in Player 1's PVP setup phase."""
        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

        assert send_command(stm32, "CONNECT") == "OK"
        assert send_command(stm32, "NEW: PVP") == "OK: NEW_PVP"

        yield

        stm32.write(b"DISCONNECT\n")
        stm32.readline()

        if hasattr(stm32, "reset_input_buffer"):
            stm32.reset_input_buffer()

    # -----------------------------------------------------------------------
    # Basic Valid Placements
    # -----------------------------------------------------------------------

    def test_valid_fleet_placement(self, stm32):
        """A completely valid fleet placement should advance the FSM."""
        # Carrier: A1-A5, Battleship: B1-B4, Destroyer: C1-C3
        # Submarine: D1-D3, Patrol: E1-E2
        cmd = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "OK: SETUP_P2"

    def test_reversed_endpoint_placement(self, stm32):
        """Placement endpoints should be accepted in reversed order."""
        # Carrier is A5->A1, Patrol is E2->E1
        cmd = "FLEET: 1,A5,A1,B1,B4,C1,C3,D1,D3,E2,E1"
        assert send_command(stm32, cmd) == "OK: SETUP_P2"

    def test_valid_placement_on_board_edges(self, stm32):
        """Valid fleets may touch any board boundary."""
        # Using J1-J5, I1-I4, H1-H3, G1-G3, F9-F10
        cmd = "FLEET: 1,J1,J5,I1,I4,H1,H3,G1,G3,F9,F10"
        assert send_command(stm32, cmd) == "OK: SETUP_P2"

    # -----------------------------------------------------------------------
    # Board Boundaries (Parser Level)
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize(
        "fleet_cmd",
        [
            "FLEET: 1,K1,K5,B1,B4,C1,C3,D1,D3,E1,E2",  # K is out of bounds
            "FLEET: 1,A1,A5,B0,B3,C1,C3,D1,D3,E1,E2",  # Row 0 is out of bounds
            "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E11,E12",  # Row 11 is out of bounds
        ],
    )
    def test_out_of_bounds_rejection(self, stm32, fleet_cmd):
        """
        Coordinates outside A-J and 1-10 are rejected by the parser logic
        before hitting the game logic.
        """
        assert send_command(stm32, fleet_cmd) == "NACK: BADCMD"

    # -----------------------------------------------------------------------
    # Geometry and Length Checking (Logic Level)
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize(
        "fleet_cmd",
        [
            # Invalid Lengths
            "FLEET: 1,A1,A4,B1,B4,C1,C3,D1,D3,E1,E2",  # Carrier too short (length 4)
            "FLEET: 1,A1,A5,B1,B5,C1,C3,D1,D3,E1,E2",  # Battleship too long (length 5)
            "FLEET: 1,A1,A5,B1,B4,C1,C2,D1,D3,E1,E2",  # Destroyer too short (length 2)
            "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E1",  # Patrol is a single cell
            # Diagonals
            "FLEET: 1,A1,B5,B1,B4,C1,C3,D1,D3,E1,E2",  # Carrier is diagonal
            "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,F3,E1,E2",  # Submarine is diagonal
        ],
    )
    def test_geometry_rejection(self, stm32, fleet_cmd):
        """Incorrectly sized or diagonal ships must be rejected."""
        response = send_command(stm32, fleet_cmd)
        assert response.startswith("NACK: BADCOORDS")

    # -----------------------------------------------------------------------
    # Overlap Checking
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize(
        "fleet_cmd",
        [
            # Battleship (A3-D3) crosses Carrier (A1-A5) perpendicularly
            "FLEET: 1,A1,A5,A3,D3,C1,C3,D1,D3,E1,E2",
            # Patrol (C1-C2) overlaps Destroyer (C1-C3) along same axis
            "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,C1,C2",
            # Submarine is placed completely inside the Carrier
            "FLEET: 1,A1,A5,B1,B4,C1,C3,A2,A4,E1,E2",
        ],
    )
    def test_overlap_rejection(self, stm32, fleet_cmd):
        """A fleet containing internal intersections must be rejected."""
        response = send_command(stm32, fleet_cmd)
        assert response.startswith("NACK: OCCUPIED")

    # -----------------------------------------------------------------------
    # Transactional State Integrity
    # -----------------------------------------------------------------------

    def test_failed_atomic_placement_leaves_board_empty(self, stm32):
        """
        If a fleet transaction fails (e.g. ship 4 overlaps ship 1),
        the board must remain completely empty and accept a corrected payload.
        """
        # Bad fleet: Submarine overlaps Carrier
        bad_fleet = "FLEET: 1,A1,A5,B1,B4,C1,C3,A2,A4,E1,E2"
        assert send_command(stm32, bad_fleet).startswith("NACK: OCCUPIED")

        # Corrected fleet should succeed because the board was untouched
        good_fleet = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, good_fleet) == "OK: SETUP_P2"

    # -----------------------------------------------------------------------
    # Turn Enforcement
    # -----------------------------------------------------------------------

    def test_wrong_player_turn(self, stm32):
        """Player 2 cannot place during Player 1's setup phase."""
        cmd = "FLEET: 2,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "NACK: NOTURN"

    def test_player_one_cannot_replace_after_completing_setup(self, stm32):
        """Once Player 1 finishes, they cannot send another FLEET command."""
        complete_player_1_setup(stm32)
        cmd = "FLEET: 1,F1,F5,G1,G4,H1,H3,I1,I3,J1,J2"
        assert send_command(stm32, cmd) == "NACK: NOTURN"

    # -----------------------------------------------------------------------
    # FSM Progression
    # -----------------------------------------------------------------------

    def test_full_setup_enters_in_progress(self, stm32):
        """A complete PVP setup should transition the FSM into shooting mode."""
        complete_pvp_setup(stm32)

        # A valid shooting command should now be processed
        response = send_command(stm32, "SHOOT: 1,J10")
        assert response.startswith("MISS:") or response.startswith("HIT:")

    def test_fleet_command_rejected_during_gameplay(self, stm32):
        """FLEET commands must be rejected after entering IN_PROGRESS."""
        complete_pvp_setup(stm32)
        cmd = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
        assert send_command(stm32, cmd) == "NACK: OUT_OF_STATE,IN_PROGRESS"

    # -----------------------------------------------------------------------
    # Malformed Command Parsing
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize(
        "command",
        [
            "FLEET:",
            "FLEET: 1",
            "FLEET: 1,A1,A5",  # Missing ships
            "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3",  # Missing Patrol ship
            "FLEET: 3,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2",  # Invalid player ID
            "FLEET: 1,A1,A5;B1,B4;C1,C3;D1,D3;E1,E2",  # Wrong delimiters
        ],
    )
    def test_malformed_fleet_command_rejected(self, stm32, command):
        """Malformed commands must be caught by the parser and rejected."""
        assert send_command(stm32, command) == "NACK: BADCMD"
