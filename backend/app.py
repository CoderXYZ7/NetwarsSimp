from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import jwt
import os
import random
from functools import wraps
from datetime import datetime, timedelta
from datetime import timezone

# Configuration and Setup
DEBUG = True
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key')

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Helper Functions
def get_db():
    """Create and return a database connection"""
    return mysql.connector.connect(**DB_CONFIG)

def log_debug(message):
    """Unified debug logging"""
    if DEBUG:
        print(f"[DEBUG] {message}", flush=True)

def log_error(message, error):
    """Unified error logging"""
    print(f"[ERROR] {message}: {str(error)}", flush=True)

# Authentication Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'message': 'Token missing'}), 401
        try:
            token = token.split('Bearer ')[1]
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user_id = data['user_id']
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        except Exception as e:
            log_error("Token validation error", e)
            return jsonify({'message': 'Server error'}), 500
    return decorated

# Game Management Functions
class GameManager:
    @staticmethod
    def get_player_role(game_id, user_id):
        """Determine user's role in a game"""
        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN player1_id = %s THEN 'player1'
                        WHEN player2_id = %s THEN 'player2'
                        ELSE NULL
                    END as role,
                    player1_id,
                    player2_id,
                    status,
                    current_turn,
                    name,
                    created_at
                FROM games 
                WHERE game_id = %s
            """, (user_id, user_id, game_id))
            
            return cursor.fetchone()
        except Exception as e:
            log_error("Error getting player role", e)
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'db' in locals():
                db.close()

    @staticmethod
    def create_ships(db, cursor, game_id, player_id):
        """Create ships for a player"""
        cursor.execute("SELECT * FROM ship_configs")
        ships = cursor.fetchall()

        for ship in ships:
            x_start = random.randint(0, 9 - ship['length'])
            y_start = random.randint(0, 9)
            orientation = random.choice(['horizontal', 'vertical'])

            cursor.execute("""
                INSERT INTO ships (game_id, player_id, ship_type, x_start, y_start, 
                                 orientation, length, health)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (game_id, player_id, ship['ship_type'], x_start, y_start, 
                 orientation, ship['length'], ship['length']))

    @staticmethod
    def create_game(name, player1_id):
        """Create a new game"""
        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)

            cursor.execute(
                "INSERT INTO games (name, player1_id, status) VALUES (%s, %s, 'waiting')",
                (name, player1_id)
            )
            game_id = cursor.lastrowid

            GameManager.create_ships(db, cursor, game_id, player1_id)
            db.commit()

            return game_id

        except Exception as e:
            log_error("Error creating game", e)
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'db' in locals():
                db.close()

    @staticmethod
    def join_game(game_id, player_id):
        """Join an existing game"""
        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)

            # Check current game state
            player_info = GameManager.get_player_role(game_id, player_id)
            
            if not player_info:
                return {'success': False, 'message': 'Game not found'}
                
            if player_info['status'] == 'completed':
                return {'success': False, 'message': 'Game is already completed'}
                
            if player_info['role']:
                return {'success': True, 'message': f'Already in game as {player_info["role"]}', 
                        'role': player_info['role']}

            # Join as player2 if possible
            if (player_info['player2_id'] is None and 
                player_info['player1_id'] != player_id and 
                player_info['status'] == 'waiting'):
                
                cursor.execute("""
                    UPDATE games 
                    SET player2_id = %s, 
                        status = 'active', 
                        current_turn = %s
                    WHERE game_id = %s
                """, (player_id, player_id, game_id))

                GameManager.create_ships(db, cursor, game_id, player_id)
                db.commit()

                return {'success': True, 'message': 'Successfully joined as player2', 
                        'role': 'player2'}
            
            return {'success': False, 'message': 'Cannot join this game'}

        except Exception as e:
            log_error("Error joining game", e)
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'db' in locals():
                db.close()

    @staticmethod
    def make_move(game_id, player_id, x, y):
        """Make a move in the game"""
        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)

            # Verify it's player's turn
            cursor.execute("""
                SELECT current_turn, player1_id, player2_id, status
                FROM games 
                WHERE game_id = %s
            """, (game_id,))
            game = cursor.fetchone()

            if not game:
                return {'success': False, 'message': 'Game not found'}

            if game['status'] != 'active':
                return {'success': False, 'message': 'Game is not active'}

            if game['current_turn'] != player_id:
                return {'success': False, 'message': 'Not your turn'}

            # Get opponent ID
            opponent_id = (game['player2_id'] if player_id == game['player1_id'] 
                         else game['player1_id'])

            # Check if move hits a ship
            cursor.execute("""
                SELECT ship_id
                FROM ships
                WHERE game_id = %s
                AND player_id = %s
                AND (
                    (orientation = 'horizontal' 
                     AND x_start <= %s 
                     AND x_start + length > %s
                     AND y_start = %s)
                    OR 
                    (orientation = 'vertical'
                     AND y_start <= %s
                     AND y_start + length > %s
                     AND x_start = %s)
                )
                LIMIT 1
            """, (game_id, opponent_id, x, x, y, y, y, x))
            
            ship = cursor.fetchone()
            is_hit = bool(ship)
            ship_id = ship['ship_id'] if ship else None

            # Record move
            cursor.execute("""
                INSERT INTO moves (game_id, player_id, x_coord, y_coord, is_hit, ship_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (game_id, player_id, x, y, is_hit, ship_id))

            result = {'hit': is_hit, 'ship_destroyed': False, 'game_over': False}

            # Update ship health if hit
            if is_hit:
                cursor.execute("""
                    UPDATE ships
                    SET health = health - 1
                    WHERE ship_id = %s
                    RETURNING health
                """, (ship_id,))
                ship = cursor.fetchone()
                
                if ship['health'] == 0:
                    result['ship_destroyed'] = True
                    
                    # Check if game is over
                    cursor.execute("""
                        SELECT COUNT(*) as ships_left 
                        FROM ships 
                        WHERE game_id = %s 
                        AND player_id = %s 
                        AND health > 0
                    """, (game_id, opponent_id))
                    ships = cursor.fetchone()
                    
                    if ships['ships_left'] == 0:
                        cursor.execute("""
                            UPDATE games 
                            SET status = 'completed', 
                                winner_id = %s 
                            WHERE game_id = %s
                        """, (player_id, game_id))
                        result['game_over'] = True

            # Switch turns if game not over
            if not result['game_over']:
                cursor.execute("""
                    UPDATE games
                    SET current_turn = %s
                    WHERE game_id = %s
                """, (opponent_id, game_id))

            db.commit()
            return {'success': True, **result}

        except Exception as e:
            log_error("Error making move", e)
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'db' in locals():
                db.close()

# API Routes
@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'message': 'Missing username or password'}), 400

        if len(data['password']) < 6:
            return jsonify({'message': 'Password must be at least 6 characters'}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        hash = generate_password_hash(data['password'])
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (data['username'], hash)
            )
            db.commit()
            user_id = cursor.lastrowid
            
            token = jwt.encode({
                'user_id': user_id,
                'exp': datetime.now(timezone.utc) + timedelta(days=1)
            }, SECRET_KEY)
            
            return jsonify({
                'token': token,
                'user_id': user_id,
                'username': data['username']
            }), 201

        except mysql.connector.IntegrityError:
            return jsonify({'message': 'Username already exists'}), 409

    except Exception as e:
        log_error("Registration error", e)
        return jsonify({'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'message': 'Missing username or password'}), 400

        log_debug(f"Login attempt: {data['username']}")

        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT * FROM users WHERE username = %s", 
            (data['username'],)
        )
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], data['password']):
            token = jwt.encode({
                'user_id': user['user_id'],
                'exp': datetime.now(timezone.utc) + timedelta(days=1)
            }, SECRET_KEY)
            
            return jsonify({
                'token': token,
                'user_id': user['user_id'],
                'username': user['username']
            })
        
        return jsonify({'message': 'Invalid credentials'}), 401

    except Exception as e:
        log_error("Login error", e)
        return jsonify({'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

@app.route('/api/v1/games', methods=['GET'])
@token_required
def get_games():
    """Get list of available games"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT g.*, 
                   u1.username as player1_username, 
                   u2.username as player2_username,
                   CASE 
                       WHEN g.player1_id = %s THEN 'player1'
                       WHEN g.player2_id = %s THEN 'player2'
                       ELSE NULL 
                   END as player_role
            FROM games g
            LEFT JOIN users u1 ON g.player1_id = u1.user_id
            LEFT JOIN users u2 ON g.player2_id = u2.user_id
            WHERE g.status != 'completed'
            AND (g.player1_id = %s OR g.player2_id = %s OR g.player2_id IS NULL)
            ORDER BY g.created_at DESC
        """, (request.user_id, request.user_id, request.user_id, request.user_id))
        
        games = cursor.fetchall()
        
        formatted_games = [{
            'game_id': game['game_id'],
            'name': game['name'],
            'status': game['status'],
            'player1': game['player1_username'],
            'player2': game['player2_username'],
            'current_turn': game['current_turn'],
            'player_role': game['player_role'],
            'created_at': game['created_at'].isoformat() if game['created_at'] else None,
            'can_join': (game['player2_id'] is None and 
                        game['player1_id'] != request.user_id and 
                        game['status'] == 'waiting')
        } for game in games]

        return jsonify({'games': formatted_games})

    except Exception as e:
        log_error("Error getting games", e)
        return jsonify({'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

@app.route('/api/v1/games', methods=['POST'])
@token_required
def create_game():
    """Create a new game"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'message': 'Game name is required'}), 400

        game_id = GameManager.create_game(data['name'], request.user_id)
        return jsonify({
            'message': 'Game created successfully',
            'game_id': game_id
        }), 201

    except Exception as e:
        log_error("Error creating game", e)
        return jsonify({'message': 'Server error'}), 500

@app.route('/api/v1/games/<int:game_id>/join', methods=['POST'])
@token_required
def join_game(game_id):
    """Join an existing game"""
    try:
        result = GameManager.join_game(game_id, request.user_id)
        
        if result['success']:
            log_debug(f"User {request.user_id} {result['message']}")
            return jsonify({
                'message': result['message'],
                'role': result['role']
            }), 200
        else:
            return jsonify({'message': result['message']}), 400

    except Exception as e:
        log_error(f"Failed to join game {game_id}", e)
        return jsonify({'message': 'Server error'}), 500

@app.route('/api/v1/games/<int:game_id>/status', methods=['GET'])
@token_required
def get_game_status(game_id):
    """Get current game status"""
    try:
        player_info = GameManager.get_player_role(game_id, request.user_id)
        
        if not player_info:
            return jsonify({'message': 'Game not found'}), 404
            
        # Get ships information for the player
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Get player's ships
        cursor.execute("""
            SELECT ship_id, ship_type, x_start, y_start, orientation, length, health
            FROM ships
            WHERE game_id = %s AND player_id = %s
        """, (game_id, request.user_id))
        ships = cursor.fetchall()
        
        # Get all moves in the game
        cursor.execute("""
            SELECT m.*, u.username as player_name
            FROM moves m
            JOIN users u ON m.player_id = u.user_id
            WHERE game_id = %s
            ORDER BY move_id
        """, (game_id,))
        moves = cursor.fetchall()
        
        print(moves, flush=True)
        print(ships, flush=True)
        print(jsonify({
            'status': player_info['status'],
            'role': player_info['role'],
            'is_your_turn': player_info['current_turn'] == request.user_id,
            'ships': [{
                'id': ship['ship_id'],
                'type': ship['ship_type'],
                'x': ship['x_start'],
                'y': ship['y_start'],
                'orientation': ship['orientation'],
                'length': ship['length'],
                'health': ship['health']
            } for ship in ships],
            'moves': [{
                'x': move['x_coord'],
                'y': move['y_coord'],
                'is_hit': move['is_hit'],
                'player': move['player_name'],
                'timestamp': move['created_at'].isoformat()
            } for move in moves]
        }), flush=True)

        return jsonify({
            'status': player_info['status'],
            'role': player_info['role'],
            'is_your_turn': player_info['current_turn'] == request.user_id,
            'ships': [{
                'id': ship['ship_id'],
                'type': ship['ship_type'],
                'x': ship['x_start'],
                'y': ship['y_start'],
                'orientation': ship['orientation'],
                'length': ship['length'],
                'health': ship['health']
            } for ship in ships],
            'moves': [{
                'x': move['x_coord'],
                'y': move['y_coord'],
                'is_hit': move['is_hit'],
                'player': move['player_name'],
                'timestamp': move['created_at'].isoformat()
            } for move in moves]
        })

    except Exception as e:
        log_error("Error getting game status", e)
        return jsonify({'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

@app.route('/api/v1/games/<int:game_id>/move', methods=['POST'])
@token_required
def make_move(game_id):
    """Make a move in the game"""
    try:
        data = request.get_json()
        if not data or 'x' not in data or 'y' not in data:
            return jsonify({'message': 'Coordinates required'}), 400
            
        if not (0 <= data['x'] <= 9 and 0 <= data['y'] <= 9):
            return jsonify({'message': 'Invalid coordinates'}), 400

        result = GameManager.make_move(game_id, request.user_id, data['x'], data['y'])
        
        if not result['success']:
            return jsonify({'message': result['message']}), 400
            
        response = {
            'hit': result['hit'],
            'ship_destroyed': result['ship_destroyed'],
            'game_over': result['game_over']
        }
        
        return jsonify(response)

    except Exception as e:
        log_error("Error making move", e)
        return jsonify({'message': 'Server error'}), 500

@app.route('/api/v1/games/<int:game_id>/board', methods=['GET'])
@token_required
def get_game_board(game_id):
    """Get the current state of the game board"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Get player role and game info
        player_info = GameManager.get_player_role(game_id, request.user_id)
        if not player_info:
            return jsonify({'message': 'Game not found'}), 404
            
        # Get opponent ID
        opponent_id = (player_info['player2_id'] 
                      if request.user_id == player_info['player1_id'] 
                      else player_info['player1_id'])
        
        # Get player's ships
        cursor.execute("""
            SELECT ship_id, ship_type, x_start, y_start, orientation, length, health
            FROM ships
            WHERE game_id = %s AND player_id = %s
        """, (game_id, request.user_id))
        my_ships = cursor.fetchall()
        
        # Get all moves
        cursor.execute("""
            SELECT player_id, x_coord, y_coord, is_hit, ship_id
            FROM moves
            WHERE game_id = %s
            ORDER BY move_id
        """, (game_id,))
        moves = cursor.fetchall()
        
        # Organize moves by player
        my_moves = []
        opponent_moves = []
        for move in moves:
            move_info = {
                'x': move['x_coord'],
                'y': move['y_coord'],
                'is_hit': move['is_hit']
            }
            if move['player_id'] == request.user_id:
                my_moves.append(move_info)
            else:
                opponent_moves.append(move_info)
        
        return jsonify({
            'my_board': {
                'ships': [{
                    'type': ship['ship_type'],
                    'x': ship['x_start'],
                    'y': ship['y_start'],
                    'orientation': ship['orientation'],
                    'length': ship['length'],
                    'health': ship['health']
                } for ship in my_ships],
                'opponent_moves': opponent_moves
            },
            'opponent_board': {
                'my_moves': my_moves
            },
            'game_status': player_info['status'],
            'is_my_turn': player_info['current_turn'] == request.user_id
        })

    except Exception as e:
        log_error("Error getting game board", e)
        return jsonify({'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    if DEBUG:
        print("Starting Battleship game server in DEBUG mode", flush=True)
    app.run(host='0.0.0.0', debug=DEBUG)