# Запуск двойным кликом по start.cmd: собирает и поднимает сервис, ждёт готовности и открывает браузер.
# Остановить: docker compose down. Другой порт: задайте HTTP_PORT перед запуском.
# Docker пишет ход сборки в stderr: в Windows PowerShell 5.1 это не должно считаться ошибкой.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$port = if ($env:HTTP_PORT) { $env:HTTP_PORT } else { "8080" }

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Нужен Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker Desktop установлен, но не запущен. Запустите его, дождитесь Engine running и повторите."
    exit 1
}

docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "Жду, пока сервис запустится..."
for ($i = 0; $i -lt 120; $i++) {
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://localhost:$port/api/health" -ErrorAction Stop | Out-Null
        Write-Host "Готово: http://localhost:$port"
        if (-not $env:DOCRUX_NO_BROWSER) { Start-Process "http://localhost:$port" }
        exit 0
    } catch {
        Start-Sleep -Seconds 2
    }
}
Write-Host "Сервис не ответил за 4 минуты. Журнал: docker compose logs"
exit 1
