from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ShipSpec:
    name: str
    length: int
    colour: str


SHIP_CONFIG: dict[str, ShipSpec] = {
    "C": ShipSpec("Carrier", 5, "#5D8AA8"),
    "B": ShipSpec("Battleship", 4, "#4A646C"),
    "D": ShipSpec("Destroyer", 3, "#3B444B"),
    "S": ShipSpec("Submarine", 3, "#232B2B"),
    "P": ShipSpec("Patrol", 2, "#8B0000"),
}

PROTOCOL_SHIP_ORDER = ("C", "B", "D", "S", "P")

CELL_SIZE = 40
BOARD_SIZE = 10
FLEET_SIZE = len(SHIP_CONFIG)

COLOR_WATER = "#1e3d59"
COLOR_MISS = "#daddd8"
COLOR_HIT = "#ff595e"

type Board = list[list[str | None]]
type BoardStore = dict[int, Board]


def _empty_board() -> Board:
    return [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
