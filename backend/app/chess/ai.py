"""Chess AI strategies."""

from __future__ import annotations

import random

from .board import ChessBoard
from .models import Move, PieceColor, PieceType
from .move_validator import MoveGenerator

PIECE_VALUES: dict[PieceType, int] = {
    PieceType.PAWN: 1,
    PieceType.KNIGHT: 3,
    PieceType.BISHOP: 3,
    PieceType.ROOK: 5,
    PieceType.QUEEN: 9,
    PieceType.KING: 100,
}


def _collect_legal_moves(board: ChessBoard, color: PieceColor) -> list[Move]:
    legal_moves: list[Move] = []
    current_turn = board.current_turn
    board.current_turn = color
    try:
        for row in range(8):
            for col in range(8):
                origin = (row, col)
                legal_moves.extend(MoveGenerator.valid_moves_for_square(board, origin))
    finally:
        board.current_turn = current_turn
    return legal_moves


class RandomMoveAI:
    """Baseline AI that randomly picks from the available legal moves."""

    def choose_move(self, board: ChessBoard, color: PieceColor) -> Move | None:
        """Return a random legal move for the provided color."""

        legal_moves = _collect_legal_moves(board, color)
        if not legal_moves:
            return None
        return random.choice(legal_moves)


class GreedyMoveAI:
    """AI that prioritizes moves with the highest material gain."""

    def choose_move(self, board: ChessBoard, color: PieceColor) -> Move | None:
        """Return the move that captures the most valuable material."""

        legal_moves = _collect_legal_moves(board, color)
        if not legal_moves:
            return None
        best_moves: list[Move] = []
        best_score = -1
        for move in legal_moves:
            score = self._material_gain(board, move)
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)
        return random.choice(best_moves)

    def _material_gain(self, board: ChessBoard, move: Move) -> int:
        target = board.get_piece(move.end)
        if move.is_en_passant:
            target = board.get_piece((move.start[0], move.end[1]))
        capture_value = PIECE_VALUES[target.kind] if target else 0
        promotion_value = 0
        if move.promotion:
            promotion_value = max(0, PIECE_VALUES[move.promotion] - PIECE_VALUES[PieceType.PAWN])
        return capture_value + promotion_value
