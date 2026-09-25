"""Extension-only authentication route adapter."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from ..services.extension_auth import (
    ExtensionAuthConfig,
    ExtensionAuthError,
    ExtensionAuthService,
)


def authenticate_extension_payload(
    payload: Any,
    service: ExtensionAuthService,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ExtensionAuthError("A JSON object is required")

    return service.authenticate(payload.get("accessToken", ""))


def register_extension_routes(
    router: Any,
    service: ExtensionAuthService | None = None,
) -> Any:
    """Register POST /api/extension/auth."""

    @router.post("/api/extension/auth")
    async def extension_auth(request: Request) -> dict[str, Any]:
        try:
            payload = await request.json()

            auth_service = (
                service
                or ExtensionAuthService(
                    ExtensionAuthConfig.from_environment()
                )
            )

            return authenticate_extension_payload(
                payload,
                auth_service,
            )

        except ExtensionAuthError as exc:
            raise HTTPException(
                status_code=401,
                detail=str(exc),
            ) from exc

        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=str(exc),
            ) from exc

    return router
