# Docker Deployment Guide

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.docker .env
   # Edit .env with your actual credentials
   ```

2. **Build and run:**
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Production Deployment

### Droplet/VPS Deployment

For deployment on Digital Ocean droplets or other VPS services:

1. **Configure environment for your server IP:**
```bash
# Edit .env with your droplet IP
nano .env

# Set these values:
VITE_API_URL=http://YOUR_DROPLET_IP:8000
CORS_ORIGINS=http://YOUR_DROPLET_IP,http://YOUR_DROPLET_IP:80,http://localhost
```

2. **Build and deploy:**
```bash
docker-compose up --build -d
```

3. **Access your application:**
- Frontend: http://YOUR_DROPLET_IP
- Backend API: http://YOUR_DROPLET_IP:8000

### 1. Environment Setup
```bash
# Create production environment file
cp .env.docker .env

# Edit with your production values:
nano .env
```

### 2. Build for Production
```bash
# Build images
docker-compose build

# Run in detached mode
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 3. SSL/HTTPS Setup (Optional)

For production with SSL, update `docker-compose.yml`:

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx-ssl.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - frontend
      - backend
```

### 4. Scaling
```bash
# Scale backend instances
docker-compose up -d --scale backend=3

# Scale with load balancer
docker-compose -f docker-compose.yml -f docker-compose.scale.yml up -d
```

## Development

### Running Individual Services
```bash
# Backend only
docker-compose up backend

# Frontend only  
docker-compose up frontend

# With rebuild
docker-compose up --build backend
```

### Debugging
```bash
# Enter backend container
docker-compose exec backend bash

# View Chrome processes
docker-compose exec backend ps aux | grep chrome

# Check logs
docker-compose logs backend | tail -100
```

### Volume Management
```bash
# View volumes
docker volume ls

# Backup data
docker run --rm -v gem-approval_bot_data:/data -v $(pwd):/backup alpine tar czf /backup/bot-data.tar.gz -C /data .

# Restore data
docker run --rm -v gem-approval_bot_data:/data -v $(pwd):/backup alpine tar xzf /backup/bot-data.tar.gz -C /data
```

## Troubleshooting

### Chrome Issues
```bash
# Check Chrome installation
docker-compose exec backend google-chrome --version

# Test headless Chrome
docker-compose exec backend google-chrome --headless --no-sandbox --dump-dom https://google.com
```

### Network Issues
```bash
# Check container networking
docker network ls
docker network inspect gem-approval-network

# Test backend from frontend
docker-compose exec frontend curl http://backend:8000/health
```

### Performance
```bash
# Monitor resources
docker stats

# Check container health
docker-compose ps
```

## Configuration

### Environment Variables
- `POST_URL`: Facebook group URL
- `FACEBOOK_USERNAME`: Your Facebook email
- `FACEBOOK_PASSWORD`: Your Facebook password
- `OPENAI_API_KEY`: OpenAI API key
- `VITE_API_URL`: Frontend API URL (set to your server IP, e.g., http://164.92.94.214:8000)
- `CORS_ORIGINS`: Allowed CORS origins (include your server IP)

### Volumes
- `./logs:/app/logs` - Persistent logging
- `./chrome_data:/app/chrome_data` - Chrome user data
- `./bot_data.db:/app/bot_data.db` - SQLite database

### Ports
- `80` - Frontend (Nginx)
- `8000` - Backend API
- Internal networking handles service communication

## Security Notes

1. **Never commit `.env` file** with real credentials
2. **Use strong passwords** for Facebook account
3. **Rotate API keys** regularly  
4. **Limit container privileges** (non-root user configured)
5. **Use secrets management** in production

## Monitoring

### Health Checks
- Backend: `curl http://localhost:8000/health`
- Frontend: `curl http://localhost/`

### Logs
```bash
# Real-time logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f backend

# Save logs to file
docker-compose logs > deployment.log
```