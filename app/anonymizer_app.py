"""
Guardraill — Anonymizer Service (port 5001)

Endpoints
---------
GET  /health      — liveness check
POST /anonymize   — detect and mask PII, return anonymised text
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from app.audit import emit_error, emit_pii_anonymized, summarize_entities
from app.config import DEFAULT_OPERATORS
from app.context import get_request_context
from app.engine import analyzer, anonymizer
from app.logging_config import setup_logging
from app.middleware import RequestContextMiddleware
from app.models import AnonymizeRequest, AnonymizeResponse

setup_logging()
logger = logging.getLogger(__name__)

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Guardraill anonymizer service starting",
        extra={"service_version": VERSION, "event_type": "SERVICE_START"},
    )
    yield
    logger.info(
        "Guardraill anonymizer service stopped",
        extra={"event_type": "SERVICE_STOP"},
    )


app = FastAPI(
    title="Guardraill Anonymizer",
    description="Ukrainian / Russian / English PII masking service powered by Microsoft Presidio.",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "version": VERSION, "service": "anonymizer"}


@app.post("/anonymize", response_model=AnonymizeResponse, tags=["pii"])
def anonymize_text(request: AnonymizeRequest, http_request: Request) -> AnonymizeResponse:
    """
    Analyse *text* and return a version with all detected PII replaced /
    masked according to the default operator configuration.
    """
    ctx = get_request_context()
    start = time.monotonic()

    try:
        raw_results = analyzer.analyze(
            text=request.text,
            language=request.language,
            score_threshold=request.score_threshold,
        )
    except Exception as exc:
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        emit_error(
            ctx,
            method=http_request.method,
            path=http_request.url.path,
            error=str(exc),
            duration_ms=duration_ms,
        )
        logger.exception("Analysis failed during anonymization")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    entity_summary = summarize_entities(raw_results)

    if not raw_results:
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        emit_pii_anonymized(
            ctx,
            language=request.language,
            text_length=len(request.text),
            score_threshold=request.score_threshold,
            pii_detected=False,
            total_entities=0,
            entity_summary=[],
            duration_ms=duration_ms,
        )
        return AnonymizeResponse(anonymized_text=request.text, entities_found=0)

    try:
        anon_result = anonymizer.anonymize(
            text=request.text,
            analyzer_results=raw_results,
            operators=DEFAULT_OPERATORS,
        )
    except Exception as exc:
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        emit_error(
            ctx,
            method=http_request.method,
            path=http_request.url.path,
            error=str(exc),
            duration_ms=duration_ms,
        )
        logger.exception("Anonymization failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    duration_ms = round((time.monotonic() - start) * 1000, 2)
    emit_pii_anonymized(
        ctx,
        language=request.language,
        text_length=len(request.text),
        score_threshold=request.score_threshold,
        pii_detected=True,
        total_entities=len(raw_results),
        entity_summary=entity_summary,
        duration_ms=duration_ms,
    )

    return AnonymizeResponse(
        anonymized_text=anon_result.text,
        entities_found=len(raw_results),
    )
