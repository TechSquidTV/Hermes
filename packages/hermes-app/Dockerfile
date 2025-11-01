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

# Production image - nginx serving static files with runtime config
FROM nginx:alpine AS runner

# Copy built static files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY packages/hermes-app/nginx.conf /etc/nginx/nginx.conf

# Copy and prepare entrypoint script
COPY packages/hermes-app/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Health check - verify nginx is serving content
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Expose port 80
EXPOSE 80

# Use custom entrypoint to generate runtime config
ENTRYPOINT ["/docker-entrypoint.sh"]

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
