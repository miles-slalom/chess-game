"""Chess board implementation and helpers."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .models import (
    BoardIndex,
    Move,
    Piece,
    PieceColor,
    PieceType,
    algebraic_to_index,
    index_to_algebraic,
    in_bounds,
)


class GameStatus(str, Enum):
    """Describes the current outcome of a chess game."""

    ONGOING = "ongoing"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"


@dataclass
class BoardState:
    """Immutable snapshot of a board for serialization purposes."""

    squares: List[Dict[str, Optional[str]]]
    current_turn: PieceColor
    status: GameStatus
    winner: Optional[PieceColor]


@dataclass
class ChessBoard:
    """Mutable chess board model supporting move validation and application."""

    current_turn: PieceColor = PieceColor.WHITE
    status: GameStatus = GameStatus.ONGOING
    winner: Optional[PieceColor] = None
    grid: List[List[Optional[Piece]]] = field(
        default_factory=lambda: [[None for _ in range(8)] for _ in range(8)]
    )
    move_history: List[Move] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset the board to the standard chess starting position."""

        self.grid = [[None for _ in range(8)] for _ in range(8)]
        placement_order = [
            PieceType.ROOK,
            PieceType.KNIGHT,
            PieceType.BISHOP,
            PieceType.QUEEN,
            PieceType.KING,
            PieceType.BISHOP,
            PieceType.KNIGHT,
            PieceType.ROOK,
        ]
        for col, piece_type in enumerate(placement_order):
            self.grid[0][col] = Piece(color=PieceColor.BLACK, kind=piece_type)
            self.grid[7][col] = Piece(color=PieceColor.WHITE, kind=piece_type)
        for col in range(8):
            self.grid[1][col] = Piece(color=PieceColor.BLACK, kind=PieceType.PAWN)
            self.grid[6][col] = Piece(color=PieceColor.WHITE, kind=PieceType.PAWN)
        self.current_turn = PieceColor.WHITE
        self.status = GameStatus.ONGOING
        self.winner = None
        self.move_history = []

    def clone(self) -> "ChessBoard":
        """Return a deep copy of the board."""

        return deepcopy(self)

    def get_piece(self, index: BoardIndex) -> Optional[Piece]:
        """Return the piece at the provided location."""

        row, col = index
        if not in_bounds(index):
            return None
        return self.grid[row][col]

    def set_piece(self, index: BoardIndex, piece: Optional[Piece]) -> None:
        """Set the piece at the provided location."""

        row, col = index
        self.grid[row][col] = piece

    def find_king(self, color: PieceColor) -> Optional[BoardIndex]:
        """Locate the king for the provided color."""

        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece and piece.kind is PieceType.KING and piece.color is color:
                    return row, col
        return None

    def to_state(self) -> BoardState:
        """Serialize the board to a transfer-friendly representation."""

        payload: List[Dict[str, Optional[str]]] = []
        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                payload.append(
                    {
                        "square": index_to_algebraic((row, col)),
                        "piece": piece.kind.value if piece else None,
                        "color": piece.color.value if piece else None,
                    }
                )
        return BoardState(
            squares=payload,
            current_turn=self.current_turn,
            status=self.status,
            winner=self.winner,
        )

    def apply_move(self, move: Move) -> None:
        """Apply a legal move, toggling the current turn."""

        piece = self.get_piece(move.start)
        if piece is None:
            msg = f"No piece at {move.start}"
            raise ValueError(msg)
        self.set_piece(move.end, piece if move.promotion is None else Piece(piece.color, move.promotion))
        self.set_piece(move.start, None)
        self.move_history.append(move)
        self.current_turn = self.current_turn.opponent

    def remove_piece(self, index: BoardIndex) -> None:
        """Clear a square."""

        self.set_piece(index, None)

    def load_from_fen(self, fen: str) -> None:
        """Load a board position from a simple FEN string."""

        ranks = fen.split("/")
        if len(ranks) != 8:
            msg = "FEN must contain eight ranks"
            raise ValueError(msg)
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        for row, rank in enumerate(ranks):
            col = 0
            for char in rank:
                if char.isdigit():
                    col += int(char)
                    continue
                color = PieceColor.WHITE if char.isupper() else PieceColor.BLACK
                piece_map = {
                    "k": PieceType.KING,
                    "q": PieceType.QUEEN,
                    "r": PieceType.ROOK,
                    "b": PieceType.BISHOP,
                    "n": PieceType.KNIGHT,
                    "p": PieceType.PAWN,
                }
                kind = piece_map[char.lower()]
                self.grid[row][col] = Piece(color=color, kind=kind)
                col += 1
        self.current_turn = PieceColor.WHITE
        self.status = GameStatus.ONGOING
        self.winner = None
        self.move_history = []


def board_from_dict(payload: Dict[str, str]) -> ChessBoard:
    """Create a board from a mapping of squares to piece descriptors."""

    board = ChessBoard()
    board.reset()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    for square, descriptor in payload.items():
        row, col = algebraic_to_index(square)
        color_value, piece_value = descriptor.split(":")
        board.grid[row][col] = Piece(color=PieceColor(color_value), kind=PieceType(piece_value))
    return board
