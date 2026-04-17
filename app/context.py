"""
Request-scoped context stored in a ContextVar so any code in the call stack
can read user/session metadata without threading through function arguments.
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RequestContext:
    # Core request identity
    request_id: str
    client_ip: str
    user_agent: str = ""

    # Source detection: "litellm" when LiteLLM proxy headers are present,
    # "direct" for plain curl / SDK calls.
    source: str = "direct"

    # ── LiteLLM-specific headers ──────────────────────────────────────────
    # Sent by the LiteLLM proxy when it forwards requests to guardrails.
    litellm_user_id: Optional[str] = None       # x-litellm-user-id
    litellm_call_id: Optional[str] = None       # x-litellm-call-id
    litellm_team_id: Optional[str] = None       # x-litellm-team-id
    litellm_org_id: Optional[str] = None        # x-litellm-organization-id
    litellm_model: Optional[str] = None         # x-litellm-model
    litellm_key_hash: Optional[str] = None      # x-litellm-proxy-api-key-hash

    # ── Direct-request headers ────────────────────────────────────────────
    # Only the last 8 characters of the key are stored (never the full secret).
    api_key_id: Optional[str] = None            # suffix of X-API-Key / Bearer token


_request_ctx: ContextVar[Optional[RequestContext]] = ContextVar(
    "request_ctx", default=None
)


def get_request_context() -> Optional[RequestContext]:
    """Return the RequestContext bound to the current async task, or None."""
    return _request_ctx.get()


def set_request_context(ctx: RequestContext) -> None:
    """Bind a RequestContext to the current async task."""
    _request_ctx.set(ctx)
