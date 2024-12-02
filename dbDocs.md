# NETWars Database Documentation

## Overview
The NETWars database is designed to support a multiplayer naval battle game. It consists of five main tables that manage players, games, ships, and combat interactions.

## Database Schema

### players
Stores user account information.

| Column   | Type         | Constraints                    | Description                    |
|----------|--------------|--------------------------------|--------------------------------|
| id       | INT          | PK, AUTO_INCREMENT            | Unique player identifier       |
| username | VARCHAR(50)  | UNIQUE, NOT NULL              | Player's username              |
| password | VARCHAR(255) | NOT NULL                      | Hashed password                |

**Constraints:**
- Username must be at least 3 characters long
- Username must be unique

### games
Manages active and completed games.

| Column          | Type                              | Constraints           | Description                        |
|-----------------|-----------------------------------|----------------------|------------------------------------|
| id              | INT                               | PK, AUTO_INCREMENT   | Unique game identifier             |
| name            | VARCHAR(100)                      | NOT NULL             | Game name/title                    |
| created_at      | TIMESTAMP                         | DEFAULT CURRENT_TIMESTAMP | Game creation time            |
| size            | INT                               | NOT NULL             | Board size (NxN)                   |
| player1_id      | INT                               | FK -> players.id     | First player's ID                  |
| player2_id      | INT                               | FK -> players.id     | Second player's ID                 |
| winner_id       | INT                               | FK -> players.id     | Winner's ID (if game completed)    |
| status          | ENUM('waiting','active','completed')| NOT NULL           | Current game state                 |
| number_of_turns | INT                               | DEFAULT 0            | Number of turns played             |

**Constraints:**
- Board size must be between 5 and 20
- Player1 and Player2 must be different players
- Cascading updates for player references

### ships_type
Defines the available ship types and their properties.

| Column  | Type       | Constraints     | Description              |
|---------|------------|----------------|--------------------------|
| type    | VARCHAR(2) | PK             | Ship type identifier     |
| length  | INT        | NOT NULL       | Ship length in grid units|

**Constraints:**
- Ship length must be between 1 and 6 units
- Default ship types:
  - CA (Carrier): 5 units
  - SB (Submarine): 3 units
  - IC (Interceptor): 3 units
  - FR (Frigate): 4 units
  - IF (Inflatable): 2 units

### ships
Tracks ship placements for each game.

| Column      | Type                    | Constraints         | Description                |
|-------------|-------------------------|--------------------|-----------------------------|
| id          | INT                     | PK, AUTO_INCREMENT | Unique ship placement ID   |
| game_id     | INT                     | FK -> games.id     | Associated game            |
| player_id   | INT                     | FK -> players.id   | Ship owner                 |
| type        | VARCHAR(2)              | FK -> ships_type.type | Ship type              |
| position_x  | INT                     | NOT NULL           | X coordinate on board      |
| position_y  | INT                     | NOT NULL           | Y coordinate on board      |
| orientation | ENUM('u','d','l','r')   | NOT NULL           | Ship orientation          |

**Constraints:**
- Positions must be non-negative
- Cascading deletes with game
- Ships must be of valid type

### hits
Records all attacks made during games.

| Column             | Type                  | Constraints       | Description              |
|-------------------|----------------------|------------------|--------------------------|
| id                | INT                  | PK, AUTO_INCREMENT | Unique hit identifier    |
| game_id           | INT                  | FK -> games.id   | Associated game          |
| attacher_player_id| INT                  | FK -> players.id | Attacking player         |
| reciver_player_id | INT                  | FK -> players.id | Defending player         |
| position_x        | INT                  | NOT NULL         | X coordinate of attack   |
| position_y        | INT                  | NOT NULL         | Y coordinate of attack   |
| what_hit          | ENUM('ship','water') | NOT NULL         | Attack result           |

**Constraints:**
- Positions must be non-negative
- Cascading deletes with game

## Indexes
The following indexes are created for query optimization:

1. `idx_games_status`: On games(status)
   - Optimizes queries filtering by game status
2. `idx_ships_game`: On ships(game_id)
   - Improves ship lookup performance for specific games
3. `idx_hits_game`: On hits(game_id)
   - Enhances hit history retrieval for specific games

## Relationships

1. Games -> Players:
   - Each game references up to three players (player1, player2, winner)
   - Soft deletion handling (SET NULL) for player references

2. Ships -> Games:
   - Ships belong to specific games
   - CASCADE deletion when game is deleted

3. Ships -> Ships_type:
   - Ships must reference valid ship types
   - RESTRICT deletion of ship types if in use

4. Hits -> Games:
   - Hits belong to specific games
   - CASCADE deletion when game is deleted

5. Hits/Ships -> Players:
   - Both reference player ownership
   - CASCADE deletion when player is deleted

## Best Practices

1. Always use transactions when modifying multiple tables
2. Validate board coordinates against game size before insertion
3. Verify player ownership and game status before allowing modifications
4. Use prepared statements to prevent SQL injection
5. Implement appropriate indexes for frequently used queries

## Common Queries

### Get Active Games
```sql
SELECT * FROM games WHERE status = 'active';
```

### Get Player's Ships
```sql
SELECT s.*, st.length 
FROM ships s 
JOIN ships_type st ON s.type = st.type 
WHERE s.game_id = ? AND s.player_id = ?;
```

### Get Game History
```sql
SELECT h.*, p1.username as attacker, p2.username as receiver 
FROM hits h 
JOIN players p1 ON h.attacher_player_id = p1.id 
JOIN players p2 ON h.reciver_player_id = p2.id 
WHERE h.game_id = ?;
```