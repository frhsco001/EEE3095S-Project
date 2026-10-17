def send_command(stm32, command: str) -> str:
    """
    Send one newline-terminated command and return one decoded response.

    The STM32 serial fixture should have a finite read timeout so a firmware
    failure does not block the test suite indefinitely.
    """
    stm32.write((command + "\n").encode("ascii"))
    return stm32.readline().decode("ascii").strip()


def complete_player_1_setup(stm32) -> None:
    """
    Place all Player 1 ships and advance the FSM to Player 2 setup.
    """
    placements = [
        "PLACE: 1,C,A1,A5",  # Carrier, length 5
        "PLACE: 1,B,B1,B4",  # Battleship, length 4
        "PLACE: 1,D,C1,C3",  # Destroyer, length 3
        "PLACE: 1,S,D1,D3",  # Submarine, length 3
    ]

    for command in placements:
        assert send_command(stm32, command) == "OK: PLACED"

    assert send_command(stm32, "PLACE: 1,P,E1,E2") == "OK: SETUP_P2"


def complete_pvp_setup(stm32) -> None:
    """
    Place both fleets and advance the FSM to STATE_IN_PROGRESS.
    """
    complete_player_1_setup(stm32)

    placements = [
        "PLACE: 2,C,A1,A5",
        "PLACE: 2,B,B1,B4",
        "PLACE: 2,D,C1,C3",
        "PLACE: 2,S,D1,D3",
    ]

    for command in placements:
        assert send_command(stm32, command) == "OK: PLACED"

    assert send_command(stm32, "PLACE: 2,P,E1,E2") == "OK: IN_PROGRESS"
