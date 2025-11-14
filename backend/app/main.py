"""FastAPI entry point for the chess web application."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .chess.models import PieceColor
from .schemas import (
    CreateGameResponse,
    GameStateSchema,
    MoveRequest,
    MoveResponse,
    MovesResponse,
    to_game_state_schema,
)
from .services.game_manager import GameManager

app = FastAPI(title="Chess AI Web", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

game_manager = GameManager()


@app.get("/healthz")
def health_check() -> dict[str, str]:
    """Return a simple health indicator."""

    return {"status": "ok"}


@app.post("/api/games", response_model=CreateGameResponse)
async def create_game(player_color: PieceColor = PieceColor.WHITE) -> CreateGameResponse:
    """Initialize a new chess game."""

    game = game_manager.create_game(player_color=player_color)
    state = to_game_state_schema(game.identifier, game.to_board_state())
    return CreateGameResponse(game_id=game.identifier, state=state)


@app.get("/api/games/{game_id}", response_model=GameStateSchema)
async def get_game(game_id: str) -> GameStateSchema:
    """Fetch a game state by identifier."""

    try:
        game = game_manager.get_game(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc
    return to_game_state_schema(game.identifier, game.to_board_state())


@app.post("/api/games/{game_id}/move", response_model=MoveResponse)
async def make_move(game_id: str, payload: MoveRequest) -> MoveResponse:
    """Apply a player's move and return the updated board plus optional AI reply."""

    try:
        player_move, ai_move = game_manager.make_player_move(
            game_id, payload.from_square, payload.to_square, payload.promotion
        )
        game = game_manager.get_game(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    state = to_game_state_schema(game.identifier, game.to_board_state())
    serialized_player_move = game_manager.serialize_move(player_move)
    if serialized_player_move is None:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail="Unable to serialize player move")
    return MoveResponse(
        state=state,
        player_move=serialized_player_move,
        ai_move=game_manager.serialize_move(ai_move),
    )


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/api/games/{game_id}/moves/{square}", response_model=MovesResponse)
async def list_moves(game_id: str, square: str) -> MovesResponse:
    """Return all valid moves for a given square."""

    try:
        moves = game_manager.list_moves_for_square(game_id, square)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc
    serialized = game_manager.serialize_moves(moves)
    return MovesResponse(moves=serialized)
