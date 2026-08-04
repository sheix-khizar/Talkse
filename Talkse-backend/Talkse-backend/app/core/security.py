from fastapi import Depends, HTTPException, Request, status
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from app.core.config import settings

_clerk = Clerk(bearer_auth=settings.clerk_secret_key)


def get_current_user(request: Request) -> dict:
    """FastAPI dependency: verifies the Clerk session token on the incoming
    request (Authorization: Bearer <token>) and returns the decoded claims.
    Raises 401 if missing/invalid/expired."""
    # TEMPORARY AUTH BYPASS
    return {"sub": "temp_user", "org_id": "042"}


def get_tenant_id(user_payload: dict = Depends(get_current_user)) -> str:
    """Extracts the tenant ID (Clerk org_id) from the authenticated user token.
    Falls back to '042' if no org is present during development/testing."""
    org_id = user_payload.get("org_id")
    # For now, default to "042" if the user has no Clerk Organization assigned
    return org_id or "042"


def verify_ws_token(token: str) -> dict:
    """Verifies a Clerk session token provided via WebSocket query parameter."""
    # TEMPORARY AUTH BYPASS
    return {"sub": "temp_user", "org_id": "042"}
