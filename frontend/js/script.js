const API_URL = '/api/v1';
let token = localStorage.getItem('token');
let currentGame = null;
let isMyTurn = false;

// Ship Placement Variables
const SHIPS = {
    'Carrier': 5,
    'Battleship': 4,
    'Cruiser': 3,
    'Submarine': 3,
    'Destroyer': 2
};

let selectedShip = null;
let isHorizontal = true;
let placedShips = new Map();

// Game Board Functions
function createGameBoard(containerId, isPlayerBoard = true) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    // Create coordinate labels
    const letters = ['', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];
    const numbers = ['', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'];

    // Create the grid with coordinates
    for (let i = 0; i < 11; i++) {
        for (let j = 0; j < 11; j++) {
            const cell = document.createElement('div');
            
            if (i === 0 && j === 0) {
                // Empty corner cell
                cell.className = 'coordinate-label';
            } else if (i === 0) {
                // Column labels (letters)
                cell.className = 'coordinate-label';
                cell.textContent = letters[j];
            } else if (j === 0) {
                // Row labels (numbers)
                cell.className = 'coordinate-label';
                cell.textContent = numbers[i];
            } else {
                // Game cells
                cell.className = 'cell';
                cell.dataset.x = j - 1;
                cell.dataset.y = i - 1;
                
                if (!isPlayerBoard) {
                    cell.addEventListener('click', () => handleCellClick(cell));
                }
            }
            
            container.appendChild(cell);
        }
    }
}

function updateGameBoard(boardId, gameState) {
    const board = document.getElementById(boardId);
    const cells = board.getElementsByClassName('cell');
    
    for (const cell of cells) {
        const x = parseInt(cell.dataset.x);
        const y = parseInt(cell.dataset.y);
        const isPlayerBoard = boardId === 'my-board';
        
        // Reset cell classes
        cell.className = 'cell';
        
        // Update cell state based on game data
        if (isPlayerBoard) {
            if (gameState.my_board[y][x] === 1) {
                cell.classList.add('ship');
            }
            if (gameState.opponent_board[y][x] === 2) {
                cell.classList.add('hit');
            }
            if (gameState.opponent_board[y][x] === 3) {
                cell.classList.add('miss');
            }
        } else {
            if (gameState.opponent_board[y][x] === 2) {
                cell.classList.add('hit');
            }
            if (gameState.opponent_board[y][x] === 3) {
                cell.classList.add('miss');
            }
        }
    }
}

function handleCellClick(cell) {
    if (!isMyTurn || cell.classList.contains('hit') || cell.classList.contains('miss')) {
        return;
    }

    const x = parseInt(cell.dataset.x);
    const y = parseInt(cell.dataset.y);

    cell.classList.add('attacking');
    
    makeMove(x, y)
        .then(response => {
            cell.classList.remove('attacking');
            if (response.success) {
                cell.classList.add(response.hit ? 'hit' : 'miss');
                loadGameState();
            }
        })
        .catch(error => {
            cell.classList.remove('attacking');
            console.error('Error making move:', error);
        });
}

function updateGameInfo(gameState) {
    const gameInfo = document.getElementById('game-info');
    const isPlayerTurn = gameState.current_turn === localStorage.getItem('user_id');
    
    gameInfo.innerHTML = `
        <div class="status">Game Status: ${gameState.status}</div>
        <div class="turn">Current Turn: ${isPlayerTurn ? 'Your Turn' : "Opponent's Turn"}</div>
        <div class="game-controls">
            <button onclick="leaveGame()">Leave Game</button>
            ${gameState.status === 'waiting' ? '<button onclick="startGame()">Start Game</button>' : ''}
        </div>
    `;
}

// Game State Management
function loadGameState() {
    if (!currentGame) return;
    
    fetch(`${API_URL}/games/${currentGame}/status`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => response.json())
    .then(gameState => {
        updateGameBoard('my-board', gameState.game);
        updateGameBoard('opponent-board', gameState.game);
        updateGameInfo(gameState.game);
        isMyTurn = gameState.game.current_turn === localStorage.getItem('user_id');
    })
    .catch(error => {
        console.error('Error updating game state:', error);
    });
}

async function loadGames() {
    try {
        const response = await apiRequest('/games');
        const gamesList = document.getElementById('games');
        gamesList.innerHTML = response.games.map(game => `
            <li class="game-item">
                <div>Name: ${game.name}</div>
                <div>Status: ${game.status}</div>
                <div>Created by: ${game.player1}</div>
                ${game.player2 ? `<div>Opponent: ${game.player2}</div>` : ''}
                ${game.status === 'waiting' ? 
                    `<button onclick="joinGame(${game.game_id})">Join Game</button>` : 
                    `<button onclick="viewGame(${game.game_id})">View Game</button>`
                }
            </li>
        `).join('');
    } catch (error) {
        console.error('Error loading games:', error);
        alert('Failed to load games');
    }
}

async function createGame() {
    try {
        const name = prompt('Enter game name:');
        if (!name) return;
        
        await apiRequest('/games', 'POST', { name });
        await loadGames();
    } catch (error) {
        console.error('Error creating game:', error);
        alert('Failed to create game');
    }
}

async function joinGame(gameId) {
    try {
        await apiRequest(`/games/${gameId}/join`, 'POST');
        currentGame = gameId;
        showGame();
    } catch (error) {
        console.error('Error joining game:', error);
        alert('Failed to join game');
    }
}

// Ship Placement Functions
function initializeShipPlacement() {
    const shipOptions = document.querySelectorAll('.ship-option');
    shipOptions.forEach(shipOption => {
        // Create ship preview
        const size = parseInt(shipOption.dataset.shipSize);
        const preview = shipOption.querySelector('.ship-preview');
        preview.innerHTML = '';
        for (let i = 0; i < size; i++) {
            const cell = document.createElement('div');
            cell.className = 'ship-preview-cell';
            preview.appendChild(cell);
        }

        // Add click event
        shipOption.addEventListener('click', () => selectShip(shipOption));
    });

    // Add keyboard listener for rotation
    document.addEventListener('keydown', (e) => {
        if (e.key.toLowerCase() === 'r') {
            toggleShipOrientation();
        }
    });

    // Add hover effect for ship placement
    const cells = document.querySelectorAll('#my-board .cell');
    cells.forEach(cell => {
        cell.addEventListener('mouseover', () => showShipPlacementPreview(cell));
        cell.addEventListener('mouseout', () => clearPlacementPreview());
        cell.addEventListener('click', () => placeShip(cell));
    });
}

function selectShip(shipOption) {
    // Clear previous selection
    document.querySelectorAll('.ship-option').forEach(option => {
        option.classList.remove('selected');
    });

    // Select new ship if it's not already placed
    if (!shipOption.classList.contains('placed')) {
        shipOption.classList.add('selected');
        selectedShip = {
            name: shipOption.dataset.shipName,
            size: parseInt(shipOption.dataset.shipSize)
        };
    }
}

function toggleShipOrientation() {
    if (selectedShip) {
        isHorizontal = !isHorizontal;
        const cells = document.querySelectorAll('#my-board .cell');
        cells.forEach(cell => {
            if (cell.matches(':hover')) {
                showShipPlacementPreview(cell);
            }
        });
    }
}

function clearPlacementPreview() {
    document.querySelectorAll('#my-board .cell').forEach(cell => {
        cell.classList.remove('placement-hover', 'placement-invalid');
    });
}

function showShipPlacementPreview(startCell) {
    if (!selectedShip) return;
    
    clearPlacementPreview();
    const cells = getShipCells(startCell, selectedShip.size);
    if (!cells) return;

    const isValid = isValidPlacement(cells);
    cells.forEach(cell => {
        cell.classList.add(isValid ? 'placement-hover' : 'placement-invalid');
    });
}

function getShipCells(startCell, size) {
    const cells = [];
    const board = document.getElementById('my-board');
    const startX = parseInt(startCell.dataset.x);
    const startY = parseInt(startCell.dataset.y);

    for (let i = 0; i < size; i++) {
        const x = isHorizontal ? startX + i : startX;
        const y = isHorizontal ? startY : startY + i;
        
        if (x > 9 || y > 9) return null;
        
        const cell = board.querySelector(`[data-x="${x}"][data-y="${y}"]`);
        if (!cell) return null;
        cells.push(cell);
    }

    return cells;
}

function isValidPlacement(cells) {
    if (!cells) return false;

    // Check if any cell is already occupied
    for (const cell of cells) {
        if (cell.classList.contains('ship-placed')) {
            return false;
        }

        // Check surrounding cells
        const x = parseInt(cell.dataset.x);
        const y = parseInt(cell.dataset.y);
        
        for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
                const adjacentCell = document.querySelector(`#my-board [data-x="${x + dx}"][data-y="${y + dy}"]`);
                if (adjacentCell && 
                    adjacentCell.classList.contains('ship-placed') && 
                    !cells.includes(adjacentCell)) {
                    return false;
                }
            }
        }
    }

    return true;
}

function placeShip(startCell) {
    if (!selectedShip) return;
    
    const cells = getShipCells(startCell, selectedShip.size);
    if (!cells || !isValidPlacement(cells)) return;

    // Place the ship
    cells.forEach(cell => {
        cell.classList.add('ship-placed');
    });

    // Mark ship as placed
    const shipOption = document.querySelector(`.ship-option[data-ship-name="${selectedShip.name}"]`);
    shipOption.classList.remove('selected');
    shipOption.classList.add('placed');

    // Store ship placement
    placedShips.set(selectedShip.name, {
        start: {
            x: parseInt(startCell.dataset.x),
            y: parseInt(startCell.dataset.y)
        },
        orientation: isHorizontal ? 'horizontal' : 'vertical'
    });

    // Clear selection
    selectedShip = null;
    clearPlacementPreview();
}

async function randomizeShips() {
    clearShips();
    
    Object.entries(SHIPS).forEach(([shipName, size]) => {
        let placed = false;
        while (!placed) {
            isHorizontal = Math.random() < 0.5;
            const x = Math.floor(Math.random() * 10);
            const y = Math.floor(Math.random() * 10);
            const startCell = document.querySelector(`#my-board .cell[data-x="${x}"][data-y="${y}"]`);
            
            if (startCell) {
                const cells = getShipCells(startCell, size);
                if (isValidPlacement(cells)) {
                    cells.forEach(cell => cell.classList.add('ship-placed'));
                    placedShips.set(shipName, {
                        start: {
                            x: parseInt(startCell.dataset.x),
                            y: parseInt(startCell.dataset.y)
                        },
                        orientation: isHorizontal ? 'horizontal' : 'vertical'
                    });
                    placed = true;
                }
            }
        }
    });
}

function clearShips() {
    document.querySelectorAll('#my-board .cell').forEach(cell => {
        cell.classList.remove('ship-placed');
    });
    placedShips.clear();
}

function confirmShipPlacement() {
    if (placedShips.size !== Object.keys(SHIPS).length) {
        alert('Please place all ships before confirming');
        return;
    }

    const shipPositions = Array.from(placedShips.entries()).map(([shipName, placement]) => ({
        name: shipName,
        positions: getShipCells(document.querySelector(`#my-board .cell[data-x="${placement.start.x}"][data-y="${placement.start.y}"]`), SHIPS[shipName]).map(cell => ({
            x: parseInt(cell.dataset.x),
            y: parseInt(cell.dataset.y)
        }))
    }));

    // Send ship positions to server
    fetch(`${API_URL}/games/${currentGame}/place-ships`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ ships: shipPositions })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text().then(text => {
            try {
                return text ? JSON.parse(text) : {};
            } catch (e) {
                console.error('Error parsing JSON:', text);
                throw new Error('Invalid JSON response from server');
            }
        });
    })
    .then(data => {
        if (data.success) {
            document.getElementById('ship-placement').classList.add('hidden');
            loadGameState();
        } else {
            throw new Error(data.message || 'Failed to place ships');
        }
    })
    .catch(error => {
        console.error('Error placing ships:', error);
        alert(`Failed to place ships: ${error.message}`);
    });
}

// Add these utility functions at the start of your script section
async function apiRequest(endpoint, method = 'GET', body = null) {
    try {
        const headers = {
            'Content-Type': 'application/json'
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_URL}${endpoint}`, {
            method,
            headers,
            body: body ? JSON.stringify(body) : null
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Request failed');
        }

        return await response.json();
    } catch (error) {
        alert(error.message);
        throw error;
    }
}

// Auth Functions
// Replace the existing login function
async function login() {
    try {
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        if (!username || !password) {
            alert('Please fill in all fields');
            return;
        }

        const data = await apiRequest('/auth/login', 'POST', {
            username,
            password
        });

        localStorage.setItem('token', data.token);
        localStorage.setItem('user_id', data.user_id);
        token = data.token;
        showGameList();
    } catch (error) {
        console.error('Login error:', error);
    }
}

async function register() {
    try {
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;

        if (!username || !password) {
            alert('Please fill in all fields');
            return;
        }

        if (password.length < 6) {
            alert('Password must be at least 6 characters');
            return;
        }

        const data = await apiRequest('/auth/register', 'POST', {
            username,
            password
        });

        localStorage.setItem('token', data.token);
        localStorage.setItem('user_id', data.user_id);
        token = data.token;
        showGameList();
    } catch (error) {
        console.error('Registration error:', error);
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    token = null;
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('game-list-screen').classList.add('hidden');
    document.getElementById('game-screen').classList.add('hidden');
}

// Game List Functions
async function showGameList() {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('game-screen').classList.add('hidden');
    document.getElementById('game-list-screen').classList.remove('hidden');
    await loadGames();
}

async function loadGames() {
    const response = await fetch(`${API_URL}/games`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.ok) {
        const data = await response.json();
        const gamesList = document.getElementById('games');
        gamesList.innerHTML = data.games.map(game => `
            <li class="game-item">
                ${game.name} (${game.status})
                <button onclick="joinGame(${game.game_id})">Join</button>
            </li>
        `).join('');
    }
}

async function createGame() {
    const name = prompt('Enter game name:');
    if (!name) return;

    try {
        const response = await fetch(`${API_URL}/games`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        });

        if (response.ok) {
            await loadGames();
            alert('Game created successfully!');
        } else {
            const errorData = await response.json();
            console.error('Error creating game:', errorData.message);
            alert(`Failed to create game: ${errorData.message || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Network error:', error);
        alert('Network error: Failed to connect to the server.');
    }
}

// Game Functions
async function joinGame(gameId) {
    const response = await fetch(`${API_URL}/games/${gameId}/join`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.ok) {
        currentGame = gameId;
        showGame();
    }
}

async function showGame() {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('game-list-screen').classList.add('hidden');
    document.getElementById('game-screen').classList.remove('hidden');
    
    // Create game boards
    createGameBoard('my-board', true);
    createGameBoard('opponent-board', false);
    
    // Show ship placement interface
    const shipPlacement = document.getElementById('ship-placement');
    shipPlacement.classList.remove('hidden');
    
    // Reset ship placement state
    selectedShip = null;
    isHorizontal = true;
    placedShips.clear();
    
    // Initialize ship placement interface
    initializeShipPlacement();
    
    // Start game state polling
    loadGameState();
    gameStateInterval = setInterval(loadGameState, 2000);
}

async function loadGameState() {
    const response = await fetch(`${API_URL}/games/${currentGame}/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.ok) {
        const game = await response.json();
        renderBoards(game.game);
        updateGameInfo(game.game);
        isMyTurn = game.game.current_turn === localStorage.getItem('user_id');
    }
}

function renderBoards(game) {
    const myBoard = document.getElementById('my-board');
    const opponentBoard = document.getElementById('opponent-board');
    
    myBoard.innerHTML = '';
    opponentBoard.innerHTML = '';
    
    for (let y = 0; y < 10; y++) {
        for (let x = 0; x < 10; x++) {
            const myCell = document.createElement('div');
            myCell.className = 'cell';
            if (game.my_board[y][x] === 1) myCell.classList.add('ship');
            if (game.my_board[y][x] === 2) myCell.classList.add('hit');
            if (game.my_board[y][x] === 3) myCell.classList.add('miss');
            myBoard.appendChild(myCell);

            const oppCell = document.createElement('div');
            oppCell.className = 'cell';
            oppCell.onclick = () => makeMove(x, y);
            if (game.opponent_board[y][x] === 2) oppCell.classList.add('hit');
            if (game.opponent_board[y][x] === 3) oppCell.classList.add('miss');
            opponentBoard.appendChild(oppCell);
        }
    }
}

async function makeMove(x, y) {
    if (!isMyTurn) return;
    
    const response = await fetch(`${API_URL}/games/${currentGame}/move`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ x, y })
    });
    
    if (response.ok) {
        const result = await response.json();
        if (result.game_over) {
            alert('Game Over! You won!');
            showGameList();
        } else {
            await loadGameState();
        }
    }
}

// Utilities
function toggleForms() {
    document.getElementById('login-form').classList.toggle('hidden');
    document.getElementById('register-form').classList.toggle('hidden');
}

// Initialize
if (token) {
    showGameList();
}