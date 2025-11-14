const API_BASE = "/api";
const PLAYER_COLOR = "white";

const files = ["a", "b", "c", "d", "e", "f", "g", "h"];
const ranks = ["8", "7", "6", "5", "4", "3", "2", "1"];

const state = {
  gameId: null,
  board: [],
  currentTurn: null,
  status: null,
  winner: null,
  selectedSquare: null,
  validTargets: new Set(),
};

const boardEl = document.getElementById("board");
const turnLabel = document.getElementById("turn-label");
const gameStatus = document.getElementById("game-status");
const moveLog = document.getElementById("move-log");
const newGameBtn = document.getElementById("new-game");

newGameBtn.addEventListener("click", () => startNewGame());
boardEl.addEventListener("click", handleSquareClick);

startNewGame();

async function startNewGame() {
  clearLog();
  updateStatus("Starting new game…", "Waiting for response…");
  try {
    const response = await fetch(`${API_BASE}/games`, { method: "POST" });
    const payload = await response.json();
    state.gameId = payload.game_id;
    syncState(payload.state);
  } catch (error) {
    updateStatus("Error", "Unable to start game");
    console.error(error);
  }
}

function syncState(newState) {
  state.board = newState.squares;
  state.currentTurn = newState.current_turn;
  state.status = newState.status;
  state.winner = newState.winner;
  state.selectedSquare = null;
  state.validTargets.clear();
  renderBoard();
  updateStatus(`Turn: ${state.currentTurn}`, formatGameStatus());
}

function renderBoard() {
  const map = new Map();
  state.board.forEach((square) => map.set(square.square, square));
  boardEl.innerHTML = "";
  ranks.forEach((rank, rowIndex) => {
    files.forEach((file, colIndex) => {
      const squareId = `${file}${rank}`;
      const classList = [
        "square",
        (rowIndex + colIndex) % 2 === 0 ? "light" : "dark",
      ];
      if (state.selectedSquare === squareId) {
        classList.push("selected");
      }
      if (state.validTargets.has(squareId)) {
        classList.push("valid-target");
      }
      const squareButton = document.createElement("div");
      squareButton.className = classList.join(" ");
      squareButton.dataset.square = squareId;
      const squareData = map.get(squareId);
      if (squareData?.piece) {
        const pieceEl = document.createElement("span");
        pieceEl.className = "piece";
        pieceEl.textContent = formatPieceSymbol(squareData);
        squareButton.appendChild(pieceEl);
      }
      boardEl.appendChild(squareButton);
    });
  });
}

function formatPieceSymbol(square) {
  const symbols = {
    white: {
      king: "WK",
      queen: "WQ",
      rook: "WR",
      bishop: "WB",
      knight: "WN",
      pawn: "WP",
    },
    black: {
      king: "bk",
      queen: "bq",
      rook: "br",
      bishop: "bb",
      knight: "bn",
      pawn: "bp",
    },
  };
  return symbols[square.color]?.[square.piece] ?? "";
}

async function handleSquareClick(event) {
  const squareEl = event.target.closest(".square");
  if (!squareEl || !state.gameId) {
    return;
  }
  const squareId = squareEl.dataset.square;
  const squareData = state.board.find((sq) => sq.square === squareId);
  const isPlayerPiece = squareData?.color === PLAYER_COLOR;

  if (!state.selectedSquare) {
    if (!isPlayerPiece || state.currentTurn !== PLAYER_COLOR) {
      return;
    }
    await selectSquare(squareId);
    return;
  }

  if (state.selectedSquare === squareId) {
    state.selectedSquare = null;
    state.validTargets.clear();
    renderBoard();
    return;
  }

  if (isPlayerPiece) {
    await selectSquare(squareId);
    return;
  }

  if (state.validTargets.has(squareId)) {
    await submitMove(state.selectedSquare, squareId);
  }
}

async function selectSquare(squareId) {
  state.selectedSquare = squareId;
  state.validTargets.clear();
  renderBoard();
  try {
    const response = await fetch(
      `${API_BASE}/games/${state.gameId}/moves/${squareId}`
    );
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    state.validTargets = new Set(data.moves.map((move) => move.to));
    renderBoard();
  } catch (error) {
    console.error("Unable to fetch moves", error);
  }
}

async function submitMove(fromSquare, toSquare) {
  updateStatus("Submitting move…", formatGameStatus());
  try {
    const response = await fetch(`${API_BASE}/games/${state.gameId}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_square: fromSquare, to_square: toSquare }),
    });
    if (!response.ok) {
      const errorPayload = await response.json();
      throw new Error(errorPayload.detail || "Move rejected");
    }
    const data = await response.json();
    syncState(data.state);
    recordMove("You", data.player_move);
    if (data.ai_move) {
      recordMove("AI", data.ai_move);
    }
  } catch (error) {
    updateStatus("Error", error.message);
  }
}

function recordMove(actor, move) {
  if (!move) return;
  const item = document.createElement("li");
  item.textContent = `${actor}: ${move.from} → ${move.to}`;
  moveLog.appendChild(item);
  moveLog.scrollTop = moveLog.scrollHeight;
}

function clearLog() {
  moveLog.innerHTML = "";
}

function updateStatus(turnText, statusText) {
  turnLabel.textContent = turnText;
  gameStatus.textContent = statusText;
}

function formatGameStatus() {
  if (state.status === "checkmate") {
    return state.winner === PLAYER_COLOR ? "You win" : "AI wins";
  }
  if (state.status === "stalemate") {
    return "Draw (stalemate)";
  }
  return "Game in progress";
}
