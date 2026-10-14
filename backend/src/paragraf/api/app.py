"""HTTP API сервиса.

Сервис ничего не хранит: файл живёт в памяти только на время разбора, карточка
возвращается клиенту и для следующих вопросов присылается обратно.
"""

import asyncio
import base64
import json
from contextlib import asynccontextmanager
from typing import Annotated

import cv2
import structlog
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

from paragraf import __version__, sandbox, selfcheck
from paragraf.api import cards
from paragraf.api.schemas import (
    AnalyzeResponse,
    AskRequest,
    CheckRequest,
    CheckResponse,
    DocTypeInfo,
    FieldInfo,
    Problem,
    RuleInfo,
    SandboxResponse,
)
from paragraf.api.security import RateLimiter, SecurityHeaders
from paragraf.extraction.generic import OTHER_TYPE
from paragraf.imaging.loader import UnsupportedFile
from paragraf.models import Answer
from paragraf.pipeline import Pipeline, TypeNotDetected
from paragraf.settings import Settings, get_settings
from paragraf.speech import MAX_BYTES as SPEECH_MAX_BYTES
from paragraf.speech import SpeechError, SpeechRecognizer

log = structlog.get_logger()

PREVIEW_WIDTH = 1400
MAX_PARALLEL_OCR = 1
"""Разборов одновременно в одном рабочем процессе. Процессов два, ядер у сервиса тоже два,
а один большой документ занимает до гигабайта памяти."""
MAX_FILES = 10
"""Сколько файлов можно прислать как страницы одного документа."""
MAX_WAITING = 6
"""Сколько запросов может ждать распознавания. Остальным сразу отвечаем, что сервис занят,
чтобы очередь и загруженные файлы не копились в памяти."""


def create_app(settings: Settings | None = None, pipeline: Pipeline | None = None) -> FastAPI:
    settings = settings or get_settings()
    limiter = RateLimiter(settings.rate_limit_per_minute)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    speech_limit = SPEECH_MAX_BYTES

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pipeline = pipeline or Pipeline.default(settings)
        app.state.ocr_slots = asyncio.Semaphore(MAX_PARALLEL_OCR)
        app.state.ocr_waiting = 0
        app.state.selfcheck_running = False
        app.state.speech = SpeechRecognizer.load(settings.speech_model)
        yield

    app = FastAPI(
        title="Параграф",
        description="Цифровой секретарь деканата: карточка документа и ответ по Положению.",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(SecurityHeaders)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["content-type"],
        )

    def client_ip(request: Request) -> str:
        # За обратным прокси настоящий адрес приходит в X-Forwarded-For последним.
        forwarded = request.headers.get("x-forwarded-for") if settings.trust_proxy else None
        if forwarded:
            return forwarded.split(",")[-1].strip()
        return request.client.host if request.client else "unknown"

    def rate_limit(request: Request) -> None:
        allowed, retry_after = limiter.allow(client_ip(request))
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Слишком много запросов. Попробуйте чуть позже.",
                headers={"Retry-After": str(retry_after)},
            )

    def get_pipeline(request: Request) -> Pipeline:
        return request.app.state.pipeline

    @asynccontextmanager
    async def ocr_slot(request: Request):
        """Место в очереди на распознавание; при длинной очереди сразу 503."""
        state = request.app.state
        if state.ocr_waiting >= MAX_WAITING:
            raise HTTPException(
                503,
                "Сервис сейчас занят другими документами. Попробуйте через минуту.",
                headers={"Retry-After": "20"},
            )
        state.ocr_waiting += 1
        try:
            await state.ocr_slots.acquire()
        finally:
            state.ocr_waiting -= 1
        try:
            yield
        finally:
            state.ocr_slots.release()

    Limited = Annotated[None, Depends(rate_limit)]
    Service = Annotated[Pipeline, Depends(get_pipeline)]

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {
            400: "bad_request",
            404: "not_found",
            413: "too_large",
            415: "unsupported",
            422: "unprocessable",
            409: "conflict",
            429: "rate_limited",
            503: "busy",
        }
        body = Problem(detail=str(exc.detail), code=codes.get(exc.status_code, "error"))
        return JSONResponse(body.model_dump(), status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        body = Problem(detail="Запрос составлен неверно.", code="unprocessable")
        return JSONResponse(body.model_dump(), status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_error", error=type(exc).__name__, path=request.url.path)
        body = Problem(detail="Внутренняя ошибка сервиса. Попробуйте ещё раз.", code="internal")
        return JSONResponse(body.model_dump(), status_code=500)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/doc-types")
    async def doc_types(service: Service) -> list[DocTypeInfo]:
        return [
            DocTypeInfo(
                id=doc_type.id,
                title=doc_type.title,
                rules=doc_type.rules,
                fields=[
                    FieldInfo(key=f.key, label=f.label, type=f.type, rule=f.rule)
                    for f in doc_type.fields
                ],
            )
            for doc_type in service.registry
        ]

    @app.get("/api/rules")
    async def rules(service: Service) -> list[RuleInfo]:
        return [
            RuleInfo(number=point.number, section=point.section, text=point.text)
            for point in service.rulebook
        ]

    @app.post(
        "/api/analyze",
        responses={
            413: {"model": Problem},
            415: {"model": Problem},
            422: {"model": Problem},
            429: {"model": Problem},
        },
    )
    async def analyze(
        request: Request,
        _: Limited,
        service: Service,
        file: Annotated[
            list[UploadFile],
            File(description="JPG, PNG или PDF; несколько файлов читаются как страницы"),
        ],
        doc_type: Annotated[str | None, Form(max_length=64)] = None,
        question: Annotated[str | None, Form(max_length=500)] = None,
    ) -> AnalyzeResponse:
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes + 64 * 1024:
            raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ.")
        if len(file) > MAX_FILES:
            raise HTTPException(422, f"За один раз можно загрузить до {MAX_FILES} файлов.")
        parts: list[bytes] = []
        for upload in file:
            parts.append(await upload.read(max_bytes + 1))
            if sum(len(part) for part in parts) > max_bytes:
                raise HTTPException(413, f"Файлы вместе больше {settings.max_upload_mb} МБ.")
        data: bytes | list[bytes] = parts[0] if len(parts) == 1 else parts
        type_id = (doc_type or "").strip() or None
        if type_id and type_id not in service.registry:
            raise HTTPException(422, "Неизвестный тип документа.")

        async with ocr_slot(request):
            try:
                processed = await run_in_threadpool(service.analyze, data, type_id)
            except UnsupportedFile as exc:
                raise HTTPException(415, str(exc)) from exc
            except TypeNotDetected as exc:
                raise HTTPException(422, str(exc)) from exc

        analysis = processed.analysis
        asked = question.strip() if question else ""
        answer = await run_in_threadpool(service.ask, analysis, asked, True) if asked else None
        log.info(
            "document_analyzed",
            request_id=request.scope.get("state", {}).get("request_id"),
            document_type=analysis.document_type,
            status=analysis.validation.status,
            kind=analysis.quality.get("file_kind"),
        )
        return AnalyzeResponse(
            analysis=analysis,
            check=service.check(analysis),
            answer=answer,
            image=_preview(processed.image),
        )

    @app.post("/api/ask", responses={422: {"model": Problem}, 429: {"model": Problem}})
    async def ask(_: Limited, service: Service, body: AskRequest) -> Answer:
        if body.document_type == OTHER_TYPE:
            analysis = cards.restore_other(body.fields, body.document_title)
        else:
            if body.document_type not in service.registry:
                raise HTTPException(422, "Неизвестный тип документа.")
            doc_type = service.registry.get(body.document_type)
            analysis = await run_in_threadpool(cards.restore, doc_type, body.fields)
        return await run_in_threadpool(service.ask, analysis, body.question.strip(), True)

    @app.post("/api/check", responses={422: {"model": Problem}, 429: {"model": Problem}})
    async def check(_: Limited, service: Service, body: CheckRequest) -> CheckResponse:
        # У документа незнакомого типа нет обязательных полей: проверять нечего.
        if body.document_type == OTHER_TYPE or body.document_type not in service.registry:
            raise HTTPException(422, "Неизвестный тип документа.")
        doc_type = service.registry.get(body.document_type)
        analysis = await run_in_threadpool(cards.restore, doc_type, body.fields)
        return CheckResponse(
            fields=analysis.fields,
            validation=analysis.validation,
            check=service.check(analysis),
            remarks=analysis.remarks,
        )

    @app.get("/api/selfcheck/available")
    async def selfcheck_available() -> dict[str, bool]:
        return {"available": selfcheck.available(settings.open_set_dir)}

    @app.get("/api/selfcheck")
    async def run_selfcheck(request: Request, _: Limited, service: Service) -> StreamingResponse:
        """Прогон открытого набора с событиями по мере чтения документов (SSE)."""
        if not selfcheck.available(settings.open_set_dir):
            raise HTTPException(404, "Открытый набор не найден.")
        state = request.app.state
        if state.selfcheck_running:
            raise HTTPException(409, "Самопроверка уже идёт. Подождите, пока она закончится.")
        state.selfcheck_running = True
        events = selfcheck.run(service, settings.open_set_dir)

        def advance():
            return next(events, None)

        async def stream():
            try:
                while True:
                    # Каждый документ занимает место в общей очереди распознавания,
                    # чтобы самопроверка не мешала тем, кто проверяет свой документ.
                    async with state.ocr_slots:
                        event = await run_in_threadpool(advance)
                    if event is None:
                        break
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    if await request.is_disconnected():
                        break
            finally:
                state.selfcheck_running = False

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/speech/available")
    async def speech_available(request: Request) -> dict[str, bool]:
        return {"available": request.app.state.speech is not None}

    @app.post("/api/speech", responses={413: {"model": Problem}, 422: {"model": Problem}})
    async def speech(request: Request, _: Limited) -> dict[str, str]:
        """Текст вопроса из короткой записи WAV 16 кГц. Звук нигде не сохраняется."""
        recognizer: SpeechRecognizer | None = request.app.state.speech
        if recognizer is None:
            raise HTTPException(404, "Голосовые вопросы в этой установке выключены.")
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > speech_limit:
                raise HTTPException(413, "Запись слишком длинная.")
        try:
            text = await run_in_threadpool(recognizer.transcribe, bytes(data))
        except SpeechError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"text": text}

    @app.get("/api/sandbox/example")
    async def sandbox_example() -> dict[str, str]:
        return {"text": sandbox.EXAMPLE}

    @app.post(
        "/api/sandbox",
        responses={
            413: {"model": Problem},
            415: {"model": Problem},
            422: {"model": Problem},
            429: {"model": Problem},
        },
    )
    async def try_type(
        request: Request,
        _: Limited,
        service: Service,
        file: Annotated[UploadFile, File(description="JPG, PNG или PDF")],
        config: Annotated[str, Form(max_length=sandbox.MAX_CONFIG_CHARS)],
    ) -> SandboxResponse:
        """Разбор документа по описанию типа, присланному вместе с ним."""
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes + 64 * 1024:
            raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ.")
        try:
            # Разбор YAML в отдельном потоке: даже неудачное описание не держит цикл событий.
            doc_type = await run_in_threadpool(sandbox.parse, config)
        except sandbox.SandboxError as exc:
            raise HTTPException(422, str(exc)) from exc
        data = await file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ.")
        async with ocr_slot(request):
            try:
                processed = await run_in_threadpool(sandbox.run, service, data, doc_type)
            except UnsupportedFile as exc:
                raise HTTPException(415, str(exc)) from exc
        log.info("sandbox_analyzed", fields=len(doc_type.fields))
        return SandboxResponse(analysis=processed.analysis, image=_preview(processed.image))

    return app


def _preview(image) -> str:
    """Снимок для подсветки полей: уменьшенный JPEG в виде data URL."""
    height, width = image.shape[:2]
    if width > PREVIEW_WIDTH:
        scale = PREVIEW_WIDTH / width
        image = cv2.resize(
            image, (PREVIEW_WIDTH, int(height * scale)), interpolation=cv2.INTER_AREA
        )
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buffer.tobytes()).decode("ascii")


app = create_app()
