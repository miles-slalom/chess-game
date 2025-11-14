"""Unit tests for chess logic and game manager orchestration."""
from backend.app.chess.board import ChessBoard
from backend.app.chess.models import Piece, PieceColor, PieceType, algebraic_to_index
from backend.app.chess.move_validator import MoveGenerator
from backend.app.services.game_manager import GameManager


def test_knight_initial_moves():
    board = ChessBoard()
    origin = algebraic_to_index("b1")
    moves = MoveGenerator.valid_moves_for_square(board, origin)
    destinations = {move.to_algebraic()[1] for move in moves}
    assert destinations == {"a3", "c3"}


def test_pawn_promotion_moves_include_queen():
    board = ChessBoard()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.current_turn = PieceColor.WHITE
    origin = (1, 0)
    board.set_piece(origin, Piece(PieceColor.WHITE, PieceType.PAWN))
    moves = MoveGenerator.valid_moves_for_square(board, origin)
    promotion_moves = [move for move in moves if move.end == (0, 0)]
    assert promotion_moves, "Expected a forward promotion move"
    assert promotion_moves[0].promotion is PieceType.QUEEN


def test_game_manager_handles_player_and_ai_turns():
    manager = GameManager()
    game = manager.create_game()
    player_move, ai_move = manager.make_player_move(game.identifier, "e2", "e4")
    assert player_move.to_algebraic() == ("e2", "e4")
    updated_game = manager.get_game(game.identifier)
    assert updated_game.board.move_history
    if ai_move is not None:
        assert ai_move in updated_game.board.move_history
