from collections.abc import Iterator

from client.ui.constants import BOARD_SIZE

type Coordinate = tuple[int, int]


def parse_coordinate(value: str) -> Coordinate:
    """Convert a protocol coordinate such as A1 into a zero-based (row, column)."""
    value = value.strip().upper()

    if len(value) < 2:
        raise ValueError(f"Invalid coordinate: {value!r}")

    column_text = value[0]
    row_text = value[1:]

    if not column_text.isalpha() or len(column_text) != 1:
        raise ValueError(f"Invalid column in coordinate: {value!r}")

    if not row_text.isdigit():
        raise ValueError(f"Invalid row in coordinate: {value!r}")

    column = ord(column_text) - ord("A")
    row = int(row_text) - 1

    if not 0 <= row < BOARD_SIZE or not 0 <= column < BOARD_SIZE:
        raise ValueError(f"Coordinate outside board: {value!r}")

    return row, column


def format_coordinate(row: int, column: int) -> str:
    """Convert a zero-based (row, column) into a protocol coordinate."""
    if not 0 <= row < BOARD_SIZE or not 0 <= column < BOARD_SIZE:
        raise ValueError(f"Board position outside board: row={row}, column={column}")

    return f"{chr(ord('A') + column)}{row + 1}"


def iter_coordinate_range(
    start: str,
    end: str,
) -> Iterator[Coordinate]:
    """Yield every board position in a horizontal or vertical coordinate range."""
    start_row, start_column = parse_coordinate(start)
    end_row, end_column = parse_coordinate(end)

    if start_row != end_row and start_column != end_column:
        raise ValueError(
            f"Coordinate range must be horizontal or vertical: {start!r}-{end!r}"
        )

    if start_row == end_row:
        first_column, last_column = sorted((start_column, end_column))

        for column in range(first_column, last_column + 1):
            yield start_row, column
    else:
        first_row, last_row = sorted((start_row, end_row))

        for row in range(first_row, last_row + 1):
            yield row, start_column
