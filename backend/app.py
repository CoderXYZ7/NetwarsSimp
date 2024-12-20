# app.py
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from functools import wraps
import os
import jwt
import datetime
import hashlib

app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_HOST'] = os.getenv('DB_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('DB_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD', 'rootpass')
app.config['MYSQL_DB'] = os.getenv('DB_NAME', 'netwars_db')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')

mysql = MySQL(app)

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            token = token.split(" ")[1]  # Remove "Bearer " prefix
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

# Helper functions
def build_board_matrix(game_id, player_id, size):
    # Initialize empty board
    board = [['WT000' for _ in range(size)] for _ in range(size)]
    
    # Get ships
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.position_x, s.position_y, s.type, s.orientation, st.length
        FROM ships s
        JOIN ships_type st ON s.type = st.type
        WHERE s.game_id = %s AND s.player_id = %s
    """, (game_id, player_id))
    ships = cur.fetchall()

    # Place ships on board
    for ship in ships:
        x, y, ship_type, orientation, length = ship
        for i in range(length):
            if orientation == 'u':
                board[y-i][x] = f"{ship_type}{orientation}{i}0"
            elif orientation == 'd':
                board[y+i][x] = f"{ship_type}{orientation}{i}0"
            elif orientation == 'l':
                board[y][x-i] = f"{ship_type}{orientation}{i}0"
            elif orientation == 'r':
                board[y][x+i] = f"{ship_type}{orientation}{i}0"

    # Get hits on this board
    cur.execute("""
        SELECT position_x, position_y, what_hit
        FROM hits
        WHERE game_id = %s AND reciver_player_id = %s
    """, (game_id, player_id))
    hits = cur.fetchall()

    # Mark hits on board
    for hit in hits:
        x, y, what_hit = hit
        cell = board[y][x]
        board[y][x] = cell[:-1] + '1'

    cur.close()
    return board

def check_ship_placement(game_id, player_id, ship_type, x, y, orientation, size):
    cur = mysql.connection.cursor()
    
    # Get ship length
    cur.execute("SELECT length FROM ships_type WHERE type = %s", (ship_type,))
    ship_length = cur.fetchone()[0]
    
    # Get existing ships
    cur.execute("""
        SELECT position_x, position_y, orientation, st.length
        FROM ships s
        JOIN ships_type st ON s.type = st.type
        WHERE game_id = %s AND player_id = %s
    """, (game_id, player_id))
    existing_ships = cur.fetchall()
    
    # Check board boundaries
    ship_coords = []
    if orientation == 'u':
        if y - ship_length + 1 < 0:
            return False
        ship_coords = [(x, y-i) for i in range(ship_length)]
    elif orientation == 'd':
        if y + ship_length > size:
            return False
        ship_coords = [(x, y+i) for i in range(ship_length)]
    elif orientation == 'l':
        if x - ship_length + 1 < 0:
            return False
        ship_coords = [(x-i, y) for i in range(ship_length)]
    elif orientation == 'r':
        if x + ship_length > size:
            return False
        ship_coords = [(x+i, y) for i in range(ship_length)]

    # Check collision with existing ships
    for existing in existing_ships:
        ex_x, ex_y, ex_orientation, ex_length = existing
        existing_coords = []
        if ex_orientation == 'u':
            existing_coords = [(ex_x, ex_y-i) for i in range(ex_length)]
        elif ex_orientation == 'd':
            existing_coords = [(ex_x, ex_y+i) for i in range(ex_length)]
        elif ex_orientation == 'l':
            existing_coords = [(ex_x-i, ex_y) for i in range(ex_length)]
        elif ex_orientation == 'r':
            existing_coords = [(ex_x+i, ex_y) for i in range(ex_length)]
        
        for coord in ship_coords:
            if coord in existing_coords:
                return False

    cur.close()
    return True

# Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Missing username or password'}), 400
    
    # Hash password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO players (username, password) VALUES (%s, %s)", 
                   (username, hashed_password))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'User registered successfully'}), 201
    except:
        cur.close()
        return jsonify({'message': 'Username already exists'}), 409

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM players WHERE username = %s AND password = %s", 
                (username, hashed_password))
    user = cur.fetchone()
    cur.close()
    
    if user:
        token = jwt.encode({
            'user_id': user[0],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }, app.config['JWT_SECRET_KEY'])
        return jsonify({'token': token})
    
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/game/status/self', methods=['GET'])
@token_required
def game_status_self(current_user_id):
    game_id = request.args.get('game_id', type=int)
    if not game_id:
        return jsonify({'message': 'Game ID is required'}), 400
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT size, status FROM games 
        WHERE id = %s AND (player1_id = %s OR player2_id = %s)
    """, (game_id, current_user_id, current_user_id))
    game = cur.fetchone()
    
    if not game:
        cur.close()
        return jsonify({'message': 'Game not found'}), 404
    
    size, status = game
    board = build_board_matrix(game_id, current_user_id, size)
    board_string = ','.join([''.join(row) for row in board])
    
    return jsonify({
        'game': {
            'game_id': game_id,
            'player_id': current_user_id,
            'status': status,
            'boardSelf': board_string
        }
    })

@app.route('/api/game/status/opponent', methods=['GET'])
@token_required
def game_status_opponent(current_user_id):
    game_id = request.args.get('game_id', type=int)
    if not game_id:
        return jsonify({'message': 'Game ID is required'}), 400
    
    cur = mysql.connection.cursor()
    # Get opponent ID
    cur.execute("""
        SELECT player1_id, player2_id, size, status 
        FROM games WHERE id = %s
    """, (game_id,))
    game = cur.fetchone()
    
    if not game:
        cur.close()
        return jsonify({'message': 'Game not found'}), 404
    
    player1_id, player2_id, size, status = game
    opponent_id = player2_id if current_user_id == player1_id else player1_id
    
    # Get all hits made by current player
    cur.execute("""
        SELECT position_x, position_y, what_hit
        FROM hits
        WHERE game_id = %s AND attacher_player_id = %s
    """, (game_id, current_user_id))
    hits = cur.fetchall()
    
    # Create opponent board view
    board = [['0' for _ in range(size)] for _ in range(size)]
    for hit in hits:
        x, y, what_hit = hit
        board[y][x] = '2' if what_hit == 'ship' else '1'
    
    board_string = ','.join([''.join(row) for row in board])
    
    return jsonify({
        'game': {
            'game_id': game_id,
            'player_id': opponent_id,
            'status': status,
            'boardOpponent': board_string
        }
    })

@app.route('/api/game/attack', methods=['POST'])
@token_required
def attack(current_user_id):
    data = request.get_json()
    attack_data = data.get('attack')
    
    if not attack_data:
        return jsonify({'message': 'Invalid request data'}), 400
    
    game_id = attack_data.get('game_id')
    x = attack_data.get('x')
    y = attack_data.get('y')
    receiver_id = attack_data.get('receiver')
    
    cur = mysql.connection.cursor()
    
    # Check if it's a valid game and player's turn
    cur.execute("""
        SELECT status, 
               CASE 
                   WHEN player1_id = %s THEN player2_id
                   WHEN player2_id = %s THEN player1_id
               END as opponent_id,
               number_of_turns
        FROM games 
        WHERE id = %s
    """, (current_user_id, current_user_id, game_id))
    game = cur.fetchone()
    
    if not game or game[0] != 'active':
        cur.close()
        return jsonify({'message': 'Invalid game or game not active'}), 400
    
    # Check if hit position has ship
    cur.execute("""
        SELECT s.id, s.type, s.orientation
        FROM ships s
        WHERE s.game_id = %s AND s.player_id = %s
        AND s.position_x = %s AND s.position_y = %s
    """, (game_id, receiver_id, x, y))
    ship = cur.fetchone()
    
    what_hit = 'ship' if ship else 'water'
    
    # Record the hit
    cur.execute("""
        INSERT INTO hits 
        (game_id, attacher_player_id, reciver_player_id, position_x, position_y, what_hit)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (game_id, current_user_id, receiver_id, x, y, what_hit))
    
    # Update game turns
    cur.execute("""
        UPDATE games 
        SET number_of_turns = number_of_turns + 1
        WHERE id = %s
    """, (game_id,))
    
    mysql.connection.commit()
    
    result = 0  # miss
    if ship:
        result = 1  # hit
        # Check if ship is sunk
        ship_id, ship_type, orientation = ship
        cur.execute("SELECT length FROM ships_type WHERE type = %s", (ship_type,))
        ship_length = cur.fetchone()[0]
        
        # Get all hits on this ship's positions
        ship_positions = []
        if orientation == 'u':
            ship_positions = [(x, y-i) for i in range(ship_length)]
        elif orientation == 'd':
            ship_positions = [(x, y+i) for i in range(ship_length)]
        elif orientation == 'l':
            ship_positions = [(x-i, y) for i in range(ship_length)]
        elif orientation == 'r':
            ship_positions = [(x+i, y) for i in range(ship_length)]
        
        position_list = []
        for pos in ship_positions:
            position_list.extend([pos[0], pos[1]])
        
        query = """
            SELECT COUNT(*) FROM hits 
            WHERE game_id = %s AND reciver_player_id = %s 
            AND what_hit = 'ship'
            AND (
        """
        for i in range(0, len(position_list), 2):
            if i > 0:
                query += " OR "
            query += f"(position_x = %s AND position_y = %s)"
        query += ")"
        
        cur.execute(query, (game_id, receiver_id, *position_list))
        hits_on_ship = cur.fetchone()[0]
        
        if hits_on_ship == ship_length:
            result = 2  # sink
    
    cur.close()
    return jsonify({'attack': {'result': result}})

@app.route('/api/game/place-ship', methods=['POST'])
@token_required
def place_ship(current_user_id):
    data = request.get_json()
    ship_data = data.get('ship')
    
    if not ship_data:
        return jsonify({'message': 'Invalid request data'}), 400
    
    game_id = ship_data.get('game_id')
    ship_type = ship_data.get('type')
    x = ship_data.get('x')
    y = ship_data.get('y')
    orientation = ship_data.get('orientation')
    
    cur = mysql.connection.cursor()
    
    # Verify game exists and is in setup phase
    cur.execute("""
        SELECT size, status FROM games 
        WHERE id = %s AND (player1_id = %s OR player2_id = %s)
        AND status = 'waiting'
    """, (game_id, current_user_id, current_user_id))
    game = cur.fetchone()
    
    # Continuing place_ship function
    if not game:
        cur.close()
        return jsonify({'message': 'Game not found or not in setup phase'}), 400
        
        size = game[0]
        
        # Check if ship placement is valid
        if not check_ship_placement(game_id, current_user_id, ship_type, x, y, orientation, size):
            cur.close()
            return jsonify({'placeShip': {'result': 0}})
        
        # Place the ship
        try:
            cur.execute("""
                INSERT INTO ships (game_id, player_id, type, position_x, position_y, orientation)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (game_id, current_user_id, ship_type, x, y, orientation))
            mysql.connection.commit()
            cur.close()
            return jsonify({'placeShip': {'result': 1}})
        except:
            cur.close()
            return jsonify({'placeShip': {'result': 0}})

@app.route('/api/game/create', methods=['POST'])
@token_required
def create_game(current_user_id):
    data = request.get_json()
    name = data.get('name')
    size = data.get('size', 10)  # Default size 10x10
    
    if not name:
        return jsonify({'message': 'Game name is required'}), 400
    
    if size < 5 or size > 20:
        return jsonify({'message': 'Invalid board size'}), 400
    
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO games (name, size, player1_id, status)
            VALUES (%s, %s, %s, 'waiting')
        """, (name, size, current_user_id))
        mysql.connection.commit()
        game_id = cur.lastrowid
        cur.close()
        return jsonify({'game_id': game_id}), 201
    except:
        cur.close()
        return jsonify({'message': 'Failed to create game'}), 500

@app.route('/api/game/join/<int:game_id>', methods=['POST'])
@token_required
def join_game(current_user_id, game_id):
    cur = mysql.connection.cursor()
    
    # Check if game exists and is waiting for players
    cur.execute("""
        SELECT player1_id, status 
        FROM games 
        WHERE id = %s AND status = 'waiting'
    """, (game_id,))
    game = cur.fetchone()
    
    if not game:
        cur.close()
        return jsonify({'message': 'Game not found or not available'}), 404
    
    if game[0] == current_user_id:
        cur.close()
        return jsonify({'message': 'Cannot join your own game'}), 400
    
    try:
        cur.execute("""
            UPDATE games 
            SET player2_id = %s
            WHERE id = %s AND status = 'waiting'
        """, (current_user_id, game_id))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Successfully joined game'}), 200
    except:
        cur.close()
        return jsonify({'message': 'Failed to join game'}), 500

@app.route('/api/game/start/<int:game_id>', methods=['POST'])
@token_required
def start_game(current_user_id, game_id):
    cur = mysql.connection.cursor()
    
    # Verify game exists and user is player1
    cur.execute("""
        SELECT player1_id, player2_id, 
               (SELECT COUNT(*) FROM ships WHERE game_id = %s AND player_id = player1_id) as p1_ships,
               (SELECT COUNT(*) FROM ships WHERE game_id = %s AND player_id = player2_id) as p2_ships
        FROM games 
        WHERE id = %s AND status = 'waiting'
    """, (game_id, game_id, game_id))
    game = cur.fetchone()
    
    if not game:
        cur.close()
        return jsonify({'message': 'Game not found or already started'}), 404
    
    player1_id, player2_id, p1_ships, p2_ships = game
    
    if player1_id != current_user_id:
        cur.close()
        return jsonify({'message': 'Only game creator can start the game'}), 403
    
    if not player2_id:
        cur.close()
        return jsonify({'message': 'Waiting for second player'}), 400
    
    if p1_ships == 0 or p2_ships == 0:
        cur.close()
        return jsonify({'message': 'All players must place their ships'}), 400
    
    try:
        cur.execute("""
            UPDATE games 
            SET status = 'active'
            WHERE id = %s
        """, (game_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Game started successfully'}), 200
    except:
        cur.close()
        return jsonify({'message': 'Failed to start game'}), 500

@app.route('/api/games/list', methods=['GET'])
@token_required
def list_games(current_user_id):
    status = request.args.get('status', 'all')
    
    cur = mysql.connection.cursor()
    
    if status == 'all':
        cur.execute("""
            SELECT g.id, g.name, g.status, g.created_at, 
                   p1.username as player1_name, p2.username as player2_name
            FROM games g
            LEFT JOIN players p1 ON g.player1_id = p1.id
            LEFT JOIN players p2 ON g.player2_id = p2.id
            WHERE g.player1_id = %s OR g.player2_id = %s
            ORDER BY g.created_at DESC
        """, (current_user_id, current_user_id))
    else:
        cur.execute("""
            SELECT g.id, g.name, g.status, g.created_at, 
                   p1.username as player1_name, p2.username as player2_name
            FROM games g
            LEFT JOIN players p1 ON g.player1_id = p1.id
            LEFT JOIN players p2 ON g.player2_id = p2.id
            WHERE (g.player1_id = %s OR g.player2_id = %s) AND g.status = %s
            ORDER BY g.created_at DESC
        """, (current_user_id, current_user_id, status))
    
    games = []
    for game in cur.fetchall():
        games.append({
            'id': game[0],
            'name': game[1],
            'status': game[2],
            'created_at': game[3].isoformat(),
            'player1_name': game[4],
            'player2_name': game[5]
        })
    
    cur.close()
    return jsonify({'games': games})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)