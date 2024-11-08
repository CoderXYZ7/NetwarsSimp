---

# NETWars Technical Document

## Overview
NETWars is a browser-based, turn-based strategy game inspired by classic Battleship gameplay, where players try to locate and destroy each other’s ships on a grid. The game emphasizes simplicity and randomization, with a retro pixel-art aesthetic.

---

## Technical Requirements

### Technology Stack
- **Frontend**: HTML, CSS, JavaScript, PHP
- **Backend**: Python (using Flask for API services)
- **Database**: MariaDB with SQL
- **Containerization**: Docker

---

## Gameplay

### Core Mechanics
1. **Turn-Based Play**:
   - Players take turns selecting grid coordinates to attack the opponent's board, attempting to locate and sink their ships.
   - Each turn, a player chooses one coordinate to “fire” upon, and the result (hit or miss) is displayed.

2. **Game Phases**:
   - **Preparation Phase**: Players place their ships on their respective grids. Both players confirm their placements to begin.
   - **Battle Phase**: Players take turns attacking coordinates on the enemy’s grid. Each turn reveals a hit or miss.
   - **Game End**: The game concludes when a player has no remaining ships.

3. **Ship Types and Placement**:
   - Each player has a set number of ships of various sizes, arranged on a grid.
   - Ships include a variety of lengths (e.g., 2-5 tiles long), which players can arrange horizontally or vertically.
   
4. **Game Interface**:
   - **Player’s Grid**: Shows the player’s ships and marks where the opponent has attacked.
   - **Opponent’s Grid**: Displays areas where the player has attacked and reveals hits or misses.

---

## Functional Components

### 1. Dockerized Services

#### Overview
Each component runs as an isolated Docker container to maintain modularity and streamline deployment.

#### Components

| Component  | Docker Service | Description                        | Technologies    |
|------------|----------------|------------------------------------|-----------------|
| **Backend**| `nw-backend`   | Manages game logic and API calls   | Python, SQL     |
| **Frontend**| `nw-frontend` | Presents UI to players             | HTML, CSS, JS, PHP |
| **Database**| `nw-db`       | Stores player and game data        | MariaDB, SQL    |

#### Docker-Compose Configuration Example

---

### 2. Backend (`nw-backend`)

- **Purpose**: Manages game logic, handles API requests, processes player actions, and coordinates with the database.
- **Technology**: Python (using Flask for the API)
- **Responsibilities**:
  - **User Authentication**: Handle registration, login, and user sessions.
  - **Game Session Management**: Create game sessions, store game state, and manage player roles (Player 1, Player 2).
  - **Gameplay Actions**:
    - Handle player moves (attacks) and track ship health.
    - Randomly assign the first turn.
  - **Endpoints**:
    - **POST /register**: Registers a new user with a hashed password.
    - **POST /login**: Authenticates users.
    - **POST /new_game**: Creates a new game session.
    - **POST /join_game**: Allows players to join a game.
    - **GET /game_state**: Retrieves current game state.
    - **POST /attack**: Processes an attack on the opponent’s grid and returns hit/miss feedback.
- **Error Handling**: Provides clear error messages and HTTP status codes for actions like invalid login or game access violations.

### 3. Frontend (`nw-frontend`)

- **Purpose**: Serves as the player interface for gameplay, user registration, and game management.
- **Technology**: HTML, CSS, JavaScript, PHP
- **Pages**:
  - **Login Page**: Allows user registration and login.
  - **Game Selection Page**: Lists active games and allows users to join or create games.
    - Displays game details and access options (Player 1, Player 2).
  - **Game Interface**: Displays:
    - **Player’s Grid**: Shows the player’s ships and areas targeted by the opponent.
    - **Opponent’s Grid**: Interactive grid where players select coordinates to attack.
    - **Attack Button**: Initiates an attack on the chosen coordinate.
    - **Turn Indicator**: Shows the current player’s turn.
- **Visual Style**:
  - Pixel-art styling for a retro aesthetic.
  - Responsive and dynamic updates using JavaScript for smooth game transitions.

### 4. Database (`nw-db`)

- **Purpose**: Stores persistent data, including user accounts, game sessions, and player moves.
- **Technology**: MariaDB, SQL
- **Schema**:
  - **Users Table**: Stores user data with `user_id`, `username`, `password_hash`.
  - **Games Table**: Contains game information with fields like `game_id`, `name`, `status`, `player_1`, `player_2`.
  - **GameState Table**: Holds game-specific data, such as `game_id`, `player_id`, `ship_positions`, `turn`, and `hits`.
- **Data Security**: Hash all passwords and enforce secure access patterns between frontend and backend.

---

## API and Data Handling

### Data Security and Flow
- **Backend-Controlled DB Access**: DB credentials remain in the backend, securing them from frontend exposure.
- **Data Flow**:
  - **Frontend-to-Backend**: All actions and updates are managed via API requests (e.g., login, game creation, in-game actions).
  - **Backend-to-Database**: Backend securely manages data requests and updates to the database.
  - **Backend-to-Frontend**: Backend responds with JSON data for real-time game updates.

---

## Technical Tasks Breakdown

1. **Backend Development**:
   - Implement Flask API endpoints for user authentication, game creation, and gameplay actions.
   - Integrate SQL queries to manage player data and game state.
   - Handle game logic, turn-based actions, and ship status.

2. **Frontend Development**:
   - Create the login, game selection, and game interfaces.
   - Use AJAX and JavaScript to manage real-time updates and smooth gameplay transitions.
   - Implement pixel-art-inspired CSS for consistent visual styling.

3. **Database Setup**:
   - Design and set up the database schema with tables for users, games, and game states.
   - Develop SQL queries for efficient data retrieval and storage.

4. **Dockerization**:
   - Set up Docker containers for the backend, frontend, and database.
   - Configure inter-service communication and test for seamless deployment.

---