# Multi-stage Dockerfile for notification server
ARG NODE_VERSION=20-alpine

# Base stage with common dependencies
FROM node:${NODE_VERSION} AS base
RUN apk add --no-cache curl tini

# Dependencies stage
FROM base AS dependencies
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Development dependencies
FROM dependencies AS dev-dependencies
RUN npm ci

# Development stage
FROM dev-dependencies AS development
WORKDIR /app
COPY . .
EXPOSE 3001
CMD ["npm", "run", "dev"]

# Build stage
FROM dev-dependencies AS builder
COPY . .
RUN npm run build

# Production stage
FROM base AS production
WORKDIR /app

# Create non-root user for security
RUN addgroup -g 1001 notifier && \
    adduser -D -u 1001 -G notifier notifier

# Copy production dependencies
COPY --from=dependencies /app/node_modules ./node_modules

# Copy built application
COPY --from=builder /app/dist ./dist
COPY package*.json ./

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs && \
    chown -R notifier:notifier /app

# Switch to non-root user
USER notifier

# Expose port
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Start the server
CMD ["node", "dist/server.js"]