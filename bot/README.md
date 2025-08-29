# Bravo Bot API

This is a FastAPI backend that provides an HTTP API layer for controlling the Facebook comment bot.

## Features

- **Bot Control**: Start/stop the Facebook comment bot
- **Status Monitoring**: Real-time bot status and statistics
- **Comment Generation**: Test comment generation without running the full bot
- **Configuration Management**: View and update bot settings
- **Log Access**: Retrieve bot logs through the API
- **Health Monitoring**: API health checks

## Setup

### 1. Install Dependencies

```bash
cd bot
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the `bot` directory with your configuration:

```env
# Facebook Bot Configuration
CHROME_PROFILE=Default
POST_URL=https://www.facebook.com/groups/5440421919361046

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. Start the API Server

```bash
# Option 1: Using the startup script
python start_api.py

# Option 2: Direct uvicorn command
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Bot Control

- `POST /bot/start` - Start the bot
- `POST /bot/stop` - Stop the bot
- `GET /bot/status` - Get bot status

### Comment Generation

- `POST /bot/comment` - Generate a comment for a post

### Configuration

- `GET /config` - Get current configuration
- `PUT /config` - Update configuration

### Monitoring

- `GET /health` - Health check
- `GET /logs` - Get bot logs

## API Documentation

Once the server is running, you can view the interactive API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Frontend Integration

The React frontend includes a `BotControl` component that provides a user interface for:

- Starting/stopping the bot
- Monitoring bot status
- Testing comment generation
- Viewing bot statistics

## Usage Examples

### Start the bot

```bash
curl -X POST "http://localhost:8000/bot/start" \
  -H "Content-Type: application/json" \
  -d '{
    "post_url": "https://www.facebook.com/groups/5440421919361046",
    "max_scrolls": 20,
    "continuous_mode": true
  }'
```

### Get bot status

```bash
curl "http://localhost:8000/bot/status"
```

### Generate a comment

```bash
curl -X POST "http://localhost:8000/bot/comment" \
  -H "Content-Type: application/json" \
  -d '{
    "post_text": "ISO: Who makes this ring in stock? Need CAD or casting help."
  }'
```

## Development

### Running in Development Mode

The startup script includes auto-reload for development:

```bash
python start_api.py
```

### Testing the API

You can test the API endpoints using tools like:

- cURL
- Postman
- Insomnia
- The built-in Swagger UI at `/docs`

## Troubleshooting

### Common Issues

1. **Port already in use**: Change the port in `start_api.py` or kill the process using port 8000
2. **CORS errors**: Ensure the frontend origin is included in the CORS configuration
3. **Bot not starting**: Check the Chrome profile configuration and ensure Chrome is installed

### Logs

Bot logs are stored in the `logs/` directory and can be accessed through the API at `/logs`

## Security Notes

- The API currently runs on localhost only
- Consider adding authentication for production use
- Sensitive configuration should be stored in environment variables
- The API exposes bot control - ensure it's not accessible from the internet in production

## Next Steps

- Add authentication and authorization
- Implement rate limiting
- Add more detailed error handling
- Create a dashboard for bot analytics
- Add webhook support for real-time notifications
