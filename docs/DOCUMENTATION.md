# NETWars Documentation

## Project Overview

NETWars is a modern implementation of the classic Battleship game, built as a web-based multiplayer strategy game. The project uses a microservices architecture with Docker containerization for easy deployment and scaling.

## Architecture

### System Components

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │ ←── │   Backend   │ ←── │  Database   │
│  (Nginx/JS) │     │   (Flask)   │     │  (MariaDB)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Technology Stack
- **Frontend**: HTML5, CSS3, JavaScript
- **Backend**: Python 3.x with Flask
- **Database**: MariaDB
- **Infrastructure**: Docker, Nginx

## Setup Guide

1. **Prerequisites**
   - Docker and Docker Compose
   - Git

2. **Installation**
   ```bash
   git clone [repository-url]
   cd NetwarsSimp
   docker-compose up --build
   ```

3. **Environment Variables**
   ```
   DB_HOST=nw-db
   DB_USER=your_user
   DB_PASSWORD=your_password
   DB_NAME=netwars
   SECRET_KEY=your_secret_key
   ```

## API Documentation

### Authentication

#### Register User
```
POST /api/register
Content-Type: application/json

{
    "username": "string",
    "password": "string"
}
```

#### Login
```
POST /api/login
Content-Type: application/json

{
    "username": "string",
    "password": "string"
}
```

### Game Management

#### Create Game
```
POST /api/games
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "string"
}
```

#### Join Game
```
POST /api/games/{game_id}/join
Authorization: Bearer <token>
```

#### Get Game Status
```
GET /api/games/{game_id}
Authorization: Bearer <token>
```

#### Make Move
```
POST /api/games/{game_id}/move
Authorization: Bearer <token>
Content-Type: application/json

{
    "x": integer,
    "y": integer
}
```

## Development Guide

### Local Development Setup
1. Clone repository
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Set up environment variables
4. Run development servers:
   ```bash
   # Backend
   python backend/app.py
   # Frontend
   cd frontend && python -m http.server
   ```

### Code Structure

```
NetwarsSimp/
├── backend/
│   ├── app.py          # Main application file
│   ├── Dockerfile      # Backend container configuration
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── js/
│   ├── Dockerfile
│   └── nginx.conf
├── db/
│   └── init.sql        # Database initialization
└── docker-compose.yml  # Container orchestration
```

## Testing

### Running Tests
```bash
# Backend tests
python -m pytest backend/tests

# Frontend tests
npm test
```

## Deployment

### Production Deployment
1. Update environment variables
2. Build containers:
   ```bash
   docker-compose -f docker-compose.prod.yml build
   ```
3. Deploy:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check environment variables
   - Verify network connectivity
   - Check database logs

2. **Authentication Problems**
   - Verify token expiration
   - Check secret key configuration
   - Review server logs

3. **Game State Issues**
   - Check database consistency
   - Review game logs
   - Verify move validation

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
