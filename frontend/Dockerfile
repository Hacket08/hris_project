FROM node:22-slim AS base
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# --- dev: used by docker-compose for local development (ng serve, live reload) ---
FROM base AS dev
COPY . .
EXPOSE 4200
CMD ["npm", "run", "start", "--", "--host", "0.0.0.0"]

# --- build: production Angular bundle ---
FROM base AS build
COPY . .
RUN npm run build -- --configuration production

# --- production: static bundle served by nginx ---
FROM nginx:1.27-alpine AS production
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
