-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS netwars_db;
USE netwars_db;

-- Drop tables if they exist to ensure clean initialization
DROP TABLE IF EXISTS hits;
DROP TABLE IF EXISTS ships;
DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS ships_type;

-- Create players table
CREATE TABLE players (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    CONSTRAINT chk_username_length CHECK (LENGTH(username) >= 3)
);

-- Create games table
CREATE TABLE games (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    size INT NOT NULL,
    player1_id INT,
    player2_id INT,
    winner_id INT,
    status ENUM('waiting', 'active', 'completed') NOT NULL DEFAULT 'waiting',
    number_of_turns INT DEFAULT 0,
    FOREIGN KEY (player1_id) REFERENCES players(id) ON DELETE SET NULL,
    FOREIGN KEY (player2_id) REFERENCES players(id) ON DELETE SET NULL,
    FOREIGN KEY (winner_id) REFERENCES players(id) ON DELETE SET NULL,
    CONSTRAINT chk_board_size CHECK (size >= 5 AND size <= 20),
    CONSTRAINT chk_different_players CHECK (player1_id != player2_id)
);

-- Create ships_type table
CREATE TABLE ships_type (
    type VARCHAR(2) PRIMARY KEY,
    length INT NOT NULL,
    CONSTRAINT chk_ship_length CHECK (length > 0 AND length <= 6)
);

-- Create ships table
CREATE TABLE ships (
    id INT PRIMARY KEY AUTO_INCREMENT,
    game_id INT NOT NULL,
    player_id INT NOT NULL,
    type VARCHAR(2) NOT NULL,
    position_x INT NOT NULL,
    position_y INT NOT NULL,
    orientation ENUM('u', 'd', 'l', 'r') NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (type) REFERENCES ships_type(type) ON DELETE RESTRICT,
    CONSTRAINT chk_position CHECK (position_x >= 0 AND position_y >= 0)
);

-- Create hits table
CREATE TABLE hits (
    id INT PRIMARY KEY AUTO_INCREMENT,
    game_id INT NOT NULL,
    attacher_player_id INT NOT NULL,
    reciver_player_id INT NOT NULL,
    position_x INT NOT NULL,
    position_y INT NOT NULL,
    what_hit ENUM('ship', 'water') NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    FOREIGN KEY (attacher_player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (reciver_player_id) REFERENCES players(id) ON DELETE CASCADE,
    CONSTRAINT chk_hit_position CHECK (position_x >= 0 AND position_y >= 0)
);

-- Insert default ship types
INSERT INTO ships_type (type, length) VALUES
    ('CA', 5),  -- Carrier
    ('SB', 3),  -- Submarine
    ('IC', 3),  -- Interceptor
    ('FR', 4),  -- Frigate
    ('IF', 2);  -- Inflatable

-- Create indexes for better query performance
CREATE INDEX idx_games_status ON games(status);
CREATE INDEX idx_ships_game ON ships(game_id);
CREATE INDEX idx_hits_game ON hits(game_id);