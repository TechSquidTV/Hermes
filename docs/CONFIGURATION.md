# Configuration Guide

This document provides detailed information about all configuration options available in Hermes.

## Environment Variables

All configuration is managed through environment variables with the `HERMES_` prefix. Below are all available options:

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_SECRET_KEY` | *(required)* | JWT secret key for token signing. Generate a strong random key for production. |
| `HERMES_DEBUG` | `true` | Enable debug mode. Set to `false` in production. |

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8000` | Port for the API server |
| `API_TITLE` | `Hermes API` | API title displayed in documentation |
| `API_DESCRIPTION` | `Video downloader API` | API description |
| `API_VERSION` | `1.0.0` | API version |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_DATABASE_URL` | `sqlite+aiosqlite:///./data/hermes.db` | Database connection URL. Supports SQLite, PostgreSQL, MySQL. |
| `HERMES_DATABASE_ECHO` | `false` | Enable SQL query logging for debugging |

### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_REDIS_URL` | `redis://localhost:6379` | Redis connection URL for task queuing and caching |
| `HERMES_REDIS_DB` | `0` | Redis database number |

### JWT Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Access token expiration (24 hours) |
| `HERMES_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token expiration (30 days) |
| `HERMES_ALGORITHM` | `HS256` | JWT signing algorithm |

### File Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_DOWNLOAD_DIR` | `./downloads` | Directory for completed downloads |
| `HERMES_TEMP_DIR` | `./temp` | Directory for temporary files during processing |

### API Keys & Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_API_KEYS` | `[]` | Comma-separated list of valid API keys |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_RATE_LIMIT_PER_MINUTE` | `60` | Maximum requests per minute per IP |
| `HERMES_ENABLE_RATE_LIMITING` | `true` | Enable rate limiting |
| `HERMES_ENABLE_TOKEN_BLACKLIST` | `true` | Enable token blacklisting for logout |

### Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_MAX_LOGIN_ATTEMPTS` | `5` | Maximum failed login attempts before lockout |
| `HERMES_LOGIN_ATTEMPT_WINDOW_MINUTES` | `15` | Time window for login attempt tracking |

### CORS Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173,https://hermes.example.com,https://hermes-api.example.com` | Comma-separated list of allowed CORS origins. Includes example domains for separate domain deployments. |
| `HERMES_ALLOW_CREDENTIALS` | `true` | Allow credentials in CORS requests |

#### CORS Examples

**Development:**
```bash
HERMES_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Single Domain Production:**
```bash
HERMES_ALLOWED_ORIGINS=https://hermes.example.com
```

**Separate Domains Production:**
```bash
HERMES_ALLOWED_ORIGINS=https://hermes.example.com,https://hermes-api.example.com
```

## Docker Configuration

When using Docker, you can also configure these additional variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_APP_PORT` | `3000` | Port for the frontend application (Docker production build) |
| `HERMES_DOWNLOADS_DIR` | `/app/downloads` | Downloads directory in container |
| `HERMES_TEMP_DIR` | `/app/temp` | Temporary directory in container |

**Note:** The frontend development server runs on port 5173 when using `pnpm dev`, but Docker builds use port 3000.

## Frontend Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `/api/v1` | API base URL for frontend builds. Used during build time to configure API endpoints. |

#### Frontend API URL Examples

**Development (same domain):**
```bash
VITE_API_BASE_URL=/api/v1
```

**Production (same domain):**
```bash
VITE_API_BASE_URL=/api/v1
```

**Separate API domain:**
```bash
VITE_API_BASE_URL=https://hermes-api.example.com/api/v1
```

**Note:** This variable is used at build time by Vite. After setting it, rebuild the frontend:
```bash
cd packages/hermes-app
pnpm run build
```

## Configuration Examples

### Development

```bash
HERMES_DEBUG=true
HERMES_SECRET_KEY=your-development-secret-key
HERMES_DATABASE_URL=sqlite+aiosqlite:///./data/hermes.db
HERMES_REDIS_URL=redis://localhost:6379
API_PORT=8000
```

### Production with PostgreSQL

```bash
HERMES_DEBUG=false
HERMES_SECRET_KEY=your-production-secret-key-change-this
HERMES_DATABASE_URL=postgresql+asyncpg://user:password@db:5432/hermes
HERMES_REDIS_URL=redis://redis:6379/0
API_PORT=8000
HERMES_RATE_LIMIT_PER_MINUTE=30
```

### Production with Docker

```bash
# In .env file
HERMES_DEBUG=false
HERMES_SECRET_KEY=your-secure-production-key
HERMES_DATABASE_URL=postgresql+asyncpg://user:password@db/hermes
HERMES_REDIS_URL=redis://redis:6379
API_PORT=8000
HERMES_APP_PORT=3000
HERMES_RATE_LIMIT_PER_MINUTE=60
```

## Generating a Secure Secret Key

For production, generate a secure secret key:

```bash
# Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"

# Using OpenSSL
openssl rand -hex 32
```

## Environment File Setup

1. Copy the example environment file (all configuration is in the root .env file):
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your specific configuration:
   ```bash
   nano .env
   ```

3. Ensure the `.env` file is in your `.gitignore` to prevent committing secrets.

## Troubleshooting

### Common Issues

**"Invalid SECRET_KEY" error:**
- Ensure `HERMES_SECRET_KEY` is set to a non-empty value
- Use a long, random string for production

**Database connection errors:**
- Verify `HERMES_DATABASE_URL` format is correct
- For SQLite: `sqlite+aiosqlite:///path/to/db.sqlite`
- For PostgreSQL: `postgresql+asyncpg://user:password@host:port/db`

**Redis connection errors:**
- Verify `HERMES_REDIS_URL` is accessible
- Check if Redis is running and accepting connections

**CORS errors:**
- Add your frontend URL to `HERMES_ALLOWED_ORIGINS`
- Ensure `HERMES_ALLOW_CREDENTIALS=true` for authenticated requests

## Security Best Practices

1. **Always use HTTPS in production**
2. **Use strong, unique secret keys**
3. **Rotate tokens regularly**
4. **Enable rate limiting**
5. **Monitor authentication attempts**
6. **Keep dependencies updated**
7. **Use proper database backups**

See the [Docker setup guide](DOCKER_OPTIMIZATION_README.md) for production deployment recommendations.
