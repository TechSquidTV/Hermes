# Hermes Proxy and Deployment Guide

This comprehensive guide covers deploying Hermes in various configurations, including single domain deployments, separate subdomains, and integration with existing reverse proxies.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Deployment Scenarios](#deployment-scenarios)
  - [Scenario 1: Single Domain (Default)](#scenario-1-single-domain-default)
  - [Scenario 2: Separate Subdomains](#scenario-2-separate-subdomains)
  - [Scenario 3: Existing Reverse Proxy](#scenario-3-existing-reverse-proxy)
- [Runtime Configuration](#runtime-configuration)
- [Reverse Proxy Examples](#reverse-proxy-examples)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [Complete Examples](#complete-examples)

---

## Overview

Hermes provides a flexible deployment architecture that supports:
- **Default**: Single domain with included Caddy reverse proxy
- **Separate Subdomains**: App and API on different domains (e.g., `app.example.com` and `api.example.com`)
- **Custom Integration**: Easy integration with existing reverse proxies (Traefik, nginx, Apache, etc.)

---

## Architecture

```
┌─────────────────┐
│  Reverse Proxy  │ ← Your choice (Caddy, Traefik, nginx, etc.)
└────────┬────────┘
         │
    ┌────┴─────────────────┬──────────────┐
    │                      │              │
┌───▼────┐          ┌──────▼─────┐   ┌───▼─────┐
│  App   │          │    API     │   │  Redis  │
│(nginx) │          │ (FastAPI)  │   │         │
└────────┘          └────────────┘   └─────────┘
```

**Key Components:**
- **App Container**: nginx serving static files with runtime configuration
- **API Container**: FastAPI backend with SSE support
- **Redis**: Caching and task queue
- **Reverse Proxy**: Routes traffic (Caddy included by default)

---

## Deployment Scenarios

### Scenario 1: Single Domain (Default)

The simplest setup - everything served from one domain (e.g., `hermes.example.com`).

#### How It Works
- Frontend: `https://hermes.example.com/`
- API: `https://hermes.example.com/api/v1/`
- Reverse proxy handles routing

#### Quick Start

```bash
# Use the default docker-compose.yml
docker compose up -d

# Access at http://localhost:3000
```

#### Configuration

```yaml
# docker-compose.yml (default)
services:
  proxy:
    image: caddy:2-alpine
    ports:
      - "3000:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - app_dist:/app:ro
    # Routes /api/* to api:8000
    # Routes /* to static files
```

**Environment Variables:**
```env
# .env
VITE_API_BASE_URL=/api/v1  # Relative path (default)
HERMES_ALLOWED_ORIGINS=http://localhost:3000,https://hermes.example.com
```

#### Customizing for Production

Edit `Caddyfile`:

```caddy
hermes.example.com {
    tls admin@example.com

    # SSE Events - MUST come before general API handler
    handle /api/v1/events/* {
        reverse_proxy api:8000 {
            flush_interval -1  # Critical for SSE
        }
    }

    # API routes
    handle /api/* {
        reverse_proxy api:8000
    }

    # Frontend static files
    handle {
        root * /app
        try_files {path} /index.html
        file_server
    }
}
```

---

### Scenario 2: Separate Subdomains

Deploy app and API on different subdomains for better separation, CDN integration, or organizational requirements.

#### Use Cases
- Different infrastructure teams manage frontend vs backend
- CDN caching for frontend only
- Different SSL certificate requirements
- Geographical distribution

#### How Runtime Configuration Works

Hermes uses a **runtime configuration** system that allows you to configure the API URL without rebuilding the Docker image:

1. **Build Time**: App is built with Vite
2. **Container Startup**: `docker-entrypoint.sh` generates `/config.js`
3. **Runtime**: Browser loads `/config.js` which provides the API base URL

This means you can change the API URL by simply setting an environment variable and restarting the container.

#### Configuration Steps

##### 1. Set the API Base URL

```yaml
# docker-compose.yml
services:
  app:
    image: ghcr.io/techsquidtv/hermes-app:latest
    environment:
      # CRITICAL: Set to your API's full URL
      - VITE_API_BASE_URL=https://api.hermes.example.com/api/v1
    ports:
      - "80:80"
```

##### 2. Configure CORS

```env
# .env - API must allow requests from app domain
HERMES_ALLOWED_ORIGINS=https://hermes.example.com,https://app.hermes.example.com
```

##### 3. Deploy Both Services

```yaml
# docker-compose.yml - Separate subdomain setup
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # API - api.hermes.example.com
  api:
    image: ghcr.io/techsquidtv/hermes-api:latest
    environment:
      - HERMES_SECRET_KEY=${HERMES_SECRET_KEY}
      - HERMES_REDIS_URL=redis://redis:6379
      - HERMES_ALLOWED_ORIGINS=https://hermes.example.com
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    ports:
      - "8000:8000"
    depends_on:
      - redis

  celery_worker:
    image: ghcr.io/techsquidtv/hermes-api:latest
    environment:
      - HERMES_SECRET_KEY=${HERMES_SECRET_KEY}
      - HERMES_REDIS_URL=redis://redis:6379
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    depends_on:
      - redis
      - api
    command: celery -A app.worker worker --loglevel=info

  # App - hermes.example.com
  app:
    image: ghcr.io/techsquidtv/hermes-app:latest
    environment:
      - VITE_API_BASE_URL=https://api.hermes.example.com/api/v1
    ports:
      - "3000:80"

volumes:
  redis_data:
```

**DNS Configuration:**
- `api.hermes.example.com` → Your server IP:8000
- `hermes.example.com` → Your server IP:3000

#### Local Testing

Test separate hosts locally without DNS:

```yaml
# docker-compose.test-separate-hosts.yml
services:
  api:
    # ... api config ...
    ports:
      - "8001:8000"
    environment:
      - HERMES_ALLOWED_ORIGINS=http://localhost:3001

  app:
    # ... app config ...
    ports:
      - "3001:80"
    environment:
      - VITE_API_BASE_URL=http://localhost:8001/api/v1
```

Access:
- App: `http://localhost:3001`
- API: `http://localhost:8001/api/v1/health/`

---

### Scenario 3: Existing Reverse Proxy

Integrate Hermes with your existing infrastructure.

#### Option A: Replace Caddy with Your Proxy

1. **Remove proxy service** from `docker-compose.yml`
2. **Connect to your network**
3. **Configure your proxy** (see examples below)

```yaml
# docker-compose.yml - No included proxy
services:
  app:
    image: ghcr.io/techsquidtv/hermes-app:latest
    volumes:
      - app_dist:/usr/share/nginx/html
    networks:
      - hermes-network
      - your-proxy-network
    # NO ports - accessed via your proxy

  api:
    image: ghcr.io/techsquidtv/hermes-api:latest
    networks:
      - hermes-network
      - your-proxy-network
    # NO ports - accessed via your proxy

networks:
  hermes-network:
    driver: bridge
  your-proxy-network:
    external: true
```

#### Option B: Keep Caddy, Proxy to Caddy

Keep the default setup and point your main proxy to Caddy on port 3000.

```yaml
# Your main proxy config
upstream hermes {
    server hermes-proxy:80;
}

server {
    listen 443 ssl;
    server_name hermes.example.com;

    location / {
        proxy_pass http://hermes;
    }
}
```

---

## Reverse Proxy Examples

### Caddy

#### Single Domain

```caddyfile
hermes.example.com {
    # Automatic HTTPS
    tls admin@example.com

    # SSE Events endpoint - MUST come first
    handle /api/v1/events/* {
        reverse_proxy api:8000 {
            flush_interval -1  # Disable buffering for SSE
        }
    }

    # API routes
    handle /api/* {
        reverse_proxy api:8000 {
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
        }
    }

    # Frontend static files
    handle {
        root * /app
        try_files {path} /index.html
        file_server

        # Cache static assets
        @static {
            path *.js *.css *.png *.jpg *.svg *.woff *.woff2
        }
        header @static Cache-Control "public, max-age=31536000, immutable"
    }
}
```

#### Separate Domains

```caddyfile
# API subdomain
api.hermes.example.com {
    reverse_proxy /api/v1/* api:8000
}

# App subdomain
hermes.example.com {
    reverse_proxy app:80
}
```

---

### nginx

#### Single Domain

```nginx
upstream hermes_api {
    server api:8000;
}

server {
    listen 80;
    server_name hermes.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name hermes.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # SSE Events - Critical configuration
    location /api/v1/events/ {
        proxy_pass http://hermes_api/api/v1/events/;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE-specific settings
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
        chunked_transfer_encoding off;
    }

    # API proxy
    location /api/ {
        proxy_pass http://hermes_api/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend static files
    location / {
        # Option 1: Proxy to app container
        proxy_pass http://app:80;

        # Option 2: Serve directly from volume
        # root /var/lib/docker/volumes/hermes_app_dist/_data;
        # try_files $uri $uri/ /index.html;
    }
}
```

#### Separate Domains

```nginx
# api.hermes.example.com
server {
    listen 443 ssl http2;
    server_name api.hermes.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /api/v1/ {
        proxy_pass http://api:8000/api/v1/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://api:8000/health;
    }
}

# hermes.example.com
server {
    listen 443 ssl http2;
    server_name hermes.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://app:80/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### Traefik

#### Labels Configuration

```yaml
services:
  # Direct service exposure
  api:
    image: ghcr.io/techsquidtv/hermes-api:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes-api.rule=Host(`hermes.example.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.hermes-api.entrypoints=websecure"
      - "traefik.http.routers.hermes-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.hermes-api.loadbalancer.server.port=8000"
    networks:
      - traefik
      - hermes-network

  app:
    image: ghcr.io/techsquidtv/hermes-app:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes-app.rule=Host(`hermes.example.com`)"
      - "traefik.http.routers.hermes-app.entrypoints=websecure"
      - "traefik.http.routers.hermes-app.tls.certresolver=letsencrypt"
      - "traefik.http.services.hermes-app.loadbalancer.server.port=80"
    networks:
      - traefik
      - hermes-network

networks:
  traefik:
    external: true
  hermes-network:
    internal: true
```

#### Separate Domains with Traefik

```yaml
services:
  api:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes-api.rule=Host(`api.hermes.example.com`)"
      - "traefik.http.routers.hermes-api.entrypoints=websecure"
      - "traefik.http.routers.hermes-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.hermes-api.loadbalancer.server.port=8000"

  app:
    environment:
      - VITE_API_BASE_URL=https://api.hermes.example.com/api/v1
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes-app.rule=Host(`hermes.example.com`)"
      - "traefik.http.routers.hermes-app.entrypoints=websecure"
      - "traefik.http.routers.hermes-app.tls.certresolver=letsencrypt"
      - "traefik.http.services.hermes-app.loadbalancer.server.port=80"
```

---

### Apache

```apache
<VirtualHost *:80>
    ServerName hermes.example.com
    Redirect permanent / https://hermes.example.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName hermes.example.com

    SSLEngine on
    SSLCertificateFile /path/to/cert.pem
    SSLCertificateKeyFile /path/to/key.pem

    # API proxy
    ProxyPass /api/ http://api:8000/api/
    ProxyPassReverse /api/ http://api:8000/api/

    # Frontend
    ProxyPass / http://app:80/
    ProxyPassReverse / http://app:80/

    # Security headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
</VirtualHost>
```

---

### nginx Proxy Manager

1. **Add Proxy Host** in web UI
2. **Domain**: `hermes.example.com`
3. **Forward Hostname/IP**: `hermes-proxy` (or `app` container)
4. **Forward Port**: `80`
5. **Add SSL Certificate** (Let's Encrypt)

For separate domains:
- Create two proxy hosts
- Point to `app:80` and `api:8000` respectively

---

### Cloudflare Tunnel

```yaml
# cloudflared config.yml
tunnel: <your-tunnel-id>
credentials-file: /path/to/credentials.json

ingress:
  - hostname: hermes.example.com
    service: http://hermes-proxy:80
  - service: http_status:404
```

For separate domains:

```yaml
ingress:
  - hostname: api.hermes.example.com
    service: http://api:8000
  - hostname: hermes.example.com
    service: http://app:80
  - service: http_status:404
```

---

## Environment Variables

### App Container

| Variable | Description | Example | Default | Required |
|----------|-------------|---------|---------|----------|
| `VITE_API_BASE_URL` | API base URL | `https://api.hermes.example.com/api/v1` | `/api/v1` | No (Yes for separate subdomains) |

### API Container

| Variable | Description | Example | Default | Required |
|----------|-------------|---------|---------|----------|
| `HERMES_SECRET_KEY` | JWT secret key | `your-secure-random-key` | - | Yes |
| `HERMES_ALLOWED_ORIGINS` | Comma-separated allowed CORS origins | `https://hermes.example.com,https://app.hermes.example.com` | `http://localhost:3000,http://localhost:5173` | Yes |
| `HERMES_REDIS_URL` | Redis connection URL | `redis://redis:6379` | `redis://localhost:6379` | Yes |
| `HERMES_DATABASE_URL` | Database connection URL | `sqlite+aiosqlite:///./data/hermes.db` | `sqlite+aiosqlite:///./data/hermes.db` | No |

### Proxy Container

| Variable | Description | Example | Default |
|----------|-------------|---------|---------|
| `HERMES_PORT` | HTTP port | `3000` | `3000` |
| `HERMES_HTTPS_PORT` | HTTPS port | `3443` | `3443` |

---

## Troubleshooting

### Issue: "405 Method Not Allowed" on Login

**Symptoms:**
- Browser console: `POST https://hermes.example.com/api/v1/auth/login 405 (Method Not Allowed)`
- API requests hitting wrong endpoint

**Causes:**
1. `VITE_API_BASE_URL` not set correctly
2. App trying to call app domain instead of API domain

**Solution:**

1. Verify `config.js` is generated correctly:
   ```bash
   docker exec hermes-app cat /usr/share/nginx/html/config.js
   ```

   Should show:
   ```javascript
   window.__RUNTIME_CONFIG__ = {
     API_BASE_URL: "https://api.hermes.example.com/api/v1"
   };
   ```

2. Check browser console for actual API URL:
   ```
   [ApiClient] Using API base URL: https://api.hermes.example.com/api/v1
   ```

3. If showing `/api/v1` instead of full URL, environment variable is not set:
   ```bash
   docker compose restart app
   ```

---

### Issue: CORS Errors

**Symptoms:**
- `Access to XMLHttpRequest... has been blocked by CORS policy`

**Solution:**

1. Add app domain to API's allowed origins:
   ```env
   # .env
   HERMES_ALLOWED_ORIGINS=https://hermes.example.com,https://app.hermes.example.com
   ```

2. Restart API:
   ```bash
   docker compose restart api
   ```

3. Verify CORS headers:
   ```bash
   curl -I http://localhost:8000/api/v1/health/ -H "Origin: https://hermes.example.com"
   # Should see: access-control-allow-origin: https://hermes.example.com
   ```

---

### Issue: Cannot Connect to API

**Symptoms:**
- `Failed to fetch` or `net::ERR_CONNECTION_REFUSED`

**Causes:**
1. API not accessible from browser
2. Mixed content (HTTPS app, HTTP API)
3. Firewall blocking

**Solution:**

1. Test API from browser:
   ```
   https://api.hermes.example.com/api/v1/health/
   ```

   Should return:
   ```json
   {"status":"healthy","timestamp":"...","version":"..."}
   ```

2. Ensure both use same protocol (both HTTP or both HTTPS)

3. Check firewall rules

---

### Issue: Real-time Updates Not Working

**Symptoms:**
- Download progress not updating
- Queue not refreshing

**Note:** Hermes uses **Server-Sent Events (SSE)**, not WebSockets.

**Solution:**

1. Verify SSE endpoint is accessible:
   ```bash
   curl http://localhost:8000/api/v1/events/downloads/test-id
   ```

2. For nginx, ensure proper configuration:
   ```nginx
   location /api/v1/events/ {
       proxy_buffering off;
       proxy_cache off;
       proxy_read_timeout 86400;
   }
   ```

3. For Caddy, ensure flush_interval is set:
   ```caddy
   handle /api/v1/events/* {
       reverse_proxy api:8000 {
           flush_interval -1
       }
   }
   ```

---

### Issue: Static Files Not Loading

**Symptoms:**
- 404 errors for JS/CSS files
- Blank page

**Solution:**

1. Verify volume mount:
   ```bash
   docker volume inspect hermes_app_dist
   ```

2. Check app container is running:
   ```bash
   docker ps | grep hermes-app
   ```

3. Test direct access to app:
   ```bash
   curl http://localhost:3000/
   ```

---

### Issue: Config Not Updating

**Symptoms:**
- Changed `VITE_API_BASE_URL` but app uses old value

**Solution:**

1. Restart app container:
   ```bash
   docker compose restart app
   ```

2. Clear browser cache:
   - Chrome/Edge: Ctrl+Shift+R or Cmd+Shift+R
   - Firefox: Ctrl+F5

3. Verify new config:
   ```bash
   curl http://localhost:3000/config.js
   ```

---

## Complete Examples

### Example 1: Production Single Domain

```yaml
# docker-compose.yml
services:
  proxy:
    image: caddy:2-alpine
    container_name: hermes-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
      - app_dist:/app:ro
    networks:
      - hermes-network
    depends_on:
      - app
      - api

  app:
    image: ghcr.io/techsquidtv/hermes-app:latest
    container_name: hermes-app
    restart: unless-stopped
    environment:
      - VITE_API_BASE_URL=/api/v1
    volumes:
      - app_dist:/usr/share/nginx/html
    networks:
      - hermes-network

  api:
    image: ghcr.io/techsquidtv/hermes-api:latest
    container_name: hermes-api
    restart: unless-stopped
    env_file: .env
    environment:
      - HERMES_REDIS_URL=redis://redis:6379
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    networks:
      - hermes-network
    depends_on:
      - redis

  celery_worker:
    image: ghcr.io/techsquidtv/hermes-api:latest
    container_name: hermes-worker
    restart: unless-stopped
    env_file: .env
    environment:
      - HERMES_REDIS_URL=redis://redis:6379
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    networks:
      - hermes-network
    depends_on:
      - redis
      - api
    command: celery -A app.worker worker --loglevel=info

  redis:
    image: redis:7-alpine
    container_name: hermes-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - hermes-network
    command: redis-server --appendonly yes

networks:
  hermes-network:
    driver: bridge

volumes:
  app_dist:
  caddy_data:
  caddy_config:
  redis_data:
```

```env
# .env
HERMES_SECRET_KEY=your-secure-production-key
HERMES_ALLOWED_ORIGINS=https://hermes.example.com
VITE_API_BASE_URL=/api/v1
```

```caddy
# Caddyfile
hermes.example.com {
    tls admin@example.com

    handle /api/v1/events/* {
        reverse_proxy api:8000 {
            flush_interval -1
        }
    }

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

---

### Example 2: Separate Subdomains with Traefik

```yaml
# docker-compose.yml
services:
  app:
    image: ghcr.io/techsquidtv/hermes-app:latest
    container_name: hermes-app
    restart: unless-stopped
    environment:
      - VITE_API_BASE_URL=https://api.hermes.example.com/api/v1
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes-app.rule=Host(`hermes.example.com`)"
      - "traefik.http.routers.hermes-app.entrypoints=websecure"
      - "traefik.http.routers.hermes-app.tls.certresolver=letsencrypt"
      - "traefik.http.services.hermes-app.loadbalancer.server.port=80"
    networks:
      - traefik
      - hermes-network

  api:
    image: ghcr.io/techsquidtv/hermes-api:latest
    container_name: hermes-api
    restart: unless-stopped
    env_file: .env
    environment:
      - HERMES_REDIS_URL=redis://redis:6379
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.hermes-api.rule=Host(`api.hermes.example.com`)"
      - "traefik.http.routers.hermes-api.entrypoints=websecure"
      - "traefik.http.routers.hermes-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.hermes-api.loadbalancer.server.port=8000"
    networks:
      - traefik
      - hermes-network
    depends_on:
      - redis

  celery_worker:
    image: ghcr.io/techsquidtv/hermes-api:latest
    container_name: hermes-worker
    restart: unless-stopped
    env_file: .env
    environment:
      - HERMES_REDIS_URL=redis://redis:6379
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    networks:
      - hermes-network
    depends_on:
      - redis
      - api
    command: celery -A app.worker worker --loglevel=info

  redis:
    image: redis:7-alpine
    container_name: hermes-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - hermes-network
    command: redis-server --appendonly yes

networks:
  traefik:
    external: true
  hermes-network:
    driver: bridge

volumes:
  redis_data:
```

```env
# .env
HERMES_SECRET_KEY=your-secure-production-key
HERMES_ALLOWED_ORIGINS=https://hermes.example.com
VITE_API_BASE_URL=https://api.hermes.example.com/api/v1
```

---

### Example 3: Local Testing Separate Hosts

```yaml
# docker-compose.test-separate-hosts.yml
services:
  redis:
    image: redis:7-alpine
    container_name: hermes-redis-test
    command: redis-server --appendonly yes

  api:
    build:
      context: ./packages/hermes-api
      dockerfile: Dockerfile
    container_name: hermes-api-test
    environment:
      - HERMES_SECRET_KEY=test-secret-key
      - HERMES_REDIS_URL=redis://redis:6379
      - HERMES_ALLOWED_ORIGINS=http://localhost:3001
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    ports:
      - "8001:8000"
    depends_on:
      - redis

  celery_worker:
    build:
      context: ./packages/hermes-api
      dockerfile: Dockerfile
    container_name: hermes-worker-test
    environment:
      - HERMES_SECRET_KEY=test-secret-key
      - HERMES_REDIS_URL=redis://redis:6379
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    depends_on:
      - redis
      - api
    command: celery -A app.worker worker --loglevel=info

  app:
    build:
      context: .
      dockerfile: packages/hermes-app/Dockerfile
    container_name: hermes-app-test
    environment:
      - VITE_API_BASE_URL=http://localhost:8001/api/v1
    ports:
      - "3001:80"
    depends_on:
      - api
```

**Usage:**
```bash
docker compose -f docker-compose.test-separate-hosts.yml up --build

# Access:
# - App: http://localhost:3001
# - API: http://localhost:8001/api/v1/health/
```

---

## Verification Checklist

After deploying, verify your setup:

- [ ] **API Health Check**
  ```bash
  curl https://api.hermes.example.com/api/v1/health/
  # or for single domain:
  curl https://hermes.example.com/api/v1/health/
  ```

- [ ] **App Loads**
  ```bash
  curl https://hermes.example.com/
  # Should return HTML
  ```

- [ ] **Config.js Generated**
  ```bash
  curl https://hermes.example.com/config.js
  # Should show API_BASE_URL
  ```

- [ ] **Browser Console Check**
  - Open `https://hermes.example.com`
  - Check console for: `[ApiClient] Using API base URL: ...`
  - Should show correct API URL

- [ ] **Login Test**
  - Try signing up / logging in
  - Should successfully authenticate

- [ ] **Real-time Updates**
  - Start a download
  - Progress should update in real-time

---

## Additional Resources

- [Main README](../README.md)
- [Environment Variables Reference](../.env.example)
- [Issue Tracker](https://github.com/TechSquidTV/Hermes/issues)
- [Docker Documentation](https://docs.docker.com/)

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check logs:**
   ```bash
   docker compose logs app
   docker compose logs api
   docker compose logs proxy
   ```

2. **Verify environment:**
   ```bash
   docker exec hermes-app env | grep VITE
   docker exec hermes-api env | grep HERMES
   ```

3. **Create a GitHub issue** with:
   - Your docker-compose configuration (redact secrets)
   - Container logs
   - Browser console errors
   - Network tab showing failed requests
