# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build


FROM caddy:2-alpine AS runtime
LABEL org.opencontainers.image.title="Параграф Web" \
      org.opencontainers.image.licenses="MIT"
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /web/dist /srv
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD ["wget", "-q", "--spider", "http://127.0.0.1:8080/healthz"]
