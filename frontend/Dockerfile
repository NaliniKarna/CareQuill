# Multi-stage Dockerfile.
#
# - `dev` target: what docker-compose.yml (local development) builds. Installs
#   dependencies and runs `next dev`; the compose file bind-mounts the source
#   over this image, so the container just provides a consistent Node runtime.
# - `production` target: a real production build (`next build` + `next start`,
#   no bind mounts, no dev dependencies in the final image). Used by
#   docker-compose.prod.yml and any other production deployment.
#
# Build a specific target with: docker build --target production -t medqueue-frontend .

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
# The BuildKit cache mount keeps npm's download cache between builds, so a
# lockfile change only downloads the new packages instead of all of them.
# Retries help on slow or unstable connections.
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit --no-fund \
    --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000

# ---------------------------------------------------------------------------
FROM deps AS dev
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ---------------------------------------------------------------------------
FROM deps AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY . .
# NEXT_PUBLIC_* values are baked in at build time -- pass the real API URL
# as a build arg when building for a specific deployment target.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_CONTACT_EMAIL=support@carequill.app
ENV NEXT_PUBLIC_CONTACT_EMAIL=$NEXT_PUBLIC_CONTACT_EMAIL
RUN npm run build

# ---------------------------------------------------------------------------
FROM node:22-alpine AS production
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup -S nodejs && adduser -S nextjs -G nodejs

# `output: "standalone"` (next.config.ts) emits a minimal server.js plus only
# the node_modules it needs. Static assets are copied alongside it.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:3000/login >/dev/null || exit 1
CMD ["node", "server.js"]
