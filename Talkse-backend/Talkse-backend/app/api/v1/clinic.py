from fastapi import APIRouter
from app.services import clinic_config as config

router = APIRouter(prefix="/api/v1/clinic", tags=["clinic"])

@router.get("/services")
def get_services():
    return config.SERVICES

@router.get("/providers")
def get_providers():
    return config.PROVIDERS
