"""
Request context middleware.

Responsibilities
----------------
1. Extract user/session identity from request headers (LiteLLM + direct).
2. Generate / propagate a ``X-Request-ID`` header.
3. Bind a ``RequestContext`` to the current async task via ContextVar.
4. Emit ``REQUEST_RECEIVED`` and ``REQUEST_COMPLETED`` audit events.
5. Echo ``X-Request-ID`` back in the response for client-side correlation.

LiteLLM header mapping
-----------------------
Header                          → RequestContext field
------------------------------------------------------
x-litellm-user-id               litellm_user_id
x-litellm-call-id               litellm_call_id
x-litellm-team-id               litellm_team_id
x-litellm-organization-id       litellm_org_id
x-litellm-model                 litellm_model
x-litellm-proxy-api-key-hash    litellm_key_hash

Direct-request header mapping
------------------------------
X-Request-ID      → request_id (generated if absent)
X-API-Key         → api_key_id (last 8 chars only, never the full value)
Authorization     → api_key_id (Bearer token suffix, last 8 chars)
X-Forwarded-For   → client_ip (first IP in the chain)
X-Real-IP         → client_ip (fallback)
CF-Connecting-IP  → client_ip (Cloudflare)
"""

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.audit import emit_request_completed, emit_request_received
from app.context import RequestContext, set_request_context

# LiteLLM header name → RequestContext field name
_LITELLM_HEADER_MAP: dict[str, str] = {
    "x-litellm-user-id":            "litellm_user_id",
    "x-litellm-call-id":            "litellm_call_id",
    "x-litellm-team-id":            "litellm_team_id",
    "x-litellm-organization-id":    "litellm_org_id",
    "x-litellm-model":              "litellm_model",
    "x-litellm-proxy-api-key-hash": "litellm_key_hash",
}


def _get_client_ip(request: Request) -> str:
    """
    Resolve the real client IP, respecting common reverse-proxy headers.

    Priority: X-Forwarded-For → X-Real-IP → CF-Connecting-IP → socket peer
    """
    for header in ("x-forwarded-for", "x-real-ip", "cf-connecting-ip"):
        value = request.headers.get(header, "").strip()
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _extract_context(request: Request) -> RequestContext:
    """Parse all relevant headers and build a RequestContext."""
    # Prefer the LiteLLM call-id as the canonical request ID so log entries
    # can be joined with LiteLLM's own logs.
    request_id = (
        request.headers.get("x-litellm-call-id")
        or request.headers.get("x-request-id")
        or str(uuid.uuid4())
    )

    # Detect whether this request is coming through a LiteLLM proxy
    is_litellm = any(h in request.headers for h in _LITELLM_HEADER_MAP)

    # Extract LiteLLM headers
    litellm_fields: dict[str, str] = {}
    for header, field_name in _LITELLM_HEADER_MAP.items():
        value = request.headers.get(header)
        if value:
            litellm_fields[field_name] = value

    # Mask the API key — store only the last 8 characters
    raw_key = (
        request.headers.get("x-api-key", "")
        or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    )
    api_key_id = f"...{raw_key[-8:]}" if len(raw_key) >= 8 else (raw_key or None)

    return RequestContext(
        request_id=request_id,
        client_ip=_get_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        source="litellm" if is_litellm else "direct",
        api_key_id=api_key_id,
        **litellm_fields,
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that sets up per-request audit context and emits
    lifecycle audit events for every HTTP request.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        ctx = _extract_context(request)
        set_request_context(ctx)

        method = request.method
        path = request.url.path
        start = time.monotonic()

        emit_request_received(ctx, method=method, path=path)

        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
        finally:
            duration_ms = round((time.monotonic() - start) * 1000, 2)
            emit_request_completed(
                ctx,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )

        # Echo the request-id back so clients can correlate with server logs
        response.headers["X-Request-ID"] = ctx.request_id
        return response
