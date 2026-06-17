# WMS MCP Server Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.13+ (for local development)
- PostgreSQL 15+ (if not using Docker)
- Redis 7+ (if not using Docker)
- RabbitMQ 3+ (if not using Docker)

## Quick Start with Docker Compose

### 1. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your specific configuration:
- Database credentials
- Redis connection details
- RabbitMQ credentials
- API keys for external services
- Security settings

### 2. Start Services

```bash
docker-compose up -d
```

This will start:
- WMS MCP Server
- PostgreSQL database
- Redis cache
- RabbitMQ message queue
- Prometheus monitoring
- Grafana dashboards

### 3. Verify Deployment

Check service status:
```bash
docker-compose ps
```

Check logs:
```bash
docker-compose logs -f wms-mcp-server
```

Run health check:
```bash
./scripts/health_check.sh
```

### 4. Stop Services

```bash
docker-compose down
```

## Environment-Specific Deployments

### Development

Use `.env` for local development with default settings:
```bash
docker-compose -f docker-compose.yml up -d
```

### Staging

Use staging environment configuration:
```bash
cp .env.staging .env
docker-compose -f docker-compose.yml up -d
```

### Production

Use production environment configuration:
```bash
cp .env.production .env
docker-compose -f docker-compose.yml up -d
```

**Important:** Update production secrets before deployment!

## Manual Deployment (Without Docker)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Initialize Database

```bash
psql -U postgres -c "CREATE DATABASE wms;"
psql -U postgres -d wms -f scripts/init-db.sql
```

### 4. Start Redis

```bash
redis-server
```

### 5. Start RabbitMQ

```bash
rabbitmq-server
```

### 6. Run Server

```bash
python -m app.server
```

## Monitoring

### Prometheus

Access Prometheus at: http://localhost:9090

Default credentials: None (no authentication)

Key metrics to monitor:
- Tool execution rate
- Success/failure rates
- Response times
- Database connection pool usage
- Redis connection pool usage
- Memory usage

### Grafana

Access Grafana at: http://localhost:3000

Default credentials:
- Username: admin
- Password: admin (change on first login)

Pre-configured dashboards:
- WMS MCP Server Overview
- Tool Performance Metrics
- Database Performance
- System Resources

### Logs

Logs are stored in:
- Container: `/app/logs/wms-mcp-server.log`
- Host: `./logs/wms-mcp-server.log` (if mounted)

View logs in real-time:
```bash
docker-compose logs -f wms-mcp-server
```

## Scaling

### Horizontal Scaling

Scale the MCP server instances:

```bash
docker-compose up -d --scale wms-mcp-server=3
```

### Load Balancing

For production, use a load balancer (nginx, HAProxy, or cloud LB) in front of multiple MCP server instances.

## Security Considerations

### Production Deployment Checklist

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY
- [ ] Enable API key authentication
- [ ] Configure TLS/SSL for external connections
- [ ] Set up firewall rules
- [ ] Enable gRPC TLS for WMS Core integration
- [ ] Use secrets management (HashiCorp Vault, AWS Secrets Manager)
- [ ] Enable network encryption
- [ ] Configure rate limiting
- [ ] Set up log aggregation

### Backup Strategy

**Database Backups:**
```bash
# Backup
docker exec wms-postgres pg_dump -U wms wms > backup.sql

# Restore
docker exec -i wms-postgres psql -U wms wms < backup.sql
```

**Redis Backups:**
```bash
# Redis uses AOF persistence by default
# Backup AOF file
docker cp wms-redis:/data/appendonly.aof ./backup/
```

## Troubleshooting

### Server Won't Start

1. Check logs: `docker-compose logs wms-mcp-server`
2. Verify environment configuration
3. Check database connectivity
4. Verify Redis/RabbitMQ connectivity

### Database Connection Issues

1. Verify PostgreSQL is running: `docker-compose ps postgres`
2. Check database credentials in `.env`
3. Test connection: `docker exec -it wms-postgres psql -U wms -d wms`

### High Memory Usage

1. Check connection pool sizes
2. Review tool execution logs
3. Monitor with Grafana dashboards
4. Consider horizontal scaling

### Performance Issues

1. Check database query performance
2. Review Redis cache hit rates
3. Monitor tool execution times
4. Check for connection pool exhaustion

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy WMS MCP Server

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: docker build -t wms-mcp-server .
      
      - name: Deploy to production
        run: |
          docker-compose -f docker-compose.yml up -d
          ./scripts/health_check.sh
```

## Maintenance

### Regular Tasks

- **Daily:** Review error logs and metrics
- **Weekly:** Review performance trends
- **Monthly:** Update dependencies, review security patches
- **Quarterly:** Review and update scaling strategy

### Updates

Update dependencies:
```bash
pip install --upgrade -r requirements.txt
```

Rebuild and restart:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Support

For issues or questions:
1. Check logs first
2. Review monitoring dashboards
3. Consult this documentation
4. Check GitHub issues
