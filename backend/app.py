# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import jwt
import os
from functools import wraps
from datetime import datetime, timedelta
from flask import make_response
from datetime import timezone

debug = True

if debug:
    print("If you see this message, the backend is running in debug mode.", flush=True)

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key')

def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

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
        except:
            return jsonify({'message': 'Invalid token'}), 401
    return decorated

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
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
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                         (data['username'], hash))
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
        print(f"Registration error: {str(e)}")
        return jsonify({'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'message': 'Missing username or password'}), 400

        if debug:
            print(f"Login attempt: {data['username']}", flush=True)

        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE username = %s", (data['username'],))
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
        print(f"Login error: {str(e)}")
        return jsonify({'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

@app.route('/api/v1/games', methods=['GET'])
@token_required
def get_games():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT g.*, 
                   u1.username as player1_username, 
                   u2.username as player2_username
            FROM games g
            LEFT JOIN users u1 ON g.player1_id = u1.user_id
            LEFT JOIN users u2 ON g.player2_id = u2.user_id
            WHERE status != 'completed'
            AND (player1_id != %s OR player2_id IS NULL)
        """, (request.user_id,))
        
        games = cursor.fetchall()
        
        # Format the response
        formatted_games = []
        for game in games:
            formatted_games.append({
                'game_id': game['game_id'],
                'name': game['name'],
                'status': game['status'],
                'player1': game['player1_username'],
                'player2': game['player2_username'] if game['player2_username'] else None,
                'current_turn': game['current_turn'],
                'created_at': game['created_at'].isoformat() if game['created_at'] else None
            })

            if debug:
                print(formatted_games, flush=True)
        
        return jsonify({'games': formatted_games})
    except Exception as e:
        print(f"Error getting games: {str(e)}")
        return jsonify({'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

@app.route('/api/v1/games/<int:game_id>/join', methods=['POST'])
@token_required
def join_game(game_id):
    db, cursor = None, None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("CALL join_game(%s, %s)", (game_id, request.user_id))
        db.commit()
        
        print(f"User {request.user_id} successfully joined game {game_id}", flush=True)
        return jsonify({'message': 'Successfully joined game'}), 200

    except Exception as e:
        print(f"[ERROR] Failed to join game {game_id} for user {request.user_id}: {e}", flush=True)
        return jsonify({'message': 'Server error'}), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()
        
        # Debugging information for missing game or user_id issues
        if 'user_id' not in request or not game_id:
            print(f"[DEBUG] User or Game ID issue: user_id={getattr(request, 'user_id', None)}, game_id={game_id}", flush=True)


@app.route('/api/v1/games', methods=['POST'])
@token_required
def create_game():
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'message': 'Game name is required'}), 400

        db = get_db()
        if db is None:
            return jsonify({'message': 'Database connection error'}), 500

        cursor = db.cursor(dictionary=True)
        
        # Check that user_id exists
        user_id = getattr(request, 'user_id', None)
        if user_id is None:
            return jsonify({'message': 'User authentication failed'}), 401
        
        cursor.execute("CALL create_game(%s, %s)", (data['name'], user_id))
        result = cursor.fetchone()
        db.commit()

        if result is None:
            return jsonify({'message': 'Game creation failed'}), 500
        
        return jsonify({'game_id': result['game_id']}), 201
    except Exception as e:
        print(f"Error creating game: {str(e)}")
        return jsonify({'message': 'Server error'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()


@app.route('/api/v1/games/<int:game_id>/move', methods=['POST'])
@token_required
def make_move(game_id):
    data = request.get_json()
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM games WHERE game_id = %s", (game_id,))
    game = cursor.fetchone()
    
    if game['current_turn'] != request.user_id:
        return jsonify({'message': 'Not your turn'}), 403
        
    cursor.execute("CALL make_move(%s, %s, %s, %s)", 
                  (game_id, request.user_id, data['x'], data['y']))
    result = cursor.fetchone()
    db.commit()
    
    # Check if ship was destroyed
    ship_destroyed = False
    if result['hit']:
        cursor.execute("SELECT health FROM ships WHERE ship_id = %s", (result['ship_id'],))
        ship = cursor.fetchone()
        ship_destroyed = ship['health'] == 0
        
        # Check if game is over
        if ship_destroyed:
            cursor.execute("SELECT COUNT(*) as ships_left FROM ships WHERE game_id = %s AND health > 0", (game_id,))
            ships = cursor.fetchone()
            if ships['ships_left'] == 0:
                cursor.execute("UPDATE games SET status = 'completed', winner_id = %s WHERE game_id = %s",
                             (request.user_id, game_id))
                db.commit()
                return jsonify({'hit': True, 'ship_destroyed': True, 'game_over': True})
    
    return jsonify({
        'hit': result['hit'],
        'ship_destroyed': ship_destroyed,
        'game_over': False
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)