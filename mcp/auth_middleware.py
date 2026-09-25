"""ASGI middleware enforcing bearer-token auth on the streamable-HTTP app.

Wraps the Starlette app MCPServer.streamable_http_app() returns, rather than
using the SDK's built-in OAuth resource-server support (AuthSettings /
TokenVerifier) — that's a full OAuth flow, more than a single-user, static-
token setup needs.
"""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from common.auth import check_token, mcp_access_level, parse_bearer


class BearerAuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        raw = headers.get(b"authorization", b"").decode("latin-1")
        level = check_token(parse_bearer(raw))
        if level is None:
            response = JSONResponse({"error": "Missing or invalid bearer token"}, status_code=401)
            await response(scope, receive, send)
            return

        reset_token = mcp_access_level.set(level)
        try:
            await self.app(scope, receive, send)
        finally:
            mcp_access_level.reset(reset_token)
