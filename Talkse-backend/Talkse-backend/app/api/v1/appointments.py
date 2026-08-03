from fastapi import APIRouter, Depends
from psycopg2.extras import RealDictCursor
from app.services import db
from app.core.security import get_tenant_id

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

@router.get("/")
def list_appointments(tenant_id: str = Depends(get_tenant_id)):
    rows = db.list_appointments_for_tenant(tenant_id)
    # Convert UUID and datetime to string to ensure JSON serialization
    for row_dict in rows:
        if 'id' in row_dict and row_dict['id']:
            row_dict['id'] = str(row_dict['id'])
        if 'scheduled_start' in row_dict and row_dict['scheduled_start']:
            row_dict['scheduled_start'] = row_dict['scheduled_start'].isoformat()
        if 'scheduled_end' in row_dict and row_dict['scheduled_end']:
            row_dict['scheduled_end'] = row_dict['scheduled_end'].isoformat()
        if 'created_at' in row_dict and row_dict['created_at']:
            row_dict['created_at'] = row_dict['created_at'].isoformat()
        if 'updated_at' in row_dict and row_dict['updated_at']:
            row_dict['updated_at'] = row_dict['updated_at'].isoformat()
    return rows
