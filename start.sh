#!/usr/bin/env sh
# Запуск одной командой: собирает и поднимает сервис, ждёт готовности и открывает браузер.
# Остановить: docker compose down. Другой порт: HTTP_PORT=8090 ./start.sh
set -e
cd "$(dirname "$0")"
PORT="${HTTP_PORT:-8080}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Нужен Docker: https://docs.docker.com/get-docker/"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker установлен, но не запущен. Запустите его и повторите."
  exit 1
fi

docker compose up -d --build
echo "Жду, пока сервис запустится..."
i=0
while [ "$i" -lt 120 ]; do
  if curl -fs "http://localhost:$PORT/api/health" >/dev/null 2>&1; then
    echo "Готово: http://localhost:$PORT"
    (xdg-open "http://localhost:$PORT" || open "http://localhost:$PORT") >/dev/null 2>&1 || true
    exit 0
  fi
  i=$((i + 1))
  sleep 2
done
echo "Сервис не ответил за 4 минуты. Журнал: docker compose logs"
exit 1
