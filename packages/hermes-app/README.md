# Hermes App

Modern React/TypeScript app for the Hermes video downloader, built with Vite, TanStack Router, and shadcn/ui.

## 🚀 Quick Start

### Prerequisites

- Node.js 22.22.2+ (22.x), 24.15+ (24.x), or 26+ (used in Docker and CI)
- pnpm 12.3.4 (pinned in the root package.json; enable Corepack)

### Installation

```bash
# From the project root
npm install --global "corepack@$(node -p 'require("./package.json").devDependencies.corepack')"
corepack enable pnpm
pnpm install

# Or from the hermes-app directory
cd packages/hermes-app
pnpm install
```

### Development

```bash
# Start development server
pnpm dev

# Type checking
pnpm type-check

# Build for production
pnpm build

# Preview production build
pnpm preview
```

The app will be available at http://localhost:5173

## 🔧 API Integration

### Type Generation

Hermes uses **automatic TypeScript type generation** from the backend API's OpenAPI schema:

```bash
# Generate types from running API (requires API server running)
pnpm generate:types
```

**Development Workflow:**
1. Backend API changes are made
2. Run `pnpm generate:types` to export the schema directly from the Python app
3. Generated types in `src/types/api.generated.ts` are committed
4. Frontend gets full type safety for all API calls

**How it works:** FastAPI automatically serves OpenAPI JSON at `http://localhost:8000/openapi.json`

**Current State:** Uses auto-generated types in `src/types/api.generated.ts` (2,937+ lines)

**✅ Working:** Run `pnpm generate:types` to update generated types with full automation

## 🏗️ Architecture

### Tech Stack

- **React 19** - Modern React with concurrent features
- **TypeScript** - Full type safety
- **Vite** - Fast build tool and dev server
- **TanStack Router** - Type-safe routing
- **TanStack Query** - Server state management
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality component library
- **Lucide React** - Beautiful icons
- **date-fns** - Modern date utilities

### Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Base shadcn/ui components
│   ├── auth/           # Authentication components
│   ├── queue/          # Queue management components
│   ├── settings/       # Settings components
│   └── forms/          # Form components
├── hooks/              # Custom React hooks
├── routes/             # Route components
├── services/           # API client and services
├── types/              # TypeScript type definitions
├── lib/                # Utilities and helpers
└── utils/              # Additional utilities
```

## 📝 Available Scripts

- `pnpm dev` - Start development server
- `pnpm build` - Build for production
- `pnpm preview` - Preview production build
- `pnpm type-check` - Run TypeScript type checking
- `pnpm lint` - Run linting
- `pnpm clean` - Clean build artifacts

## 🔧 Configuration

The app connects to the Hermes API backend. Configure the API URL in:

- Development: `VITE_API_BASE_URL` environment variable
- Production: Uses relative paths for nginx proxy

## 🎨 Styling

- **Tailwind CSS** for styling
- **CSS Variables** for theming
- **Dark mode** support (auto, light, dark)
- **Responsive design** with mobile-first approach

## 🔒 Authentication

- JWT token-based authentication
- Automatic token refresh
- Secure token storage (sessionStorage + localStorage)
- Protected routes with role-based access

## 📱 Features

- **Drag & Drop** URL input
- **Real-time** download progress
- **Queue management** with filtering and sorting
- **Video preview** with format selection
- **Bulk operations** (delete, retry)
- **Responsive design** for all devices
- **Keyboard shortcuts** for power users
- **Settings management** with API key generation

## 🧪 Testing

```bash
# Run tests (when implemented)
pnpm test

# Test with coverage
pnpm test:coverage
```

## 📦 Building

```bash
# Build for production
pnpm build

# The built files will be in the `dist/` directory
```

## 🚀 Deployment

The app is designed to work with nginx and can be deployed as static files. See the Dockerfile for containerized deployment.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `pnpm type-check` to ensure type safety
5. Submit a pull request

## 📄 License

See the main project LICENSE file.

