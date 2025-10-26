# Reverse Proxy Integration Guide

This guide explains how to integrate Hermes with existing reverse proxy setups or customize the default Caddy configuration.

## Overview

Hermes provides a flexible deployment architecture:
- **Default**: Includes Caddy reverse proxy (see `docker-compose.yml`)
- **Custom**: Easy integration with existing reverse proxies (Traefik, nginx, etc.)

## Architecture

```
┌─────────────────┐
│  Reverse Proxy  │ ← Your choice (Caddy, Traefik, nginx, etc.)
└────────┬────────┘
         │
    ┌────┴─────────────────┬──────────────┐
    │                      │              │
┌───▼────┐          ┌──────▼─────┐   ┌───▼─────┐
│ Static │          │    API     │   │  Redis  │
│ Files  │          │ (FastAPI)  │   │         │
│ (app)  │          └────────────┘   └─────────┘
└────────┘
```

## Default Setup (Caddy)

The default `docker-compose.yml` uses Caddy. No additional configuration needed!

```bash
docker compose up -d
# Access at http://localhost:3000
```

### Customizing Caddyfile

Edit the `Caddyfile` in the project root:

```caddy
# Production with automatic HTTPS
hermes.yourdomain.com {
    tls admin@yourdomain.com
    
    handle /api/* {
        reverse_proxy api:8000
    }
    
    handle {
        root * /app
        try_files {path} /index.html
        file_server
    }
}
```

Then restart: `docker compose restart proxy`

## Integration with Existing Setups

### Option 1: Replace Caddy with Your Proxy

1. **Edit docker-compose.yml** - Remove the `proxy` service
2. **Connect to your network** - Add your proxy network to services
3. **Configure your proxy** - Point to the services (see examples below)

Example modification to `docker-compose.yml`:

```yaml
services:
  app:
    # ... existing config ...
    networks:
      - hermes-network
      - your-proxy-network  # Add your proxy network

  api:
    # ... existing config ...
    networks:
      - hermes-network
      - your-proxy-network  # Add your proxy network

networks:
  hermes-network:
    driver: bridge
  your-proxy-network:
    external: true  # Your existing proxy network
```

### Option 2: Keep Caddy, Proxy to Caddy

Keep the default setup and point your main proxy to the Caddy container on port 3000.

---

## Reverse Proxy Examples

### Traefik

Add labels to your services in `docker-compose.yml`:

```yaml
services:
  proxy:
    # Remove this service or keep it for internal routing
    
  app:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes.rule=Host(`hermes.yourdomain.com`)"
      - "traefik.http.routers.hermes.entrypoints=websecure"
      - "traefik.http.routers.hermes.tls.certresolver=letsencrypt"
      # Route to Caddy if keeping it, otherwise serve static files
      - "traefik.http.services.hermes.loadbalancer.server.port=80"
    networks:
      - traefik-network
      - hermes-network
```

**Or serve files directly without Caddy:**

```yaml
services:
  api:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes-api.rule=Host(`hermes.yourdomain.com`) && PathPrefix(`/api`)"
      - "traefik.http.services.hermes-api.loadbalancer.server.port=8000"
    networks:
      - traefik-network

  # Use a simple nginx to serve static files
  app:
    image: nginx:alpine
    volumes:
      - app_dist:/usr/share/nginx/html:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes-app.rule=Host(`hermes.yourdomain.com`)"
      - "traefik.http.services.hermes-app.loadbalancer.server.port=80"
```

### nginx Proxy Manager

1. In nginx Proxy Manager web UI:
   - Add **Proxy Host**
   - **Domain**: `hermes.yourdomain.com`
   - **Forward Hostname/IP**: `hermes-proxy` (or container IP)
   - **Forward Port**: `80`
   - Enable **Websockets Support**
   - Add **SSL Certificate** (Let's Encrypt)

2. If not using Caddy, point directly to services:
   - Frontend: `hermes-app:80` (if using nginx to serve)
   - API: `hermes-api:8000`

### nginx (Manual Configuration)

```nginx
upstream hermes_api {
    server api:8000;
}

server {
    listen 80;
    server_name hermes.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name hermes.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API proxy
    location /api/ {
        proxy_pass http://hermes_api/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Frontend static files
    location / {
        # Option 1: Proxy to Caddy
        proxy_pass http://hermes-proxy:80;
        
        # Option 2: Serve directly from volume
        # root /var/lib/docker/volumes/hermes_app_dist/_data;
        # try_files $uri $uri/ /index.html;
    }
}
```

### Apache

```apache
<VirtualHost *:80>
    ServerName hermes.yourdomain.com
    Redirect permanent / https://hermes.yourdomain.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName hermes.yourdomain.com

    SSLEngine on
    SSLCertificateFile /path/to/cert.pem
    SSLCertificateKeyFile /path/to/key.pem

    # API proxy
    ProxyPass /api/ http://api:8000/api/
    ProxyPassReverse /api/ http://api:8000/api/

    # Frontend proxy to Caddy
    ProxyPass / http://hermes-proxy:80/
    ProxyPassReverse / http://hermes-proxy:80/

    # WebSocket support
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/api/(.*) ws://api:8000/api/$1 [P,L]
</VirtualHost>
```

### Cloudflare Tunnel

```yaml
# cloudflared config.yml
tunnel: <your-tunnel-id>
credentials-file: /path/to/credentials.json

ingress:
  - hostname: hermes.yourdomain.com
    service: http://hermes-proxy:80
  - service: http_status:404
```

---

## Network Configuration

### Connecting to Existing Networks

If you have an existing Docker network for your reverse proxy:

```yaml
networks:
  hermes-network:
    driver: bridge
    internal: true  # Isolate internal communication
  
  proxy-network:
    name: your-existing-network
    external: true

services:
  proxy:
    networks:
      - hermes-network
      - proxy-network
  
  app:
    networks:
      - hermes-network
      - proxy-network  # Only if direct access needed
```

### Port Exposure

**Production (with reverse proxy):**
```yaml
services:
  app:
    # NO ports: section - accessed via reverse proxy
    
  api:
    # NO ports: section - accessed via reverse proxy
```

**Development (direct access):**
```yaml
services:
  app:
    ports:
      - "5173:5173"  # Vite dev server
  
  api:
    ports:
      - "8000:8000"  # Direct API access
```

---

## Static File Serving

### Option 1: Via Reverse Proxy Volume Mount

The app container creates static files in a Docker volume. Your reverse proxy mounts this volume:

```yaml
services:
  your-proxy:
    volumes:
      - app_dist:/path/to/serve:ro

volumes:
  app_dist:  # Shared volume
```

### Option 2: Direct nginx Container

Replace the busybox app container with nginx:

```yaml
services:
  app:
    image: nginx:alpine
    volumes:
      - app_dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
```

### Option 3: Build-time Copy

Export static files during build and serve from your own infrastructure:

```bash
# Build and extract
docker build -t hermes-app -f packages/hermes-app/Dockerfile .
docker create --name temp hermes-app
docker cp temp:/app ./static-files
docker rm temp

# Serve from your web server
cp -r ./static-files/* /var/www/hermes/
```

---

## Environment Variables

Update `.env` for your domain:

```env
# CORS origins (must include your domain)
HERMES_ALLOWED_ORIGINS=["https://hermes.yourdomain.com"]

# Optional: Port overrides
HERMES_PORT=3000
HERMES_HTTPS_PORT=3443
```

---

## Troubleshooting

### API calls return 404
- Ensure your proxy forwards `/api/*` to `api:8000/api/*` (preserving the path)
- Check CORS origins in `.env`

### Static files not loading
- Verify volume mount: `docker volume inspect hermes_app_dist`
- Check file permissions in the volume
- Ensure your proxy serves from `/app` or the mounted volume path

### WebSocket connections fail
- Enable WebSocket support in your reverse proxy
- Forward `Upgrade` and `Connection` headers

### HTTPS redirect loops
- Set `X-Forwarded-Proto` header correctly
- Disable SSL enforcement in Hermes if your proxy handles it

---

## Security Considerations

When using your own reverse proxy:

- ✅ Enable HTTPS with valid certificates
- ✅ Set security headers (CSP, HSTS, X-Frame-Options)
- ✅ Configure rate limiting
- ✅ Use internal networks where possible
- ✅ Keep services unexposed (no ports) unless needed
- ✅ Regularly update your reverse proxy

---

## Example: Complete Traefik Stack

```yaml
# docker-compose.yml for Hermes with Traefik
services:
  app:
    build: .
    volumes:
      - app_dist:/app
    networks:
      - hermes-network
      - traefik

  web:
    image: nginx:alpine
    volumes:
      - app_dist:/usr/share/nginx/html:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes.rule=Host(`hermes.example.com`)"
      - "traefik.http.routers.hermes.tls.certresolver=letsencrypt"
    networks:
      - traefik

  api:
    build: ./packages/hermes-api
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes-api.rule=Host(`hermes.example.com`) && PathPrefix(`/api`)"
    networks:
      - hermes-network
      - traefik

networks:
  hermes-network:
    internal: true
  traefik:
    external: true
```

---

## Getting Help

- Check the [Deployment Guide](DEPLOYMENT.md) for general setup
- Review [Configuration Guide](CONFIGURATION.md) for environment variables
- Open an issue on GitHub for specific integration questions

