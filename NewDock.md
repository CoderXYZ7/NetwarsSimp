# DB new structure

games:

    - id (int)
    - name (text)
    - created_at (timestamp)
    - size (int) //size of the board
    - player1_id (int)
    - player2_id (int)
    - winner_id (int)
    - status (enum{waiting, active, completed})
    - number_of_turns (int)

hits:

    - game_id (int)
    - attacher_player_id (int)
    - reciver_player_id (int)
    - position x (int)
    - position y (int)
    - what_hit (enum{ship, water})

ships:

    - game_id (int)
    - player_id (int)
    - type (text) //this is a 2 letter string like so: "CA" for carrier
    - position x (int)
    - position y (int)
    - orientation (enum{u, d, l, r}) //up, down, left, right

ships_type:

    - type (text) //this is a 2 letter string like so: "CA" for carrier (CA carrier, SB submarine, IC interceptor, FR frigate, IF inflatable)
    - length (int)

players:

    - id (int)
    - username (text)
    - password (text)

---
## Database in DB markdown

```md

Table players {
    id          int [pk, increment]
    username    text [unique, not null]
    password    text [not null]
}

Table games {
    id              int [pk, increment]
    name            text [not null]
    created_at      timestamp [default: `CURRENT_TIMESTAMP`]
    size            int [not null]
    player1_id      int [ref: > players.id]
    player2_id      int [ref: > players.id]
    winner_id       int [ref: > players.id]
    status          enum('waiting', 'active', 'completed') [not null]
    number_of_turns int [default: 0]
}

Table hits {
    id          int [pk, increment]
    game_id     int [ref: > games.id]
    attacher_player_id   int [ref: > players.id]
    reciver_player_id   int [ref: > players.id]
    position_x  int [not null]
    position_y  int [not null]
    what_hit    enum('ship', 'water') [not null]
}

Table ships {
    id          int [pk, increment]
    game_id     int [ref: > games.id]
    player_id   int [ref: > players.id]
    type        text [not null]
    position_x  int [not null]
    position_y  int [not null]
    orientation enum('u', 'd', 'l', 'r') [not null]
}

Table ships_type {
    type    text [pk]
    length  int [not null]
}




Ref: "ships"."type" < "ships_type"."type"

```


# Backend new structure

## API functions

- gameStatusSelf:
    returns a json object structured like so:
    ```json
    {
        "game": {
            "id": ,
            "name": ,
            "status": ,
            "boardSelf": ,
        }
    }
    ```

    boardSelf is a string composed of 5 character sections divided by a comma. Each section is composed of:
     2 letter for the cell type (for example CA, SB.... if it is a ship or WT if it is water)
     1 letter for the orientation (u, d, l, r) if it is a ship or 0 if it is water
     1 if it is a ship: the distance from the start of the ship. if it is water it is 0
     1 letter for if it is a hit or not. if it is a hit it is a 1, if not it is a 0

    On the backend side the program will build a matrix of size nxn taking the information from the database.
    Once the matrix is built the program will populate the matrix with the ships from the database.
    After the ships are placed the program will add all the hits to the matrix.
    Then all the cells of the matrix will be converted to a string and returned to the frontend.

    so an example matrix for a 5x5 board will look like this:

    one submarine (long 3) has been placed on the board at position (3, 4) in the up direction.
    there are 4 hits on the board. (1,1);(3,3);(1,5);(4,3)

    ```
    [
        [WT001, WT000, WT000, WT000, WT000],
        [WT000, WT000, SBu20, WT000, WT000],
        [WT000, WT000, SBu11, WT001, WT000],
        [WT000, WT000, SBu00, WT000, WT000],
        [WT001, WT000, WT000, WT000, WT000],
    ]
    ```

    this matrix will be converted to a string like so:
    WT001,WT000,WT000,WT000,WT000,WT000,WT000,SBu20,WT000,WT000,WT000,WT000,SBu11,WT001,WT000,WT000,WT000,SBu00,WT000,WT000,WT001,WT000,WT000,WT000,WT000

- gameStatusOpponent:
    returns a json object structured like so:

    ```json
    {
        "game": {
            "id": ,
            "name": ,
            "status": ,
            "boardOpponent": ,
        }
    }
    ```

    boardOpponent is a string composed a 1 character section divided by a comma. The character is 0 if it is an non-hit cell, 1 if it is a hit water cell and 2 if it is a hit ship cell.

- attack:
    when a player attacks a cell on the oppnent's board, the api recieves a json object structured like so:

    ```json
    {
        "attack": {
            "x": ,
            "y": ,
            "game_id": ,
            "attacker": ,
            "receiver": ,
        }
    }
    ```

    the attack object will be added to the database (hits) and the attack will be executed on the board.

    the api returns a json object structured like so:

    ```json
    {
        "attack": {
            "result": , //0 if it is a miss, 1 if it is a hit, 2 if it is a sink
        }
    }
    ```

    to detect the sink the api will iterate over the ships on the matrix to check if the ship has been sunk.

- placeShip:
    when a player places a ship on the board, the api recieves a json object structured like so:   

    ```json
    {
        "ship": { 
            "game_id": ,
            "player_id": ,
            "type": ,
            "x": ,
            "y": ,
            "orientation": ,
        }
    }
    ```

    and if it is possible to place the ship without sovraposition with other ships, adds it to the database (ships) taking the leght from the (ships_type) database.

    the api returns a json object structured like so:

    ```json
    {
        "placeShip": {
            "result": , //0 if it cannot be placed an 1 if it can be placed
        }
    }
    ```

