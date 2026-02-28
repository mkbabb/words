# syntax=docker/dockerfile:1
ARG NODE_VERSION=20-alpine
FROM node:${NODE_VERSION} AS base

# Dependencies stage
FROM base AS dependencies
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies with cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm install --production --legacy-peer-deps

# Development dependencies stage
FROM base AS dev-dependencies
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies with cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm install --legacy-peer-deps

# Development stage
FROM base AS development
WORKDIR /app

# Copy package.json for npm scripts
COPY package*.json ./

# Copy dependencies
COPY --from=dev-dependencies /app/node_modules ./node_modules
# Don't copy source files - they'll be mounted via volume

# Environment for hot reloading
ENV CHOKIDAR_USEPOLLING=true
ENV VITE_HOST=0.0.0.0

EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

# Build stage
FROM base AS build
WORKDIR /app

# Copy dependencies and source
COPY --from=dev-dependencies /app/node_modules ./node_modules
COPY . .

# Build arguments for environment variables
ARG VITE_API_URL
ARG VITE_APP_TITLE="Floridify"
ARG VITE_VAPID_PUBLIC_KEY
ARG VITE_BASE_PATH="/"
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_APP_TITLE=${VITE_APP_TITLE}
ENV VITE_VAPID_PUBLIC_KEY=${VITE_VAPID_PUBLIC_KEY}
ENV VITE_BASE_PATH=${VITE_BASE_PATH}

# Build the application
RUN npm run build

# Production stage with nginx
FROM nginx:alpine AS production

# Install runtime dependencies
RUN apk add --no-cache curl

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application
COPY --from=build /app/dist /usr/share/nginx/html

# Copy and set up environment injection script
COPY docker-entrypoint.sh /docker-entrypoint.d/40-envsubst.sh
RUN chmod +x /docker-entrypoint.d/40-envsubst.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]