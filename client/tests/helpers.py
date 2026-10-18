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
    command = "FLEET: 1,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
    assert send_command(stm32, command) == "OK: SETUP_P2"


def complete_pvp_setup(stm32) -> None:
    """
    Place both fleets and advance the FSM to STATE_IN_PROGRESS.
    """
    complete_player_1_setup(stm32)

    command = "FLEET: 2,A1,A5,B1,B4,C1,C3,D1,D3,E1,E2"
    assert send_command(stm32, command) == "OK: IN_PROGRESS"
