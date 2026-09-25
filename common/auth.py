"""Static bearer-token auth, shared by the capture API and the MCP server.

Deliberately not OAuth: single user on a private network, two long-lived tokens.
See README.md's Authentication section for why.
"""

import hmac
import os
from contextvars import ContextVar
from typing import Literal

AccessLevel = Literal["read", "write"]

_READ_TOKEN = os.environ.get("OPENBRAIN_READ_TOKEN", "")
_WRITE_TOKEN = os.environ.get("OPENBRAIN_WRITE_TOKEN", "")

if not _READ_TOKEN or not _WRITE_TOKEN:
    raise RuntimeError(
        "OPENBRAIN_READ_TOKEN and OPENBRAIN_WRITE_TOKEN must both be set "
        "(non-empty) in the environment. Refusing to start with auth "
        "silently disabled — generate tokens with `openssl rand -hex 32` "
        "and set them in .env."
    )


def parse_bearer(header_value: str | None) -> str | None:
    """Pull the token out of an `Authorization: Bearer <token>` header value."""
    if not header_value:
        return None
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def check_token(token: str | None) -> AccessLevel | None:
    """Classify a bearer token. The write token also grants read access."""
    if not token:
        return None
    # Compare both, in fixed order, so a read-token guess doesn't take a
    # different code path (and thus timing) than a write-token guess.
    if hmac.compare_digest(token, _WRITE_TOKEN):
        return "write"
    if hmac.compare_digest(token, _READ_TOKEN):
        return "read"
    return None


# Set by the MCP server's ASGI auth middleware for the lifetime of one HTTP
# request, read by tools (capture) that need write access specifically.
# MCP funnels every tool call through a single route, so a per-route check
# like the capture API's isn't possible — this is the per-tool equivalent.
mcp_access_level: ContextVar["AccessLevel | None"] = ContextVar("mcp_access_level", default=None)
