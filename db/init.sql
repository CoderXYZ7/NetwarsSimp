-- Create schema file: ./db/init.sql
CREATE DATABASE IF NOT EXISTS netwars_db;
USE netwars_db;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    games_played INT DEFAULT 0,
    games_won INT DEFAULT 0
);

CREATE TABLE games (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status ENUM('waiting', 'active', 'completed') DEFAULT 'waiting',
    player1_id INT,
    player2_id INT,
    current_turn INT,
    winner_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player1_id) REFERENCES users(user_id),
    FOREIGN KEY (player2_id) REFERENCES users(user_id),
    FOREIGN KEY (winner_id) REFERENCES users(user_id)
);

CREATE TABLE ship_configs (
    ship_type ENUM('carrier', 'battleship', 'cruiser', 'submarine', 'destroyer') PRIMARY KEY,
    length INT NOT NULL
);

CREATE TABLE ships (
    ship_id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT,
    player_id INT,
    ship_type ENUM('carrier', 'battleship', 'cruiser', 'submarine', 'destroyer'),
    x_start INT NOT NULL,
    y_start INT NOT NULL,
    orientation ENUM('horizontal', 'vertical'),
    length INT NOT NULL,
    health INT NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES users(user_id),
    FOREIGN KEY (ship_type) REFERENCES ship_configs(ship_type)
);

CREATE TABLE moves (
    move_id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT,
    player_id INT,
    x_coord INT NOT NULL,
    y_coord INT NOT NULL,
    is_hit BOOLEAN,
    ship_id INT,
    move_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (player_id) REFERENCES users(user_id),
    FOREIGN KEY (ship_id) REFERENCES ships(ship_id)
);

-- Add indexes for performance
CREATE INDEX idx_games_status ON games(status);
CREATE INDEX idx_moves_game ON moves(game_id);
CREATE INDEX idx_ships_game ON ships(game_id);

-- Insert ship configuration
INSERT INTO ship_configs (ship_type, length) VALUES
    ('carrier', 5),
    ('battleship', 4),
    ('cruiser', 3),
    ('submarine', 3),
    ('destroyer', 2);

-- Add procedures for game actions
DELIMITER //

CREATE PROCEDURE create_game(
    IN p_name VARCHAR(100),
    IN p_player1_id INT
)
BEGIN
    DECLARE v_game_id INT;

    -- Create the game
    INSERT INTO games (name, player1_id, status)
    VALUES (p_name, p_player1_id, 'waiting');

    -- Debug check: Confirm game ID
    SET v_game_id = LAST_INSERT_ID();
    IF v_game_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Failed to retrieve game ID';
    END IF;

    -- Create ships for player 1
    INSERT INTO ships (game_id, player_id, ship_type, x_start, y_start, orientation, length, health)
    SELECT 
        v_game_id,
        p_player1_id,
        ship_type,
        FLOOR(RAND() * (10 - length)), -- Random starting position
        FLOOR(RAND() * 10),
        IF(RAND() > 0.5, 'horizontal', 'vertical'),
        length,
        length
    FROM ship_configs;

    -- Final return: Game ID
    SELECT v_game_id as game_id;
END//


CREATE PROCEDURE join_game(
    IN p_game_id INT,
    IN p_player_id INT
)
BEGIN
    -- Join the game and set it to active
    UPDATE games 
    SET player2_id = p_player_id,
        status = 'active',
        current_turn = p_player_id
    WHERE game_id = p_game_id
    AND status = 'waiting'
    AND player1_id != p_player_id;
    
    -- Create ships for player 2
    INSERT INTO ships (game_id, player_id, ship_type, x_start, y_start, orientation, length, health)
    SELECT 
        p_game_id,
        p_player_id,
        ship_type,
        FLOOR(RAND() * (10 - length)), -- Random starting position
        FLOOR(RAND() * 10),
        IF(RAND() > 0.5, 'horizontal', 'vertical'),
        length,
        length
    FROM ship_configs;
END//

CREATE PROCEDURE make_move(
    IN p_game_id INT,
    IN p_player_id INT,
    IN p_x INT,
    IN p_y INT
)
BEGIN
    DECLARE v_ship_id INT;
    DECLARE v_is_hit BOOLEAN;
    DECLARE v_opponent_id INT;
    
    -- Get opponent ID
    SELECT IF(player1_id = p_player_id, player2_id, player1_id)
    INTO v_opponent_id
    FROM games
    WHERE game_id = p_game_id;
    
    -- Check if hits any ship
    SELECT ship_id INTO v_ship_id
    FROM ships
    WHERE game_id = p_game_id
    AND player_id = v_opponent_id
    AND ((orientation = 'horizontal' 
          AND x_start <= p_x 
          AND x_start + length > p_x
          AND y_start = p_y)
    OR (orientation = 'vertical'
        AND y_start <= p_y
        AND y_start + length > p_y
        AND x_start = p_x))
    LIMIT 1;
    
    SET v_is_hit = v_ship_id IS NOT NULL;
    
    -- Record move
    INSERT INTO moves (game_id, player_id, x_coord, y_coord, is_hit, ship_id)
    VALUES (p_game_id, p_player_id, p_x, p_y, v_is_hit, v_ship_id);
    
    -- Update ship health if hit
    IF v_is_hit THEN
        UPDATE ships
        SET health = health - 1
        WHERE ship_id = v_ship_id;
    END IF;
    
    -- Switch turns
    UPDATE games
    SET current_turn = v_opponent_id
    WHERE game_id = p_game_id;
    
    -- Return result
    SELECT v_is_hit as hit, v_ship_id as ship_id;
END//

DELIMITER ;

-- Add trigger for game statistics
DELIMITER //

CREATE TRIGGER after_game_complete
AFTER UPDATE ON games
FOR EACH ROW
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        -- Update games_played for both players
        UPDATE users 
        SET games_played = games_played + 1
        WHERE user_id IN (NEW.player1_id, NEW.player2_id);
        
        -- Update games_won for winner
        IF NEW.winner_id IS NOT NULL THEN
            UPDATE users
            SET games_won = games_won + 1
            WHERE user_id = NEW.winner_id;
        END IF;
    END IF;
END//

DELIMITER ;