"""Pydantic schemas for API contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .chess.board import BoardState, GameStatus
from .chess.models import PieceColor


class PieceSchema(BaseModel):
    """Serialized representation of a board square."""

    square: str
    piece: str | None = Field(default=None)
    color: str | None = Field(default=None)


class GameStateSchema(BaseModel):
    """Full board state returned to clients."""

    game_id: str
    squares: list[PieceSchema]
    current_turn: PieceColor
    status: GameStatus
    winner: PieceColor | None
    castling_rights: dict[str, dict[str, bool]]
    en_passant_target: str | None


class CreateGameResponse(BaseModel):
    """Response body for newly created games."""

    game_id: str
    state: GameStateSchema


class MoveRequest(BaseModel):
    """Payload for player move submissions."""

    from_square: str = Field(..., description="Algebraic square, e.g., e2")
    to_square: str = Field(..., description="Algebraic destination square")
    promotion: str | None = Field(default=None, description="Optional promotion piece")


class MoveResponse(BaseModel):
    """Response for move submissions, including any AI reply."""

    state: GameStateSchema
    player_move: dict[str, str]
    ai_move: dict[str, str] | None


class MovesResponse(BaseModel):
    """Response containing all legal moves for a given square."""

    moves: list[dict[str, str]]


def to_game_state_schema(game_id: str, board_state: BoardState) -> GameStateSchema:
    """Convert a BoardState into an API schema."""

    return GameStateSchema(
        game_id=game_id,
        squares=[PieceSchema(**square) for square in board_state.squares],
        current_turn=board_state.current_turn,
        status=board_state.status,
        winner=board_state.winner,
        castling_rights=board_state.castling_rights,
        en_passant_target=board_state.en_passant_target,
    )
