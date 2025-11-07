# Installation Guide

## Prerequisites

- Docker and docker-compose (recommended), OR
- Python 3.10+ with uv package manager
- 2GB+ RAM (for embedding model)
- 1GB+ disk space

## Option 1: Docker Deployment (Recommended)

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd PaperTrail
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate a secure secret key
openssl rand -hex 32

# Edit .env and set SECRET_KEY
nano .env
```

### Step 3: Start Application

```bash
# Build and start container
docker-compose up -d

# Check logs
docker-compose logs -f

# Access at http://localhost:8000
```

### Step 4: Create Admin User (Optional)

```bash
# Enter container
docker exec -it papertrail bash

# Create user
python -m src.cli create-user --username admin --email admin@example.com

# Exit container
exit
```

## Option 2: Manual Installation

### Step 1: Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Clone and Setup

```bash
git clone <repository-url>
cd PaperTrail

# Install dependencies
uv pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Set SECRET_KEY and other settings
```

### Step 3: Initialize Database

```bash
# Create data directory
mkdir -p data

# Initialize database
uv run python -m src.database init
```

### Step 4: Run Application

```bash
# Development server
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production server (with gunicorn)
uv run gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Production Deployment

### Using Nginx Reverse Proxy

1. Install nginx:
```bash
sudo apt install nginx
```

2. Create nginx config (`/etc/nginx/sites-available/papertrail`):
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. Enable site and restart nginx:
```bash
sudo ln -s /etc/nginx/sites-available/papertrail /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

4. Setup SSL with Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Systemd Service (for non-Docker deployment)

Create `/etc/systemd/system/papertrail.service`:

```ini
[Unit]
Description=PaperTrail Application
After=network.target

[Service]
Type=notify
User=your-user
Group=your-group
WorkingDirectory=/path/to/PaperTrail
Environment="PATH=/home/your-user/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/your-user/.cargo/bin/uv run gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable papertrail
sudo systemctl start papertrail
sudo systemctl status papertrail
```

## Database Backups

### SQLite Backup

```bash
# Stop application
docker-compose down  # or sudo systemctl stop papertrail

# Backup database
cp data/papertrail.db data/papertrail.db.backup-$(date +%Y%m%d)

# Restart application
docker-compose up -d  # or sudo systemctl start papertrail
```

### Automated Backups

Add to crontab (`crontab -e`):

```bash
# Daily backup at 2 AM
0 2 * * * cp /path/to/PaperTrail/data/papertrail.db /backups/papertrail-$(date +\%Y\%m\%d).db
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process or change PORT in .env
```

### Database Locked

```bash
# Stop all instances
docker-compose down
# or
sudo systemctl stop papertrail

# Remove lock files
rm data/*.db-journal data/*.db-wal data/*.db-shm

# Restart
docker-compose up -d
```

### Embedding Model Download Issues

```bash
# Manually download model
docker exec -it papertrail python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')"
```

### Permission Issues (Docker)

```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/
```

## Upgrading

### Docker

```bash
# Pull latest changes
git pull

# Rebuild container
docker-compose down
docker-compose build
docker-compose up -d
```

### Manual

```bash
# Pull latest changes
git pull

# Update dependencies
uv pip install -r requirements.txt

# Run migrations (if any)
uv run python -m src.database migrate

# Restart service
sudo systemctl restart papertrail
```

## Uninstallation

### Docker

```bash
# Stop and remove container
docker-compose down

# Remove images
docker rmi papertrail_papertrail

# Remove data (WARNING: This deletes all papers!)
rm -rf data/
```

### Manual

```bash
# Stop service
sudo systemctl stop papertrail
sudo systemctl disable papertrail

# Remove service file
sudo rm /etc/systemd/system/papertrail.service
sudo systemctl daemon-reload

# Remove application
rm -rf /path/to/PaperTrail
```
