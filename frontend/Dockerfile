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
RUN npm ci

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
RUN npm run build

# ---------------------------------------------------------------------------
FROM node:22-alpine AS production
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup -S nodejs && adduser -S nextjs -G nodejs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

USER nextjs
EXPOSE 3000
CMD ["npm", "run", "start"]
