const API_URL = '/api/v1';
        let token = localStorage.getItem('token');
        let currentGame = null;
        let isMyTurn = false;


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
            document.getElementById('game-list-screen').classList.add('hidden');
            document.getElementById('game-screen').classList.remove('hidden');
            await loadGameState();
        }

        async function loadGameState() {
            const response = await fetch(`${API_URL}/games/${currentGame}`, {
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