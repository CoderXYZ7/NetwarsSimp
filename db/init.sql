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

DELIMITER //

-- Trigger: after_game_complete
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