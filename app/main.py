"""
Guardraill — Ukrainian PII Guardrail Service
============================================

Endpoints
---------
GET  /health      — liveness check
POST /analyze     — detect PII entities and return positions + scores
POST /anonymize   — detect and mask PII, return anonymised text
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from presidio_anonymizer.entities import OperatorConfig

from app.config import DEFAULT_OPERATORS, DEFAULT_SCORE_THRESHOLD
from app.engine import analyzer, anonymizer
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnonymizeRequest,
    AnonymizeResponse,
    EntityResult,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Guardraill service starting (version %s)", VERSION)
    yield
    logger.info("Guardraill service stopped")


app = FastAPI(
    title="Guardraill",
    description="Ukrainian PII detection and masking service powered by Microsoft Presidio.",
    version=VERSION,
    lifespan=lifespan,
)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "version": VERSION}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["pii"])
def analyze_text(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyse *text* and return all detected PII entities with their
    character offsets and confidence scores.
    """
    try:
        raw_results = analyzer.analyze(
            text=request.text,
            language=request.language,
            entities=request.entities,
            score_threshold=request.score_threshold,
        )
    except Exception as exc:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    results = [
        EntityResult(
            entity_type=r.entity_type,
            start=r.start,
            end=r.end,
            score=round(r.score, 4),
            text=request.text[r.start : r.end],
        )
        for r in raw_results
    ]

    return AnalyzeResponse(results=results, total=len(results))


@app.post("/anonymize", response_model=AnonymizeResponse, tags=["pii"])
def anonymize_text(request: AnonymizeRequest) -> AnonymizeResponse:
    """
    Analyse *text* and return a version with all detected PII replaced /
    masked according to the default operator configuration.
    """
    try:
        raw_results = analyzer.analyze(
            text=request.text,
            language=request.language,
            score_threshold=request.score_threshold,
        )
    except Exception as exc:
        logger.exception("Analysis failed during anonymization")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not raw_results:
        return AnonymizeResponse(
            anonymized_text=request.text,
            entities_found=0,
        )

    try:
        anon_result = anonymizer.anonymize(
            text=request.text,
            analyzer_results=raw_results,
            operators=DEFAULT_OPERATORS,
        )
    except Exception as exc:
        logger.exception("Anonymization failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AnonymizeResponse(
        anonymized_text=anon_result.text,
        entities_found=len(raw_results),
    )
