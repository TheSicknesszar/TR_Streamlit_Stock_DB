# RefurbAdmin AI - Deployment Guide

Production deployment guide for RefurbAdmin AI.

## Prerequisites

- Docker 24+ and Docker Compose 2.20+
- PostgreSQL 16+
- Redis 7+
- Nginx (for production)
- SSL certificates (Let's Encrypt recommended)

## Quick Start

### 1. Clone and Configure

```bash
cd C:\Users\User\Documents\pricing_tool_est

# Copy environment template
copy deployment\.env.production .env
```

### 2. Generate Secrets

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY  
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Update `.env` with generated secrets.

### 3. Start Services

```bash
# Build and start all services
docker-compose -f deployment\docker-compose.yml up -d

# Check status
docker-compose ps
```

### 4. Initialize Database

```bash
docker-compose exec app python manage.py migrate
docker-compose exec app python manage.py create-admin
```

### 5. Verify Deployment

```bash
# Health check
curl http://localhost:8000/api/health

# Check logs
docker-compose logs -f app
```

## Production Deployment

### SSL Configuration

1. Obtain SSL certificates (Let's Encrypt):

```bash
certbot certonly --standalone -d refurbadmin.co.za -d www.refurbadmin.co.za
```

2. Copy certificates to deployment/ssl/:

```
deployment/ssl/
├── fullchain.pem
├── privkey.pem
└── chain.pem
```

### Docker Compose Production

```bash
# Start with production profile
docker-compose -f deployment\docker-compose.yml --profile backup up -d

# Include monitoring
docker-compose -f deployment\docker-compose.yml --profile backup --profile monitoring up -d
```

### Nginx Configuration

The included `deployment/nginx.conf` provides:
- SSL termination
- Rate limiting
- Gzip compression
- Security headers

## Backup Configuration

### Automated Backups

Backups run daily at 2 AM SAST:

```bash
# Enable backup service
docker-compose --profile backup up -d backup
```

### Manual Backup

```bash
docker-compose exec app python scripts/backup_database.py
```

### Restore from Backup

```bash
docker-compose exec app python scripts/restore_database.py /app/data/backups/backup_file.sql.gz
```

## Monitoring

### Prometheus Metrics

Access metrics at: `http://localhost:9090/metrics`

### Grafana Dashboard

Access Grafana at: `http://localhost:3000`
- Username: admin
- Password: (from .env)

### Health Endpoints

- `/api/health` - Full health check
- `/api/health/live` - Liveness probe
- `/api/health/ready` - Readiness probe

## Troubleshooting

### Database Connection Issues

```bash
# Check database status
docker-compose exec db pg_isready

# View database logs
docker-compose logs db
```

### Application Errors

```bash
# View app logs
docker-compose logs -f app

# Restart application
docker-compose restart app
```

### Permission Issues

```bash
# Fix permissions
docker-compose exec app chown -R refurbadmin:refurbadmin /app
```

## Performance Tuning

### Database

```sql
-- Analyze tables
ANALYZE;

-- Vacuum
VACUUM;
```

### Redis

Configure in `docker-compose.yml`:
```yaml
command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Application

Adjust workers in `docker-compose.yml`:
```yaml
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Security Checklist

- [ ] Change all default passwords
- [ ] Generate new SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Set up automated backups
- [ ] Configure rate limiting
- [ ] Review CORS settings
- [ ] Enable POPIA compliance features

## Support

- Documentation: docs/
- Issues: GitHub Issues
- Email: support@refurbadmin.co.za
- Phone: 0800 REFURB
