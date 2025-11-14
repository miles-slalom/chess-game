"""Move generation and validation utilities."""

from __future__ import annotations

from collections.abc import Iterable

from .board import ChessBoard, GameStatus
from .models import (
    BoardIndex,
    Move,
    Piece,
    PieceColor,
    PieceType,
    in_bounds,
)


class MoveGenerator:
    """Generate legal chess moves and detect game states."""

    KNIGHT_DELTAS = [
        (-2, -1),
        (-2, 1),
        (-1, -2),
        (-1, 2),
        (1, -2),
        (1, 2),
        (2, -1),
        (2, 1),
    ]

    KING_DELTAS = [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ]

    @classmethod
    def valid_moves_for_square(cls, board: ChessBoard, origin: BoardIndex) -> list[Move]:
        """Return all legal moves originating from the given square."""

        piece = board.get_piece(origin)
        if piece is None or piece.color is not board.current_turn:
            return []
        raw_moves = list(cls._candidate_moves(board, origin, piece))
        legal_moves: list[Move] = []
        for move in raw_moves:
            if cls._keeps_king_safe(board, move, piece.color):
                legal_moves.append(move)
        return legal_moves

    @classmethod
    def is_valid_move(cls, board: ChessBoard, move: Move) -> bool:
        """True if the provided move is legal in the current position."""

        piece = board.get_piece(move.start)
        if piece is None:
            return False
        return move in cls.valid_moves_for_square(board, move.start)

    @classmethod
    def update_game_status(cls, board: ChessBoard) -> None:
        """Set the board's GameStatus based on available moves."""

        legal_moves_exist = cls.any_legal_move(board, board.current_turn)
        in_check = cls.is_in_check(board, board.current_turn)
        if legal_moves_exist:
            board.status = GameStatus.ONGOING
            board.winner = None
            return
        if in_check:
            board.status = GameStatus.CHECKMATE
            board.winner = board.current_turn.opponent
        else:
            board.status = GameStatus.STALEMATE
            board.winner = None

    @classmethod
    def any_legal_move(cls, board: ChessBoard, color: PieceColor) -> bool:
        """Return True if the color has at least one legal move."""

        for row in range(8):
            for col in range(8):
                origin = (row, col)
                piece = board.get_piece(origin)
                if piece and piece.color is color:
                    current_turn = board.current_turn
                    board.current_turn = color
                    if cls.valid_moves_for_square(board, origin):
                        board.current_turn = current_turn
                        return True
                    board.current_turn = current_turn
        return False

    @classmethod
    def _candidate_moves(
        cls, board: ChessBoard, origin: BoardIndex, piece: Piece
    ) -> Iterable[Move]:
        if piece.kind is PieceType.PAWN:
            yield from cls._pawn_moves(board, origin, piece)
        elif piece.kind is PieceType.KNIGHT:
            yield from cls._step_moves(board, origin, piece, cls.KNIGHT_DELTAS)
        elif piece.kind is PieceType.BISHOP:
            yield from cls._sliding_moves(board, origin, piece, diagonal=True)
        elif piece.kind is PieceType.ROOK:
            yield from cls._sliding_moves(board, origin, piece, orthogonal=True)
        elif piece.kind is PieceType.QUEEN:
            yield from cls._sliding_moves(board, origin, piece, orthogonal=True, diagonal=True)
        elif piece.kind is PieceType.KING:
            yield from cls._step_moves(board, origin, piece, cls.KING_DELTAS)
            yield from cls._castling_moves(board, origin, piece)

    @classmethod
    def _pawn_moves(cls, board: ChessBoard, origin: BoardIndex, piece: Piece) -> Iterable[Move]:
        direction = -1 if piece.color is PieceColor.WHITE else 1
        start_row = 6 if piece.color is PieceColor.WHITE else 1
        row, col = origin
        forward_one = (row + direction, col)
        if in_bounds(forward_one) and board.get_piece(forward_one) is None:
            yield cls._maybe_promote(Move(origin, forward_one), piece, forward_one)
            forward_two = (row + 2 * direction, col)
            if row == start_row and board.get_piece(forward_two) is None:
                yield Move(origin, forward_two)
        for delta_col in (-1, 1):
            capture_square = (row + direction, col + delta_col)
            if not in_bounds(capture_square):
                continue
            target = board.get_piece(capture_square)
            if target and target.color is not piece.color:
                yield cls._maybe_promote(Move(origin, capture_square), piece, capture_square)
                continue
            adjacent = board.get_piece((row, col + delta_col))
            if (
                board.en_passant_target
                and board.en_passant_target == capture_square
                and adjacent
                and adjacent.color is not piece.color
                and adjacent.kind is PieceType.PAWN
            ):
                yield Move(origin, capture_square, is_en_passant=True)

    @classmethod
    def _maybe_promote(cls, move: Move, piece: Piece, destination: BoardIndex) -> Move:
        if piece.kind is not PieceType.PAWN:
            return move
        dest_row, _ = destination
        promotion_rank = 0 if piece.color is PieceColor.WHITE else 7
        if dest_row == promotion_rank:
            return Move(move.start, move.end, promotion=PieceType.QUEEN)
        return move

    @classmethod
    def _step_moves(
        cls,
        board: ChessBoard,
        origin: BoardIndex,
        piece: Piece,
        deltas: Iterable[tuple[int, int]],
    ) -> Iterable[Move]:
        for delta_row, delta_col in deltas:
            destination = (origin[0] + delta_row, origin[1] + delta_col)
            if not in_bounds(destination):
                continue
            target = board.get_piece(destination)
            if target is None or target.color is not piece.color:
                yield Move(origin, destination)

    @classmethod
    def _sliding_moves(
        cls,
        board: ChessBoard,
        origin: BoardIndex,
        piece: Piece,
        orthogonal: bool = False,
        diagonal: bool = False,
    ) -> Iterable[Move]:
        directions: list[tuple[int, int]] = []
        if orthogonal:
            directions.extend([(-1, 0), (1, 0), (0, -1), (0, 1)])
        if diagonal:
            directions.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
        for delta_row, delta_col in directions:
            row, col = origin
            while True:
                row += delta_row
                col += delta_col
                destination = (row, col)
                if not in_bounds(destination):
                    break
                target = board.get_piece(destination)
                if target is None:
                    yield Move(origin, destination)
                    continue
                if target.color is not piece.color:
                    yield Move(origin, destination)
                break

    @classmethod
    def _castling_moves(cls, board: ChessBoard, origin: BoardIndex, piece: Piece) -> Iterable[Move]:
        rights = board.castling_rights.get(piece.color)
        if not rights:
            return
        row = 7 if piece.color is PieceColor.WHITE else 0
        if origin != (row, 4):
            return
        if cls.is_in_check(board, piece.color):
            return
        opponent = piece.color.opponent

        def path_clear(squares: Iterable[BoardIndex]) -> bool:
            return all(board.get_piece(square) is None for square in squares)

        def safe_squares(squares: Iterable[BoardIndex]) -> bool:
            return all(not cls.is_square_attacked(board, square, opponent) for square in squares)

        if rights.get("kingside"):
            rook_square = (row, 7)
            between = [(row, 5), (row, 6)]
            rook = board.get_piece(rook_square)
            if (
                rook
                and rook.kind is PieceType.ROOK
                and rook.color is piece.color
                and path_clear(between)
                and safe_squares(between)
            ):
                yield Move(origin, (row, 6), is_castling=True)
        if rights.get("queenside"):
            rook_square = (row, 0)
            between = [(row, 1), (row, 2), (row, 3)]
            king_path = [(row, 3), (row, 2)]
            rook = board.get_piece(rook_square)
            if (
                rook
                and rook.kind is PieceType.ROOK
                and rook.color is piece.color
                and path_clear(between)
                and safe_squares(king_path)
            ):
                yield Move(origin, (row, 2), is_castling=True)

    @classmethod
    def _keeps_king_safe(cls, board: ChessBoard, move: Move, color: PieceColor) -> bool:
        clone = board.clone()
        try:
            clone.apply_move(move)
        except ValueError:
            return False
        king_position = clone.find_king(color)
        if king_position is None:
            return False
        return not cls.is_square_attacked(clone, king_position, color.opponent)

    @classmethod
    def is_square_attacked(
        cls, board: ChessBoard, square: BoardIndex, attacker: PieceColor
    ) -> bool:
        # Pawns
        direction = -1 if attacker is PieceColor.WHITE else 1
        for delta_col in (-1, 1):
            candidate = (square[0] - direction, square[1] - delta_col)
            if not in_bounds(candidate):
                continue
            piece = board.get_piece(candidate)
            if piece and piece.color is attacker and piece.kind is PieceType.PAWN:
                return True
        # Knights
        for delta_row, delta_col in cls.KNIGHT_DELTAS:
            candidate = (square[0] + delta_row, square[1] + delta_col)
            if not in_bounds(candidate):
                continue
            piece = board.get_piece(candidate)
            if piece and piece.color is attacker and piece.kind is PieceType.KNIGHT:
                return True
        # Sliding pieces
        if cls._attacks_from_directions(
            board,
            square,
            attacker,
            [(-1, 0), (1, 0), (0, -1), (0, 1)],
            {PieceType.ROOK, PieceType.QUEEN},
        ):
            return True
        if cls._attacks_from_directions(
            board,
            square,
            attacker,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)],
            {PieceType.BISHOP, PieceType.QUEEN},
        ):
            return True
        # Kings
        for delta_row, delta_col in cls.KING_DELTAS:
            candidate = (square[0] + delta_row, square[1] + delta_col)
            if not in_bounds(candidate):
                continue
            piece = board.get_piece(candidate)
            if piece and piece.color is attacker and piece.kind is PieceType.KING:
                return True
        return False

    @classmethod
    def _attacks_from_directions(
        cls,
        board: ChessBoard,
        square: BoardIndex,
        attacker: PieceColor,
        directions: Iterable[tuple[int, int]],
        valid_types: set[PieceType],
    ) -> bool:
        for delta_row, delta_col in directions:
            row, col = square
            while True:
                row += delta_row
                col += delta_col
                candidate = (row, col)
                if not in_bounds(candidate):
                    break
                piece = board.get_piece(candidate)
                if piece is None:
                    continue
                if piece.color is attacker and piece.kind in valid_types:
                    return True
                break
        return False

    @classmethod
    def is_in_check(cls, board: ChessBoard, color: PieceColor) -> bool:
        """Return True if the provided color is currently in check."""

        king_position = board.find_king(color)
        if king_position is None:
            return False
        return cls.is_square_attacked(board, king_position, color.opponent)
