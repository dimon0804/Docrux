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
# У бинарника в базовом образе есть привилегия на привязку к портам ниже 1024. Сервис слушает 8080,
# поэтому снимаем её: без этого контейнер не запустится со сброшенными привилегиями.
RUN cp /usr/bin/caddy /tmp/caddy \
    && mv -f /tmp/caddy /usr/bin/caddy \
    && caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
# Caddy работает от непривилегированного пользователя и пишет служебные файлы только в /tmp.
ENV XDG_CONFIG_HOME=/tmp/caddy/config \
    XDG_DATA_HOME=/tmp/caddy/data
USER 65532:65532
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD ["wget", "-q", "--spider", "http://127.0.0.1:8080/healthz"]
