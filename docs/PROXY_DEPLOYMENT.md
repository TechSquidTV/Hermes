# Reverse proxy deployment

The bundled app container serves the UI and proxies `/api/*` to `api:8000`.
For most deployments, put an HTTPS reverse proxy in front of `app:80` and keep
`VITE_API_BASE_URL=/api/v1`. The API and Redis need no public host ports.

Use the complete [source or prebuilt stack](../README.md#quick-start), including
the worker and scheduler. Examples here are proxy configuration or Compose
**overrides**, not replacement stacks. Keep one exact release across all Hermes
services; do not replace backend definitions with standalone `latest` images.
See [deployment](DEPLOYMENT.md) for storage and operational requirements.

## Single domain

For `https://hermes.example.com`:

| Traffic | Destination |
| --- | --- |
| UI and static assets | External proxy → `app:80` |
| `/api/v1/*`, including API docs and events | External proxy → `app:80` → `api:8000` |

In `.env`:

```dotenv
VITE_API_BASE_URL=/api/v1
HERMES_ALLOWED_ORIGINS=https://hermes.example.com
```

The examples assume the proxy can resolve the Compose service names. For a
containerized proxy, connect it to `hermes-network`, or connect `app` to the
proxy's existing Docker network with an override:

```yaml
# proxy-overrides.yml: replace proxy-network with your existing network.
services:
  app:
    networks:
      - hermes-network
      - proxy-network

networks:
  proxy-network:
    external: true
```

Apply it alongside your base file:

```bash
docker compose -f docker-compose.example.yml -f proxy-overrides.yml up -d --wait
```

For a proxy running on the host, forward to the app's published port, such as
`127.0.0.1:3000`, instead of a Docker service name. Restrict that port to trusted
traffic when the proxy is the intended public entry point.

### Caddy

```caddyfile
hermes.example.com {
    reverse_proxy app:80 {
        flush_interval -1
    }
}
```

### nginx

The TLS certificate paths below refer to files on the external proxy. This
configuration sends all requests through the app, including API documentation
and event streams:

```nginx
server {
    listen 80;
    server_name hermes.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name hermes.example.com;
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://app:80;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
    }
}
```

### Traefik

Add labels and network access to the existing `app` service. This assumes your
Traefik deployment already defines the `websecure` entrypoint, `letsencrypt`
certificate resolver, and external `traefik` network:

```yaml
# traefik-overrides.yml
services:
  app:
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=traefik"
      - "traefik.http.routers.hermes.rule=Host(`hermes.example.com`)"
      - "traefik.http.routers.hermes.entrypoints=websecure"
      - "traefik.http.routers.hermes.tls.certresolver=letsencrypt"
      - "traefik.http.services.hermes.loadbalancer.server.port=80"
    networks:
      - hermes-network
      - traefik

networks:
  traefik:
    external: true
```

Keep API routing through the app; a second API router is unnecessary for a
single-domain setup.

### Other proxies

| Proxy | Upstream and requirements |
| --- | --- |
| nginx Proxy Manager | Create a proxy host for `hermes.example.com`, forward to `app:80`, enable a TLS certificate, and disable event-stream buffering |
| Apache | Proxy `/` to `http://app:80/`, preserve the host, and allow unbuffered long-lived event responses |
| Cloudflare Tunnel | Route the Hermes hostname to `http://app:80` on a reachable Docker network |

## Separate API domain

Use this topology when the browser must contact an independent API origin:

- Frontend: `https://hermes.example.com`
- API: `https://api.hermes.example.com/api/v1`

DNS records for both hostnames point to the public proxy. DNS records do not
select container ports; the proxy routes each hostname to the correct upstream.

In `.env`:

```dotenv
VITE_API_BASE_URL=https://api.hermes.example.com/api/v1
HERMES_ALLOWED_ORIGINS=https://hermes.example.com
```

Allow the **frontend origin** in CORS. The API base URL must be browser-reachable
and use HTTPS when the frontend does. Keep API paths unchanged; do not strip
`/api/v1` at the proxy.

Connect `api` to the proxy network as well as `hermes-network` in an override,
while retaining the base environment, mounts, dependencies, and health checks.
The worker, scheduler, and Redis stay on the internal network.

For Caddy:

```caddyfile
hermes.example.com {
    reverse_proxy app:80
}

api.hermes.example.com {
    reverse_proxy api:8000 {
        flush_interval -1
    }
}
```

For nginx, use the TLS server block above for each hostname, with the API
hostname's `proxy_pass` set to `http://api:8000`. Retain the buffering and timeout
settings for API events. Traefik and other proxies similarly need a second
hostname route to `api:8000`.

### Local separate-origin test

The repository includes a source-build test stack with distinct browser origins:

```bash
docker compose -f docker-compose.test-separate-hosts.yml up --build --wait
```

Prepare the secret and storage directories from the [quick start](../README.md#quick-start)
first. Stop other Hermes stacks sharing these directories. This test stack uses
its own environment overrides and Redis volume; it is not a production config.
Open [the app](http://localhost:3001) and [API docs](http://localhost:8001/api/v1/docs).
The API URL is `http://localhost:8001/api/v1`.

## Runtime configuration

The production app entrypoint generates `/config.js` from `VITE_API_BASE_URL`
each time its container starts. The browser's [configuration helper](../packages/hermes-app/src/lib/config.ts)
reads that runtime value before Vite's build-time value and the `/api/v1` default.

After changing `.env`, recreate affected services with the same base and override
files used for deployment:

```bash
docker compose -f docker-compose.example.yml -f proxy-overrides.yml up -d --wait
```

`docker compose restart` does not reload changed container environment values.
No app image rebuild is needed for production runtime configuration. Native Vite
builds capture the value at build time and need a rebuild. Development Compose
uses `/api/v1` and sets the Vite upstream separately.

## Forwarded addresses and events

Preserve the public `Host` header and supply forwarded protocol/client headers
at the edge. `HERMES_TRUSTED_PROXY_HOSTS` controls which exact proxy IPs or
resolvable hostnames the authentication limiter trusts for `X-Forwarded-For`.
Compose trusts `app` by default. Include each trusted external proxy in the chain
when client addresses must pass through it; for direct API routing, include the
proxy reaching the API. Never trust arbitrary forwarded headers or wildcard peers.

Hermes uses server-sent events (SSE). Every proxy hop must avoid buffering or
caching event responses and allow long-lived connections. The bundled nginx
already configures `/api/v1/events/` this way. Browser streams use scoped,
short-lived tokens obtained through an authenticated request; an unauthenticated
`curl` to an event URL cannot verify the complete stream flow.

## Verify and troubleshoot

```bash
curl --fail https://hermes.example.com/
curl --fail https://hermes.example.com/config.js
curl --fail https://hermes.example.com/api/v1/health/ready
```

For a separate API hostname, send the readiness request there. Verify the
browser loads the intended API URL, can log in, and receives progress for a new
download. Keep `config.js`, `index.html`, and `build-id.txt` uncached at any
additional proxy or CDN so configuration and deployed-build detection stay current.

| Symptom | Check |
| --- | --- |
| Login returns 405 or an HTML response | `/api/*` reaches the API through the app, or the separate API URL is configured correctly |
| CORS error | API allows the exact frontend origin, including scheme and any non-default port |
| Changed API URL has no effect | Recreate the app and inspect `/config.js`; restarting alone retains the old environment |
| Connection refused or mixed content | API hostname resolves, proxy upstream is reachable, and both public origins use HTTPS |
| Progress is delayed | Disable buffering/caching at every proxy hop and renew scoped SSE tokens |
| Authentication limits group all users together | Check the trusted proxy chain and forwarded client addresses |

Review `app` and `api` logs using the same Compose file selection as deployment.
Redact secrets from configuration and logs before opening an
[issue](https://github.com/TechSquidTV/Hermes/issues).
