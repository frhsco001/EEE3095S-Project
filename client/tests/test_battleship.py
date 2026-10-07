import pytest


class TestPlacement:
    
    @pytest.fixture(autouse=True)
    def setup_fsm_to_placement(self, stm32):
        """Automatically transitions STM32 to STATE_SETUP_P1 before every test."""
        stm32.write(b"CONNECT\n")
        stm32.readline() # Consume OK
        stm32.write(b"NEW: PVP\n")
        stm32.readline() # Consume OK: NEW_PVP
        
        yield
        
        stm32.write(b"DISCONNECT\n") 
        stm32.readline()


    def test_place_out_of_state(self, stm32):
        """Ensure placements are rejected if no game is active."""
        stm32.write(b"DISCONNECT\n")
        stm32.readline()  # Consume OK

        stm32.write(b"PLACE: 1,C,A1,A5\n")
        response = stm32.readline().decode("ascii").strip()
        assert response == "NACK: NOGAME"


    def test_valid_placement(self, stm32):
        """A strictly valid placement should be accepted."""
        stm32.write(b"PLACE: 1,C,A1,A5\n")  # Carrier, Length 5
        response = stm32.readline().decode("ascii").strip()
        assert response == "OK: PLACED"


    def test_wrong_player_turn(self, stm32):
        """Player 2 cannot place ships during Player 1's setup phase."""
        stm32.write(b"PLACE: 2,C,A1,A5\n")
        response = stm32.readline().decode("ascii").strip()
        assert response == "NACK: NOTURN"


    def test_diagonal_rejection(self, stm32):
        """The system must reject diagonal placements."""
        stm32.write(b"PLACE: 1,C,A1,B5\n")
        response = stm32.readline().decode("ascii").strip()
        assert response == "NACK: BADCOORDS"


    def test_bad_length_rejection(self, stm32):
        """The coordinates must exactly match the predefined ship length."""
        # Carrier requires length 5, but A1 to A3 is only length 3
        stm32.write(b"PLACE: 1,C,A1,A3\n")
        response = stm32.readline().decode("ascii").strip()
        assert response == "NACK: BADCOORDS"


    def test_duplicate_ship_rejection(self, stm32):
        """A player cannot place the same ship class twice."""
        stm32.write(b"PLACE: 1,B,C1,C4\n")
        stm32.readline()  # Consume OK: PLACED

        # Try to place the Battleship (B) again elsewhere
        stm32.write(b"PLACE: 1,B,D1,D4\n")
        response = stm32.readline().decode("ascii").strip()
        assert response == "NACK: PLACED"


    def test_overlap_rejection(self, stm32):
        """Ships cannot be placed on occupied cells."""
        # Place Carrier horizontally across row 1
        stm32.write(b"PLACE: 1,C,A1,A5\n")
        stm32.readline()

        # Place Battleship vertically, intersecting at A3
        stm32.write(b"PLACE: 1,B,A3,D3\n")
        response = stm32.readline().decode("ascii").strip()
        assert response == "NACK: OCCUPIED"


    def test_full_setup_fsm_progression(self, stm32):
        """Placing all 5 ships should automatically advance the FSM to the next phase."""

        # Player 1 Phase
        stm32.write(b"PLACE: 1,C,A1,A5\n")
        stm32.readline()  # Carrier (5)
        stm32.write(b"PLACE: 1,B,B1,B4\n")
        stm32.readline()  # Battleship (4)
        stm32.write(b"PLACE: 1,D,C1,C3\n")
        stm32.readline()  # Destroyer (3)
        stm32.write(b"PLACE: 1,S,D1,D3\n")
        stm32.readline()  # Submarine (3)

        # Final P1 Ship should trigger state transition
        stm32.write(b"PLACE: 1,P,E1,E2\n")  # Patrol Boat (2)
        response = stm32.readline().decode("ascii").strip()
        assert response == "OK: SETUP_P2"

        # Player 2 Phase
        stm32.write(b"PLACE: 2,C,A1,A5\n")
        stm32.readline()
        stm32.write(b"PLACE: 2,B,B1,B4\n")
        stm32.readline()
        stm32.write(b"PLACE: 2,D,C1,C3\n")
        stm32.readline()
        stm32.write(b"PLACE: 2,S,D1,D3\n")
        stm32.readline()

        # Final P2 Ship should trigger IN_PROGRESS
        stm32.write(b"PLACE: 2,P,E1,E2\n")
        response = stm32.readline().decode("ascii").strip()
        assert response == "OK: IN_PROGRESS"
