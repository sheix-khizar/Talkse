from fastapi import Depends, HTTPException, Request, status
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from app.core.config import settings

_clerk = Clerk(bearer_auth=settings.clerk_secret_key)


def get_current_user(request: Request) -> dict:
    """FastAPI dependency: verifies the Clerk session token on the incoming
    request (Authorization: Bearer <token>) and returns the decoded claims.
    Raises 401 if missing/invalid/expired."""
    request_state = _clerk.authenticate_request(
        request,
        AuthenticateRequestOptions(
            authorized_parties=[settings.clerk_authorized_party],
        ),
    )
    if not request_state.is_signed_in:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Not authenticated: {request_state.reason}",
        )
    return request_state.payload  # dict with 'sub' (Clerk user id), etc.
