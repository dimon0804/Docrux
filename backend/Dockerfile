# syntax=docker/dockerfile:1.7
# Собирается из корня репозитория: docker build -f backend/Dockerfile .

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS base
ARG APT_MIRROR=deb.debian.org
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
RUN sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-rus libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Точная модель русского языка. Версия закреплена коммитом и контрольной суммой.
ARG TESSDATA_COMMIT=e12c65a915945e4c28e237a9b52bc4a8f39a0cec
ADD --checksum=sha256:b617eb6830ffabaaa795dd87ea7fd251adfe9cf0efe05eb9a2e8128b7728d6b6 \
    --chmod=644 \
    https://github.com/tesseract-ocr/tessdata_best/raw/${TESSDATA_COMMIT}/rus.traineddata \
    /usr/share/tessdata_best/rus.traineddata


FROM base AS build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /src
COPY backend/pyproject.toml ./
COPY backend/src ./src
RUN pip install .


FROM base AS runtime
LABEL org.opencontainers.image.title="Параграф API" \
      org.opencontainers.image.description="Цифровой секретарь деканата" \
      org.opencontainers.image.licenses="MIT"
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=build /opt/venv /opt/venv
COPY config /app/config
ENV PATH="/opt/venv/bin:$PATH" \
    PARAGRAF_CONFIG_DIR=/app/config \
    PARAGRAF_TESSDATA=/usr/share/tessdata_best \
    OMP_THREAD_LIMIT=1 \
    TMPDIR=/tmp
WORKDIR /app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "paragraf.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--no-server-header", "--timeout-keep-alive", "15"]
