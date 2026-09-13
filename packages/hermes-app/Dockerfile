# Hermes App Dockerfile - Static Build Only
FROM node:26-alpine AS base

# Corepack selects the package manager pinned in the root manifest.
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
WORKDIR /app
COPY package.json ./
# Node 26 no longer bundles Corepack; keep its version managed by Dependabot.
RUN npm install --global --ignore-scripts --no-audit --no-fund \
    "corepack@$(node -p 'require("./package.json").devDependencies.corepack')" \
    && corepack enable pnpm

FROM base AS deps
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/hermes-app/package.json ./packages/hermes-app/package.json
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile

FROM deps AS builder
ARG VITE_HERMES_BUILD_VERSION
ENV VITE_HERMES_BUILD_VERSION=${VITE_HERMES_BUILD_VERSION}
COPY packages/hermes-app/ ./packages/hermes-app/
RUN pnpm --filter hermes-app build

# Production image - nginx serving static files with runtime config
FROM nginx:1.31-alpine AS runner

# Copy built static files from builder
COPY --from=builder /app/packages/hermes-app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY packages/hermes-app/nginx.conf /etc/nginx/nginx.conf

# Copy and prepare entrypoint script
COPY packages/hermes-app/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Health check - verify nginx is serving content
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1

# Expose port 80
EXPOSE 80

# Use custom entrypoint to generate runtime config
ENTRYPOINT ["/docker-entrypoint.sh"]

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
