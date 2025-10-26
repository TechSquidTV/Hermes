# Hermes App Dockerfile - Static Build Only
FROM node:22-alpine AS base

# Install pnpm with specific version for reproducibility
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@latest --activate

# Install dependencies only when needed - optimized caching
FROM base AS deps
WORKDIR /app

# Copy lock files first for better caching
COPY pnpm-lock.yaml packages/hermes-app/package.json ./

# Install dependencies with optimized caching
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --no-frozen-lockfile

# Build the application - optimized layer caching
FROM base AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source files (order matters for caching)
COPY packages/hermes-app/package.json pnpm-lock.yaml ./
COPY packages/hermes-app/postcss.config.js packages/hermes-app/tsconfig.json packages/hermes-app/tsconfig.node.json packages/hermes-app/vite.config.ts packages/hermes-app/index.html ./
COPY packages/hermes-app/public ./public
COPY packages/hermes-app/src ./src

# Build the application
RUN pnpm run build

# Production image - lightweight container for static files
FROM busybox:1.36-glibc AS runner

# Copy built static files from builder
COPY --from=builder /app/dist /app

# Create non-root user
RUN adduser -D -u 1000 hermes && \
    chown -R hermes:hermes /app

# Switch to non-root user
USER hermes

# Set working directory
WORKDIR /app

# Health check - verify static files exist
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD test -f /app/index.html || exit 1

# This container holds static files for the reverse proxy to serve
# It doesn't run a web server - just keeps files available via volume
CMD ["sh", "-c", "echo 'Static files ready at /app' && sleep infinity"]
