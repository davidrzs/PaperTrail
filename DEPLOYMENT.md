# PaperTrail Deployment Guide

## Deploying to Dokploy

This guide covers deploying PaperTrail to Dokploy using Docker.

## Prerequisites

- Dokploy instance running
- GitHub repository connected to Dokploy
- Domain name (optional, but recommended for HTTPS)

## Quick Start

1. Create a new Docker application in Dokploy
2. Connect your GitHub repository
3. Configure environment variables (see below)
4. Set up volume mount for database persistence
5. Deploy

## Environment Variables

Set these in Dokploy's environment configuration:

### Required

```bash
SECRET_KEY=your-secret-key-here-change-this-to-something-random
DEBUG=false
```

Generate a secure `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Optional

```bash
DATABASE_URL=sqlite:///./data/papertrail.db  # Default, can be changed to PostgreSQL
ACCESS_TOKEN_EXPIRE_MINUTES=30               # Default: 30 minutes
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B   # Default model
```

## Volume Configuration

**Critical:** Mount a volume to persist your SQLite database.

In Dokploy, add a volume mount:
- **Container Path:** `/app/data`
- **Host Path:** Choose a persistent location on your server

Without this volume, your database will be lost on container restarts.

## Port Configuration

- **Container Port:** 8000
- **External Port:** Map to your desired port (typically 80 or 443 with reverse proxy)

## Security Hardening for Production

If deploying with HTTPS (recommended), update cookie settings to use `secure=True`:

### File: `src/routers/auth.py`

Find all `response.set_cookie()` calls and add `secure=True`:

```python
response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,
    secure=True,  # Add this line for HTTPS
    max_age=settings.access_token_expire_minutes * 60,
    samesite="lax"
)
```

This change appears in 3 places:
1. Login endpoint (~line 117)
2. Register endpoint (~line 70)
3. Logout endpoint (for clearing cookie)

## First Deployment

On first deployment, the container will:

1. Install dependencies via `uv`
2. Download embedding model (~2.5GB) - **this takes a few minutes**
3. Initialize SQLite database
4. Start the application on port 8000

**Note:** The first startup will be slower due to model download. Subsequent restarts are fast.

## Database Initialization

The database is automatically initialized on container startup via:
```bash
uv run python -m src.database init
```

This creates all tables and sets up the schema. No manual migration needed.

## Reverse Proxy Configuration

If using Dokploy's built-in Traefik or nginx:

1. Enable HTTPS via Let's Encrypt
2. Set your domain name
3. Traefik will automatically handle SSL termination

Example Traefik labels (usually auto-configured by Dokploy):
```yaml
traefik.enable=true
traefik.http.routers.papertrail.rule=Host(`your-domain.com`)
traefik.http.routers.papertrail.tls=true
traefik.http.routers.papertrail.tls.certresolver=letsencrypt
```

## Health Check

The application doesn't have a dedicated health endpoint, but you can check:

```bash
curl http://your-domain.com/
```

Should return the homepage HTML.

## Monitoring and Logs

View logs in Dokploy to monitor:
- Application startup
- Model download progress
- Request logs
- Error messages

## Scaling Considerations

### Current Setup (SQLite)
- Suitable for: Personal use, small teams (1-100 users)
- Limitations: Single-writer, file-based

### For Larger Scale
Consider migrating to PostgreSQL:

1. Set up PostgreSQL database
2. Update `DATABASE_URL` environment variable:
   ```bash
   DATABASE_URL=postgresql://user:password@host:5432/papertrail
   ```
3. Add PostgreSQL driver to `pyproject.toml`:
   ```toml
   dependencies = [
       ...
       "psycopg2-binary>=2.9.0",
   ]
   ```

## Backup Strategy

Since you're using SQLite with volume mount:

1. **Automated Backups:** Use Dokploy's volume backup feature or set up a cron job:
   ```bash
   # Backup script
   cp /path/to/volume/data/papertrail.db /backups/papertrail-$(date +%Y%m%d).db
   ```

2. **Manual Backup:** Download the database file from the volume:
   ```bash
   docker cp <container-id>:/app/data/papertrail.db ./backup.db
   ```

## Troubleshooting

### Container Fails to Start

Check logs for:
- Missing environment variables
- Volume mount permissions
- Port conflicts

### Database Not Persisting

Verify volume mount is configured correctly:
```bash
docker inspect <container-id> | grep Mounts -A 10
```

Should show `/app/data` mounted.

### Embedding Model Download Fails

The model downloads from HuggingFace. If it fails:
- Check internet connectivity
- Verify disk space (~3GB needed)
- Check logs for specific error

### Cookie/Auth Issues

If users can't log in after deployment:
- Verify `SECRET_KEY` is set
- Check if `secure=True` is set but HTTPS is not configured (causes cookie rejection)
- Check browser console for cookie errors

### Performance Issues

1. Check model is loaded (first request is slow, subsequent requests are fast)
2. Consider increasing container resources
3. Monitor disk I/O if using SQLite heavily

## Updating the Application

To deploy updates:

1. Push changes to your GitHub repository
2. In Dokploy, trigger a redeploy
3. Container will rebuild with latest code
4. Database schema migrations run automatically if needed

## Environment-Specific Configuration

### Development
```bash
DEBUG=true
SECRET_KEY=dev-secret-key-not-for-production
```

### Production
```bash
DEBUG=false
SECRET_KEY=<strong-random-key>
```

## Post-Deployment Checklist

- [ ] Environment variables set correctly
- [ ] Volume mounted for `/app/data`
- [ ] HTTPS enabled with valid SSL certificate
- [ ] `secure=True` added to cookie settings
- [ ] First user account created
- [ ] Backup strategy in place
- [ ] Domain DNS configured
- [ ] Monitoring/logs accessible

## Support

For issues specific to:
- **PaperTrail:** Check application logs
- **Dokploy:** Consult Dokploy documentation
- **Docker:** Verify Dockerfile and container configuration

## Additional Resources

- Application repository: Your GitHub repo
- Dokploy documentation: https://docs.dokploy.com
- FastAPI documentation: https://fastapi.tiangolo.com
