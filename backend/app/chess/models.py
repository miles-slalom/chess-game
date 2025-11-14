"""Core chess domain models and helper utilities."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

BOARD_FILES = "abcdefgh"
BOARD_RANKS = "12345678"
BoardIndex = tuple[int, int]


class PieceColor(str, Enum):
    """Enumeration of chess piece colors."""

    WHITE = "white"
    BLACK = "black"

    @property
    def opponent(self) -> PieceColor:
        """Return the opposing color."""

        return PieceColor.BLACK if self is PieceColor.WHITE else PieceColor.WHITE


class PieceType(str, Enum):
    """Enumeration of chess piece types."""

    KING = "king"
    QUEEN = "queen"
    ROOK = "rook"
    BISHOP = "bishop"
    KNIGHT = "knight"
    PAWN = "pawn"


@dataclass(frozen=True)
class Piece:
    """A chess piece present on a board square."""

    color: PieceColor
    kind: PieceType


@dataclass(frozen=True)
class Move:
    """Representation of a chess move using zero-based matrix coordinates."""

    start: BoardIndex
    end: BoardIndex
    promotion: PieceType | None = None
    is_castling: bool = False
    is_en_passant: bool = False

    def to_algebraic(self) -> tuple[str, str]:
        """Return the move as algebraic square strings."""

        return index_to_algebraic(self.start), index_to_algebraic(self.end)


def in_bounds(index: BoardIndex) -> bool:
    """Return True if the provided index is on the board."""

    row, col = index
    return 0 <= row < 8 and 0 <= col < 8


def algebraic_to_index(square: str) -> BoardIndex:
    """Convert algebraic notation (e.g., "e4") to a matrix index."""

    file_char = square[0].lower()
    rank_char = square[1]
    col = BOARD_FILES.index(file_char)
    row = 8 - BOARD_RANKS.index(rank_char) - 1
    return row, col


def index_to_algebraic(index: BoardIndex) -> str:
    """Convert a matrix index to standard algebraic notation."""

    row, col = index
    file_char = BOARD_FILES[col]
    rank_char = BOARD_RANKS[7 - row]
    return f"{file_char}{rank_char}"


def iter_directions(
    directions: Sequence[tuple[int, int]], start: BoardIndex
) -> Iterable[BoardIndex]:
    """Yield successive squares along provided directions until out of bounds."""

    for delta_row, delta_col in directions:
        row, col = start
        while True:
            row += delta_row
            col += delta_col
            candidate = (row, col)
            if not in_bounds(candidate):
                break
            yield candidate


ORTHOGONAL_DIRECTIONS: list[tuple[int, int]] = [
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
]

DIAGONAL_DIRECTIONS: list[tuple[int, int]] = [
    (-1, -1),
    (-1, 1),
    (1, -1),
    (1, 1),
]
