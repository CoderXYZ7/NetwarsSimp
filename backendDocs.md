# NETWars API Documentation

## Overview
NETWars is a battleship-style game where players can place ships on a grid and engage in turn-based naval combat. This documentation covers the REST API endpoints available for game interaction.

## Base URL
```
/api/v1
```

## Authentication
Authentication details are not specified in the current documentation. Implementation-specific authentication headers should be included with all requests.

## Data Types

### Ship Types
The following ship types are available in the game:
- CA: Carrier
- SB: Submarine
- IC: Interceptor
- FR: Frigate
- IF: Inflatable

### Game Status
Games can have the following status values:
- `waiting`: Game is waiting for players to join
- `active`: Game is in progress
- `completed`: Game has ended

### Orientation Values
Ships can be placed in four orientations:
- `u`: Up
- `d`: Down
- `l`: Left
- `r`: Right

## Endpoints

### Get Self Game Status
Returns the current state of the game board from the perspective of the requesting player.

```
GET /game/status/self
```

#### Parameters
| Name      | Type    | Required | Description           |
|-----------|---------|----------|-----------------------|
| game_id   | integer | Yes      | Unique game identifier|
| player_id | integer | Yes      | Requesting player ID  |

#### Response
```json
{
    "game": {
        "game_id": integer,
        "player_id": integer,
        "status": string,
        "boardSelf": string
    }
}
```

#### Board Format
The `boardSelf` string represents the game board as a comma-separated string of 5-character sections:
- Characters 1-2: Cell type
  - Ship types (CA, SB, IC, FR, IF)
  - WT for water
- Character 3: Orientation (u, d, l, r) for ships, 0 for water
- Character 4: Distance from ship start (0-9) or 0 for water
- Character 5: Hit status (1 for hit, 0 for no hit)

Example:
```
"WT001,WT000,SBu20,WT000,WT000..."
```

### Get Opponent Game Status
Returns the opponent's board state with limited information about ship positions.

```
GET /game/status/opponent
```

#### Parameters
| Name      | Type    | Required | Description           |
|-----------|---------|----------|-----------------------|
| game_id   | integer | Yes      | Unique game identifier|
| player_id | integer | Yes      | Requesting player ID  |

#### Response
```json
{
    "game": {
        "game_id": integer,
        "player_id": integer,
        "status": string,
        "boardOpponent": string
    }
}
```

#### Board Format
The `boardOpponent` string is a comma-separated string of single characters:
- `0`: Non-hit cell
- `1`: Hit water cell
- `2`: Hit ship cell

### Attack Position
Executes an attack on a specific position on the opponent's board.

```
POST /game/attack
```

#### Request Body
```json
{
    "attack": {
        "x": integer,
        "y": integer,
        "game_id": integer,
        "attacker": integer,
        "receiver": integer
    }
}
```

#### Response
```json
{
    "attack": {
        "result": integer
    }
}
```

#### Result Codes
- `0`: Miss (hit water)
- `1`: Hit (hit ship)
- `2`: Sink (ship destroyed)

### Place Ship
Places a ship on the player's board at the specified position and orientation.

```
POST /game/place-ship
```

#### Request Body
```json
{
    "ship": {
        "game_id": integer,
        "player_id": integer,
        "type": string,
        "x": integer,
        "y": integer,
        "orientation": string
    }
}
```

#### Response
```json
{
    "placeShip": {
        "result": integer
    }
}
```

#### Result Codes
- `0`: Ship cannot be placed (invalid position or overlap)
- `1`: Ship successfully placed

## Error Handling
Standard HTTP status codes are used:
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 404: Resource Not Found
- 500: Server Error

Detailed error messages should be included in the response body when appropriate.

## Examples

### Example: Getting Self Board Status
```bash
GET /api/v1/game/status/self?game_id=123&player_id=456
```

Response:
```json
{
    "game": {
        "game_id": 123,
        "player_id": 456,
        "status": "active",
        "boardSelf": "WT001,WT000,SBu20,WT000,WT000,WT000,WT000,SBu11,WT001,WT000"
    }
}
```

### Example: Placing a Ship
```bash
POST /api/v1/game/place-ship

{
    "ship": {
        "game_id": 123,
        "player_id": 456,
        "type": "CA",
        "x": 3,
        "y": 4,
        "orientation": "u"
    }
}
```

Response:
```json
{
    "placeShip": {
        "result": 1
    }
}
```

## Rate Limiting
Implementation-specific rate limiting should be applied to prevent abuse.

## Database Schema Reference
The API interacts with the following database tables:
- games
- hits
- ships
- ships_type
- players

Refer to the database schema documentation for detailed information about table structures and relationships.