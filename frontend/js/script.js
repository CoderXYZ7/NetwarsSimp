let placementMode = false;
const baseUrl = '/api/v1';

// Initialize the game boards
function initializeBoards() {
    const boards = ['selfBoard', 'opponentBoard'];
    boards.forEach(boardId => {
        const board = document.getElementById(boardId);
        board.innerHTML = '';
        for (let i = 0; i < 100; i++) {
            const cell = document.createElement('div');
            cell.className = 'cell';
            cell.dataset.x = i % 10;
            cell.dataset.y = Math.floor(i / 10);
            cell.addEventListener('click', (e) => handleCellClick(e, boardId));
            board.appendChild(cell);
        }
    });
}

// Handle cell clicks for ship placement and attacks
function handleCellClick(event, boardId) {
    const cell = event.target;
    const x = parseInt(cell.dataset.x);
    const y = parseInt(cell.dataset.y);
    const gameId = document.getElementById('gameId').value;
    const playerId = document.getElementById('playerId').value;

    if (boardId === 'selfBoard' && placementMode) {
        placeShip(gameId, playerId, x, y);
    } else if (boardId === 'opponentBoard' && !placementMode) {
        attackPosition(gameId, playerId, x, y);
    }
}

// Toggle ship placement mode
function togglePlacementMode() {
    placementMode = !placementMode;
    const btn = document.querySelector('.ship-placement button');
    btn.textContent = placementMode ? 'Cancel Placement' : 'Place Ship';
    btn.style.backgroundColor = placementMode ? '#ff4444' : '#4CAF50';
}

// Initialize game state
async function initializeGame() {
    const gameId = document.getElementById('gameId').value;
    const playerId = document.getElementById('playerId').value;
    
    if (!gameId || !playerId) {
        updateStatus('Please enter both Game ID and Player ID');
        return;
    }

    initializeBoards();
    await refreshBoards();
}

// Place a ship
async function placeShip(gameId, playerId, x, y) {
    const shipType = document.getElementById('shipType').value;
    const orientation = document.getElementById('orientation').value;

    try {
        const response = await fetch(`${baseUrl}/game/place-ship`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ship: {
                    game_id: parseInt(gameId),
                    player_id: parseInt(playerId),
                    type: shipType,
                    x: x,
                    y: y,
                    orientation: orientation
                }
            })
        });

        const data = await response.json();
        if (data.placeShip.result === 1) {
            updateStatus('Ship placed successfully');
            togglePlacementMode();
            refreshBoards();
        } else {
            updateStatus('Invalid ship placement');
        }
    } catch (error) {
        updateStatus('Error placing ship: ' + error.message);
    }
}

// Attack a position
async function attackPosition(gameId, playerId, x, y) {
    try {
        const response = await fetch(`${baseUrl}/game/attack`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                attack: {
                    x: x,
                    y: y,
                    game_id: parseInt(gameId),
                    attacker: parseInt(playerId),
                    receiver: parseInt(playerId) === 1 ? 2 : 1 // Simple logic for 2 players
                }
            })
        });

        const data = await response.json();
        const results = ['Miss!', 'Hit!', 'Ship Sunk!'];
        updateStatus(results[data.attack.result]);
        refreshBoards();
    } catch (error) {
        updateStatus('Error attacking position: ' + error.message);
    }
}

// Refresh both game boards
async function refreshBoards() {
    const gameId = document.getElementById('gameId').value;
    const playerId = document.getElementById('playerId').value;

    try {
        // Get self board
        const selfResponse = await fetch(`${baseUrl}/game/status/self?game_id=${gameId}&player_id=${playerId}`);
        const selfData = await selfResponse.json();
        updateSelfBoard(selfData.game.boardSelf);

        // Get opponent board
        const oppResponse = await fetch(`${baseUrl}/game/status/opponent?game_id=${gameId}&player_id=${playerId}`);
        const oppData = await oppResponse.json();
        updateOpponentBoard(oppData.game.boardOpponent);
    } catch (error) {
        updateStatus('Error refreshing boards: ' + error.message);
    }
}

// Update self board display
function updateSelfBoard(boardData) {
    const cells = document.querySelectorAll('#selfBoard .cell');
    const boardArray = boardData.split(',');
    
    cells.forEach((cell, index) => {
        const cellData = boardArray[index];
        const shipType = cellData.substring(0, 2);
        const isHit = cellData.charAt(4) === '1';
        
        cell.className = 'cell';
        if (shipType !== 'WT') {
            cell.classList.add('ship');
            cell.textContent = shipType;
        }
        if (isHit) {
            cell.classList.add('hit');
        }
    });
}

// Update opponent board display
function updateOpponentBoard(boardData) {
    const cells = document.querySelectorAll('#opponentBoard .cell');
    const boardArray = boardData.split(',');
    
    cells.forEach((cell, index) => {
        const status = boardArray[index];
        cell.className = 'cell';
        if (status === '1') {
            cell.classList.add('miss');
        } else if (status === '2') {
            cell.classList.add('hit');
        }
    });
}

// Update status message
function updateStatus(message) {
    const statusDiv = document.getElementById('gameStatus');
    statusDiv.textContent = message;
}

// Initialize boards on page load
document.addEventListener('DOMContentLoaded', initializeBoards);