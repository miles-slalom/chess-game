"""Simple chess AI that selects a random legal move."""
from __future__ import annotations

import random
from typing import Optional

from .board import ChessBoard
from .models import Move, PieceColor
from .move_validator import MoveGenerator


class RandomMoveAI:
    """Baseline AI that randomly picks from the available legal moves."""

    def choose_move(self, board: ChessBoard, color: PieceColor) -> Optional[Move]:
        """Return a random legal move for the provided color."""

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
        if not legal_moves:
            return None
        return random.choice(legal_moves)
