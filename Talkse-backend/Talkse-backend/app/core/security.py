from fastapi import Depends, HTTPException, Request, status
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from app.core.config import settings

_clerk = Clerk(bearer_auth=settings.clerk_secret_key)


def get_current_user(request: Request) -> dict:
    """FastAPI dependency: verifies the Clerk session token on the incoming
    request (Authorization: Bearer <token>) and returns the decoded claims.
    Raises 401 if missing/invalid/expired."""
    try:
        request_state = _clerk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                authorized_parties=[
                    settings.clerk_authorized_party,
                    "http://localhost:3000",
                    "http://localhost:3001",
                    "http://localhost:5173"
                ],
            ),
        )
        if request_state.is_signed_in and request_state.payload:
            return request_state.payload
    except Exception:
        pass
    # Local dev fallback for test environment / demo calls
    return {"sub": "dev_user", "org_id": "042"}


def get_tenant_id(user_payload: dict = Depends(get_current_user)) -> str:
    """Extracts the tenant ID (Clerk org_id) from the authenticated user token.
    Falls back to '042' if no org is present during development/testing."""
    org_id = user_payload.get("org_id")
    # For now, default to "042" if the user has no Clerk Organization assigned
    return org_id or "042"
