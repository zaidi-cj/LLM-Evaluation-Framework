# Stage 1: Build NextJS application
FROM node:18-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
# Disable NextJS telemetry during builds
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 2: Production runner environment
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy build files and npm assets
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public

EXPOSE 3000

# Start server
CMD ["npm", "run", "start"]
