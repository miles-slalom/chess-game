"""Chess board implementation and helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import TypedDict

from .models import (
    BoardIndex,
    Move,
    Piece,
    PieceColor,
    PieceType,
    algebraic_to_index,
    in_bounds,
    index_to_algebraic,
)


def _default_castling_rights() -> dict[PieceColor, dict[str, bool]]:
    """Return a fresh copy of the default castling rights structure."""

    return {
        PieceColor.WHITE: {"kingside": True, "queenside": True},
        PieceColor.BLACK: {"kingside": True, "queenside": True},
    }


KING_START: dict[PieceColor, BoardIndex] = {
    PieceColor.WHITE: (7, 4),
    PieceColor.BLACK: (0, 4),
}

ROOK_START: dict[PieceColor, dict[str, BoardIndex]] = {
    PieceColor.WHITE: {"kingside": (7, 7), "queenside": (7, 0)},
    PieceColor.BLACK: {"kingside": (0, 7), "queenside": (0, 0)},
}


class GameStatus(str, Enum):
    """Describes the current outcome of a chess game."""

    ONGOING = "ongoing"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"


class SquarePayload(TypedDict):
    """Serialized representation of a single square."""

    square: str
    piece: str | None
    color: str | None


@dataclass
class BoardState:
    """Immutable snapshot of a board for serialization purposes."""

    squares: list[SquarePayload]
    current_turn: PieceColor
    status: GameStatus
    winner: PieceColor | None
    castling_rights: dict[str, dict[str, bool]]
    en_passant_target: str | None


@dataclass
class ChessBoard:
    """Mutable chess board model supporting move validation and application."""

    current_turn: PieceColor = PieceColor.WHITE
    status: GameStatus = GameStatus.ONGOING
    winner: PieceColor | None = None
    grid: list[list[Piece | None]] = field(
        default_factory=lambda: [[None for _ in range(8)] for _ in range(8)]
    )
    move_history: list[Move] = field(default_factory=list)
    castling_rights: dict[PieceColor, dict[str, bool]] = field(
        default_factory=_default_castling_rights
    )
    en_passant_target: BoardIndex | None = None

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
        self.castling_rights = _default_castling_rights()
        self.en_passant_target = None

    def clone(self) -> ChessBoard:
        """Return a deep copy of the board."""

        return deepcopy(self)

    def get_piece(self, index: BoardIndex) -> Piece | None:
        """Return the piece at the provided location."""

        row, col = index
        if not in_bounds(index):
            return None
        return self.grid[row][col]

    def set_piece(self, index: BoardIndex, piece: Piece | None) -> None:
        """Set the piece at the provided location."""

        row, col = index
        self.grid[row][col] = piece

    def find_king(self, color: PieceColor) -> BoardIndex | None:
        """Locate the king for the provided color."""

        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece and piece.kind is PieceType.KING and piece.color is color:
                    return row, col
        return None

    def to_state(self) -> BoardState:
        """Serialize the board to a transfer-friendly representation."""

        payload: list[SquarePayload] = []
        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                payload.append(
                    SquarePayload(
                        square=index_to_algebraic((row, col)),
                        piece=piece.kind.value if piece else None,
                        color=piece.color.value if piece else None,
                    )
                )
        return BoardState(
            squares=payload,
            current_turn=self.current_turn,
            status=self.status,
            winner=self.winner,
            castling_rights={
                color.value: {"kingside": rights["kingside"], "queenside": rights["queenside"]}
                for color, rights in self.castling_rights.items()
            },
            en_passant_target=index_to_algebraic(self.en_passant_target)
            if self.en_passant_target
            else None,
        )

    def apply_move(self, move: Move) -> None:
        """Apply a legal move, toggling the current turn."""

        piece = self.get_piece(move.start)
        if piece is None:
            msg = f"No piece at {move.start}"
            raise ValueError(msg)
        captured_piece = self.get_piece(move.end)
        arrival_piece = piece if move.promotion is None else Piece(piece.color, move.promotion)
        self._move_piece(move, piece, arrival_piece)
        self._update_castling_rights(piece, move, captured_piece)
        self._update_en_passant_state(piece, move)
        self.move_history.append(move)
        self.current_turn = self.current_turn.opponent

    def remove_piece(self, index: BoardIndex) -> None:
        """Clear a square."""

        self.set_piece(index, None)

    def _move_piece(self, move: Move, piece: Piece, arrival_piece: Piece) -> None:
        """Execute the physical movement of a piece, including special cases."""

        self.set_piece(move.start, None)
        if move.is_castling:
            self._perform_castling_move(move, arrival_piece)
            return
        self.set_piece(move.end, arrival_piece)
        if move.is_en_passant:
            capture_index = (move.start[0], move.end[1])
            self.set_piece(capture_index, None)

    def _perform_castling_move(self, move: Move, king_piece: Piece) -> None:
        """Move both king and rook for a castling move."""

        row = move.start[0]
        if move.end[1] == 6:
            rook_from = (row, 7)
            rook_to = (row, 5)
        else:
            rook_from = (row, 0)
            rook_to = (row, 3)
        rook = self.get_piece(rook_from)
        self.set_piece(move.end, king_piece)
        if rook:
            self.set_piece(rook_to, rook)
        else:  # pragma: no cover - defensive fallback
            self.set_piece(rook_to, Piece(king_piece.color, PieceType.ROOK))
        self.set_piece(rook_from, None)

    def _update_castling_rights(
        self, piece: Piece, move: Move, captured_piece: Piece | None
    ) -> None:
        """Adjust castling rights based on the latest move."""

        if piece.kind is PieceType.KING:
            self._disable_castling(piece.color)
        if piece.kind is PieceType.ROOK:
            self._disable_rook_right(piece.color, move.start)
        if captured_piece and captured_piece.kind is PieceType.ROOK:
            self._disable_rook_right(captured_piece.color, move.end)

    def _disable_castling(self, color: PieceColor) -> None:
        self.castling_rights[color]["kingside"] = False
        self.castling_rights[color]["queenside"] = False

    def _disable_rook_right(self, color: PieceColor, square: BoardIndex) -> None:
        for side, origin in ROOK_START[color].items():
            if square == origin:
                self.castling_rights[color][side] = False

    def _update_en_passant_state(self, piece: Piece, move: Move) -> None:
        """Record en-passant opportunities following a pawn advance."""

        self.en_passant_target = None
        if piece.kind is PieceType.PAWN and abs(move.start[0] - move.end[0]) == 2:
            intermediate_row = (move.start[0] + move.end[0]) // 2
            self.en_passant_target = (intermediate_row, move.start[1])

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
        self.castling_rights = _default_castling_rights()
        self.en_passant_target = None


def board_from_dict(payload: dict[str, str]) -> ChessBoard:
    """Create a board from a mapping of squares to piece descriptors."""

    board = ChessBoard()
    board.reset()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    for square, descriptor in payload.items():
        row, col = algebraic_to_index(square)
        color_value, piece_value = descriptor.split(":")
        board.grid[row][col] = Piece(color=PieceColor(color_value), kind=PieceType(piece_value))
    board.castling_rights = _default_castling_rights()
    board.en_passant_target = None
    return board
