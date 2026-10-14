"""HTTP API сервиса.

Сервис ничего не хранит: файл живёт в памяти только на время разбора, карточка
возвращается клиенту и для следующих вопросов присылается обратно.
"""

import asyncio
import base64
from contextlib import asynccontextmanager
from typing import Annotated

import cv2
import structlog
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from paragraf import __version__, sandbox
from paragraf.api.schemas import (
    AnalyzeResponse,
    AskRequest,
    DocTypeInfo,
    FieldInfo,
    Problem,
    RuleInfo,
    SandboxResponse,
)
from paragraf.api.security import RateLimiter, SecurityHeaders
from paragraf.extraction.generic import OTHER_TYPE
from paragraf.imaging.loader import UnsupportedFile
from paragraf.models import Analysis, Answer, FieldValue, Validation
from paragraf.pipeline import Pipeline, TypeNotDetected
from paragraf.rules.validate import validate
from paragraf.settings import Settings, get_settings
from paragraf.textnorm import NOT_FOUND

log = structlog.get_logger()

PREVIEW_WIDTH = 1400
MAX_PARALLEL_OCR = 2


def create_app(settings: Settings | None = None, pipeline: Pipeline | None = None) -> FastAPI:
    settings = settings or get_settings()
    limiter = RateLimiter(settings.rate_limit_per_minute)
    max_bytes = settings.max_upload_mb * 1024 * 1024

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.pipeline = pipeline or Pipeline.default(settings)
        app.state.ocr_slots = asyncio.Semaphore(MAX_PARALLEL_OCR)
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
            429: "rate_limited",
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
        file: Annotated[UploadFile, File(description="JPG, PNG или одностраничный PDF")],
        doc_type: Annotated[str | None, Form(max_length=64)] = None,
        question: Annotated[str | None, Form(max_length=500)] = None,
    ) -> AnalyzeResponse:
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes + 64 * 1024:
            raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ.")
        data = await file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ.")
        type_id = (doc_type or "").strip() or None
        if type_id and type_id not in service.registry:
            raise HTTPException(422, "Неизвестный тип документа.")

        async with request.app.state.ocr_slots:
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
            # Документ незнакомого типа: карточка состоит из строк, найденных на снимке.
            generic = [
                FieldValue(
                    key=item.key,
                    label=(item.label or item.key)[:120],
                    type="text",
                    value=str(item.value)[:300],
                    found=True,
                    origin="generic",
                )
                for item in body.fields
                if isinstance(item.value, str) and item.value.strip()
            ]
            other = Analysis(
                document_type=OTHER_TYPE,
                document_title=(body.document_title or "Документ").strip()[:120],
                supported=False,
                type_detected=True,
                ocr_engine="client",
                text="",
                fields=generic,
                validation=Validation(status="not_applicable", missing_fields=[], sources=[]),
                width=0,
                height=0,
            )
            return await run_in_threadpool(service.ask, other, body.question.strip(), True)
        if body.document_type not in service.registry:
            raise HTTPException(422, "Неизвестный тип документа.")
        doc_type = service.registry.get(body.document_type)
        sent = {item.key: item for item in body.fields}
        fields: list[FieldValue] = []
        for spec in doc_type.fields:
            item = sent.get(spec.key)
            if spec.is_mark:
                present = bool(item and item.value is True)
                fields.append(
                    FieldValue(
                        key=spec.key,
                        label=spec.label,
                        type=spec.type,
                        value=present,
                        found=present,
                        rule=spec.rule,
                    )
                )
                continue
            value = str(item.value).strip()[:300] if item and isinstance(item.value, str) else ""
            found = bool(value) and value != NOT_FOUND
            fields.append(
                FieldValue(
                    key=spec.key,
                    label=spec.label,
                    type=spec.type,
                    value=value if found else NOT_FOUND,
                    found=found,
                    rule=spec.rule,
                )
            )
        analysis = Analysis(
            document_type=doc_type.id,
            document_title=doc_type.title,
            type_detected=False,
            ocr_engine="client",
            text="",
            fields=fields,
            validation=validate(doc_type, fields),
            width=0,
            height=0,
        )
        return await run_in_threadpool(service.ask, analysis, body.question.strip(), True)

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
            doc_type = sandbox.parse(config)
        except sandbox.SandboxError as exc:
            raise HTTPException(422, str(exc)) from exc
        data = await file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ.")
        async with request.app.state.ocr_slots:
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
