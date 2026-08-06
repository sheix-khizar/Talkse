# Stage 1: Build Vite React application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package manifests and install dependencies
COPY package*.json ./
RUN npm ci

# Accept build arguments for frontend environment variables
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

# Copy frontend source code and build production bundle
COPY . .
RUN npm run build

# Stage 2: Serve static build with Nginx
FROM nginx:alpine

# Copy custom Nginx reverse proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
