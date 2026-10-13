# Configuration Guide

This document provides detailed information about all configuration options available in Hermes.

## Environment Variables

All configuration is managed through environment variables with the `HERMES_` prefix. Below are all available options:

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_SECRET_KEY` | *(required)* | JWT secret key for token signing. Generate a strong random key for production. |
| `HERMES_DEBUG` | `false` | Enable debug logging. HTTP tracebacks and exception details are never exposed. |

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
| `HERMES_DATABASE_URL` | `sqlite+aiosqlite:///./data/hermes.db` | Database connection URL. **SQLite only** - uses aiosqlite for async support. |
| `HERMES_DATABASE_ECHO` | `false` | Enable SQL query logging for debugging |

### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_REDIS_URL` | `redis://localhost:6379` | Redis connection URL for task queuing and caching |
| `HERMES_REDIS_DB` | `0` | Redis database number |

### JWT Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token expiration in minutes |
| `HERMES_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token expiration in days |
| `HERMES_ALGORITHM` | `HS256` | JWT signing algorithm |

Refresh tokens are single-use and must be replaced after every refresh. Logout
revokes the access and refresh token family. Revocation is always enabled;
`HERMES_ENABLE_TOKEN_BLACKLIST` has been removed.

### Signup and initial administrator

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ALLOW_PUBLIC_SIGNUP` | `false` | Public signup policy for new installations; existing saved settings take precedence |
| `HERMES_INITIAL_ADMIN_USERNAME` | unset | Create the initial administrator on startup when no users exist |
| `HERMES_INITIAL_ADMIN_EMAIL` | unset | Valid email for the initial administrator |
| `HERMES_INITIAL_ADMIN_PASSWORD` | unset | Password for the initial administrator; at least eight characters and at most 72 UTF-8 bytes |

The first account can always be created during bootstrap and becomes an
administrator. Later public signup requires an explicit administrator setting.
Account creation and password changes use the same password policy.

### File Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_DOWNLOAD_DIR` | `./downloads` | Directory for completed downloads |
| `HERMES_TEMP_DIR` | `./temp` | Directory for temporary files during processing |
| `HERMES_DOWNLOAD_RETENTION_DAYS` | unset | Opt-in hourly deletion of managed terminal downloads older than this many days; minimum 1. Failed file deletions retain their download records. |

The API and worker must use the same `HERMES_DOWNLOAD_DIR` and share that directory.
On API startup, Hermes repairs missing file records for completed downloads whose
outputs still exist inside this directory. Missing files, directories, and paths
or symlinks that escape the download root are skipped. The repair is idempotent
and does not download media again.

**Breaking configuration change:** The worker no longer reads
`HERMES_DOWNLOADS_DIR`. Set `HERMES_DOWNLOAD_DIR` instead, using `/app/downloads`
for the bundled Docker mounts, and restart the API and worker after updating.

### API Keys & Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_API_KEYS` | `[]` | Comma-separated list of valid API keys |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_RATE_LIMIT_PER_MINUTE` | `60` | Value exposed by the configuration API; authentication uses the budgets below |
| `HERMES_ENABLE_RATE_LIMITING` | `true` | Enable shared Redis budgets for login, signup, and refresh; Redis failure returns 503 |
| `HERMES_TRUSTED_PROXY_HOSTS` | `[]` | Exact IPs or resolvable DNS names of trusted proxies, comma-separated; Compose defaults to `app` |

### Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_MAX_LOGIN_ATTEMPTS` | `5` | Maximum requests per client per authentication endpoint within the configured window |
| `HERMES_LOGIN_ATTEMPT_WINDOW_MINUTES` | `15` | Redis budget window for login, signup, and refresh |

### CORS Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173,https://hermes.example.com,https://hermes-api.example.com` | Comma-separated list of allowed CORS origins. Includes example domains for separate domain deployments. |
| `HERMES_ALLOW_CREDENTIALS` | `true` | Allow credentials in CORS requests |

Wildcard origins (`*`) are rejected when `HERMES_ALLOW_CREDENTIALS=true`.
Configure concrete frontend origins for credentialed requests.

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
| `HERMES_DOWNLOAD_DIR` | `./downloads` | Use `/app/downloads` for the bundled API and worker download mounts |
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

### Production

```bash
HERMES_DEBUG=false
HERMES_SECRET_KEY=your-production-secret-key-change-this
HERMES_DATABASE_URL=sqlite+aiosqlite:///./data/hermes.db
HERMES_REDIS_URL=redis://redis:6379/0
API_PORT=8000
HERMES_RATE_LIMIT_PER_MINUTE=30
```

### Production with Docker

```bash
# In .env file
HERMES_DEBUG=false
HERMES_SECRET_KEY=your-secure-production-key
HERMES_DATABASE_URL=sqlite+aiosqlite:///./data/hermes.db
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
- **Note:** Only SQLite is currently supported

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
8. **User enumeration protection** - Signup endpoints use generic error messages to prevent attackers from discovering registered usernames/emails

See the [Docker setup guide](DOCKER_OPTIMIZATION_README.md) for production deployment recommendations.
