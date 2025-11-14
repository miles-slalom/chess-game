"""Service layer for coordinating chess games and AI moves."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ..chess.ai import GreedyMoveAI
from ..chess.board import BoardState, ChessBoard, GameStatus
from ..chess.models import Move, PieceColor, PieceType, algebraic_to_index, index_to_algebraic
from ..chess.move_validator import MoveGenerator


@dataclass
class Game:
    """State container for a single chess game."""

    identifier: str
    board: ChessBoard
    player_color: PieceColor
    ai_color: PieceColor

    def to_board_state(self) -> BoardState:
        """Serialize the game board."""

        return self.board.to_state()


class GameManager:
    """Manage active games and delegate AI responses."""

    def __init__(self) -> None:
        self._games: Dict[str, Game] = {}
        self._ai = GreedyMoveAI()

    def create_game(self, player_color: PieceColor = PieceColor.WHITE) -> Game:
        """Create and register a new game."""

        game_id = uuid.uuid4().hex
        ai_color = player_color.opponent
        board = ChessBoard()
        board.reset()
        game = Game(identifier=game_id, board=board, player_color=player_color, ai_color=ai_color)
        self._games[game_id] = game
        if player_color is PieceColor.BLACK:
            self._trigger_ai_turn(game)
        return game

    def get_game(self, identifier: str) -> Game:
        """Retrieve a game by identifier."""

        game = self._games.get(identifier)
        if game is None:
            msg = "Game not found"
            raise KeyError(msg)
        return game

    def make_player_move(
        self, identifier: str, from_square: str, to_square: str, promotion: Optional[str] = None
    ) -> Tuple[Move, Optional[Move]]:
        """Apply a player's move and optionally respond with an AI move."""

        game = self.get_game(identifier)
        board = game.board
        if board.status is not GameStatus.ONGOING:
            msg = "Game has already concluded"
            raise ValueError(msg)
        if board.current_turn is not game.player_color:
            msg = "It is not the player's turn"
            raise ValueError(msg)
        player_move = self._build_move(board, from_square, to_square, promotion)
        if not MoveGenerator.is_valid_move(board, player_move):
            msg = "Illegal move"
            raise ValueError(msg)
        board.apply_move(player_move)
        MoveGenerator.update_game_status(board)
        ai_move = None
        if board.status is GameStatus.ONGOING and board.current_turn is game.ai_color:
            ai_move = self._trigger_ai_turn(game)
        return player_move, ai_move

    def _trigger_ai_turn(self, game: Game) -> Optional[Move]:
        board = game.board
        if board.status is not GameStatus.ONGOING:
            return None
        move = self._ai.choose_move(board, game.ai_color)
        if move is None:
            MoveGenerator.update_game_status(board)
            return None
        if not MoveGenerator.is_valid_move(board, move):
            # In the unlikely event our AI proposes an illegal move, skip it.
            MoveGenerator.update_game_status(board)
            return None
        board.apply_move(move)
        MoveGenerator.update_game_status(board)
        return move

    def _build_move(
        self, board: ChessBoard, from_square: str, to_square: str, promotion: Optional[str]
    ) -> Move:
        start = algebraic_to_index(from_square)
        end = algebraic_to_index(to_square)
        piece = board.get_piece(start)
        if piece is None:
            msg = "No piece at the source square"
            raise ValueError(msg)
        promotion_type = self._promotion_from_string(promotion)
        if promotion_type is None and piece.kind is PieceType.PAWN:
            dest_row, _ = end
            if dest_row in (0, 7):
                promotion_type = PieceType.QUEEN
        return Move(start=start, end=end, promotion=promotion_type)

    @staticmethod
    def _promotion_from_string(value: Optional[str]) -> Optional[PieceType]:
        if value is None:
            return None
        normalized = value.lower()
        try:
            return PieceType(normalized)
        except ValueError as exc:  # pragma: no cover - input validation
            msg = f"Unsupported promotion piece: {value}"
            raise ValueError(msg) from exc

    def serialize_move(self, move: Optional[Move]) -> Optional[dict[str, str]]:
        """Serialize a move for transport."""

        if move is None:
            return None
        start, end = move.to_algebraic()
        payload = {"from": start, "to": end}
        if move.promotion:
            payload["promotion"] = move.promotion.value
        return payload

    def list_moves_for_square(self, identifier: str, square: str) -> list[Move]:
        """Return all legal moves for a particular square."""

        game = self.get_game(identifier)
        index = algebraic_to_index(square)
        piece = game.board.get_piece(index)
        if piece is None or piece.color is not game.board.current_turn:
            return []
        return MoveGenerator.valid_moves_for_square(game.board, index)

    def serialize_moves(self, moves: list[Move]) -> list[dict[str, str]]:
        """Serialize a collection of moves."""

        serialized: list[dict[str, str]] = []
        for move in moves:
            payload = self.serialize_move(move)
            if payload is not None:
                serialized.append(payload)
        return serialized
