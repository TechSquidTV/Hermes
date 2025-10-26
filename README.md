# Hermes — Self-Hosted Video Downloader

🎥 **Download videos from YouTube and 1000+ sites with a robust API and beautiful, modern interface**

Hermes is a self-hosted video downloader built on [yt-dlp](https://github.com/yt-dlp/yt-dlp).

_This tool is designed for content creators who wish to **lawfully** use freely available media under [fair use](https://en.wikipedia.org/wiki/Fair_use) (best explained by [Tom Scott](https://www.youtube.com/watch?v=1Jwo5qc78QU)).
Hermes **does not endorse** piracy, freebooting, or using downloads to bypass advertising._

https://github.com/user-attachments/assets/7d9c6b96-d966-4989-a8b3-d5d49af463ae

## ✨ Key Features

- 🎥 **Universal Support** - Download from YouTube, Vimeo, TikTok, and 1000+ sites
- ⚡ **Background Processing** - Queue downloads and process them asynchronously
- 🔒 **Secure Authentication** - JWT tokens with API key management
- 🐳 **Docker Ready** - One-command deployment with Docker Compose

## 🚀 Quick Start

### Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/techsquidtv/hermes.git
cd hermes

# Copy environment template (all environment variables are configured in the root .env file)
cp .env.example .env

# Edit .env and set a secure HERMES_SECRET_KEY
nano .env

# Start all services (includes Caddy reverse proxy)
docker compose up -d
```

**That's it!** 🎉 Your Hermes instance will be available at:
- **Web App**: http://localhost:3000
- **API Docs**: http://localhost:3000/api/v1/docs (via proxy)

**For development with hot reload:**
```bash
docker compose -f docker-compose.dev.yml up
```
- **Dev Server**: http://localhost:5173 (Vite with hot reload)
- **API**: http://localhost:8000 (direct access)

### Customizing the Reverse Proxy

The default setup uses Caddy as a reverse proxy. You can customize it by editing the `Caddyfile`:

```bash
nano Caddyfile
# Add your domain for automatic HTTPS, custom routing, etc.
docker compose restart proxy
```

See our [Reverse Proxy Guide](docs/REVERSE_PROXY_GUIDE.md) for integrating with existing setups (Traefik, nginx, etc.).

### 🐛 Having Issues?

If you run into problems, please use our [issue templates](https://github.com/techsquidtv/hermes/issues/new/choose) instead of generic issues:
- **[🐛 Bug Report](https://github.com/techsquidtv/hermes/issues/new?template=bug_report.yml)** - For unexpected behavior
- **[🔧 API Issues](https://github.com/techsquidtv/hermes/issues/new?template=hermes-api-issue.yml)** - Backend problems
- **[🎨 Frontend Issues](https://github.com/techsquidtv/hermes/issues/new?template=hermes-app-issue.yml)** - UI/UX problems
- **[🐳 DevOps Issues](https://github.com/techsquidtv/hermes/issues/new?template=devops-issue.yml)** - Docker/deployment issues

These templates help us help you faster! 🚀

### Manual Installation

```bash
# Install dependencies
pnpm install

# Set up environment (all environment variables are configured in the root .env file)
cp .env.example .env
# Edit .env with your settings

# Start development servers
pnpm dev
```

## 📚 Documentation

- **[Configuration Guide](docs/CONFIGURATION.md)** - Complete environment variables and settings reference
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Docker volumes, production deployment, and troubleshooting
- **[Contributing Guide](docs/CONTRIBUTING.md)** - How to contribute code, tests, and documentation
- **[API Documentation](packages/hermes-api/README.md)** - Complete API reference and examples
- **[Frontend Guide](packages/hermes-app/README.md)** - React app development guide
- **[Interactive API Docs](http://localhost:8000/docs)** - Live Swagger documentation

## 🤝 Contributing

We welcome contributions! Here's how to get involved:

### 🐛 Reporting Issues
Use our [issue templates](https://github.com/techsquidtv/hermes/issues/new/choose) to report bugs and request features:
- **[🐛 Bug Report](https://github.com/techsquidtv/hermes/issues/new?template=bug_report.yml)** - Report bugs and unexpected behavior
- **[✨ Feature Request](https://github.com/techsquidtv/hermes/issues/new?template=feature_request.yml)** - Suggest new features
- **[🔧 API Issues](https://github.com/techsquidtv/hermes/issues/new?template=hermes-api-issue.yml)** - Backend/API specific issues
- **[🎨 Frontend Issues](https://github.com/techsquidtv/hermes/issues/new?template=hermes-app-issue.yml)** - UI/UX and frontend issues
- **[🐳 DevOps Issues](https://github.com/techsquidtv/hermes/issues/new?template=devops-issue.yml)** - Docker/deployment issues
- **[📚 Documentation](https://github.com/techsquidtv/hermes/issues/new?template=documentation.yml)** - Documentation improvements

### 💻 Contributing Code
See our [contribution guidelines](docs/CONTRIBUTING.md) for development setup, testing, and code standards.

## 📄 License

See [LICENSE](LICENSE) for details.

---

## Hosting Partner

This could be you! Bring Hermes to the world by hosting a public instance and getting featured here!
