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
    board.set_piece((7, 4), Piece(PieceColor.WHITE, PieceType.KING))
    board.set_piece((0, 4), Piece(PieceColor.BLACK, PieceType.KING))
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


def test_update_game_status_detects_checkmate():
    board = ChessBoard()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.set_piece(algebraic_to_index("h8"), Piece(PieceColor.BLACK, PieceType.KING))
    board.set_piece(algebraic_to_index("g7"), Piece(PieceColor.WHITE, PieceType.QUEEN))
    board.set_piece(algebraic_to_index("f6"), Piece(PieceColor.WHITE, PieceType.KING))
    board.current_turn = PieceColor.BLACK
    MoveGenerator.update_game_status(board)
    assert board.status.name.lower() == "checkmate"
    assert board.winner is PieceColor.WHITE


def test_update_game_status_detects_stalemate():
    board = ChessBoard()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.set_piece(algebraic_to_index("h8"), Piece(PieceColor.BLACK, PieceType.KING))
    board.set_piece(algebraic_to_index("f7"), Piece(PieceColor.WHITE, PieceType.KING))
    board.set_piece(algebraic_to_index("g6"), Piece(PieceColor.WHITE, PieceType.QUEEN))
    board.current_turn = PieceColor.BLACK
    MoveGenerator.update_game_status(board)
    assert board.status.name.lower() == "stalemate"
    assert board.winner is None


def test_en_passant_execution_removes_captured_pawn():
    board = ChessBoard()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.current_turn = PieceColor.WHITE
    board.set_piece((7, 4), Piece(PieceColor.WHITE, PieceType.KING))
    board.set_piece((0, 4), Piece(PieceColor.BLACK, PieceType.KING))
    white_origin = (3, 4)
    board.set_piece(white_origin, Piece(PieceColor.WHITE, PieceType.PAWN))
    board.set_piece((3, 3), Piece(PieceColor.BLACK, PieceType.PAWN))
    board.en_passant_target = (2, 3)
    moves = MoveGenerator.valid_moves_for_square(board, white_origin)
    en_passant_moves = [move for move in moves if move.is_en_passant]
    assert en_passant_moves
    board.apply_move(en_passant_moves[0])
    assert board.get_piece((3, 3)) is None
    destination_piece = board.get_piece((2, 3))
    assert destination_piece and destination_piece.color is PieceColor.WHITE


def test_castling_moves_king_and_rook():
    board = ChessBoard()
    board.grid = [[None for _ in range(8)] for _ in range(8)]
    board.current_turn = PieceColor.WHITE
    board.set_piece((0, 4), Piece(PieceColor.BLACK, PieceType.KING))
    board.castling_rights = {
        PieceColor.WHITE: {"kingside": True, "queenside": True},
        PieceColor.BLACK: {"kingside": False, "queenside": False},
    }
    board.set_piece((7, 4), Piece(PieceColor.WHITE, PieceType.KING))
    board.set_piece((7, 7), Piece(PieceColor.WHITE, PieceType.ROOK))
    moves = MoveGenerator.valid_moves_for_square(board, (7, 4))
    castle_moves = [move for move in moves if move.is_castling and move.end == (7, 6)]
    assert castle_moves
    board.apply_move(castle_moves[0])
    king_dest = board.get_piece((7, 6))
    rook_dest = board.get_piece((7, 5))
    assert king_dest and king_dest.kind is PieceType.KING
    assert rook_dest and rook_dest.kind is PieceType.ROOK
    assert not board.castling_rights[PieceColor.WHITE]["kingside"]
