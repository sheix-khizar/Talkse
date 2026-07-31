from fastapi import APIRouter, Depends
from psycopg2.extras import RealDictCursor
from app.services import db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])

@router.get("/")
def list_appointments(user: dict = Depends(get_current_user)):
    conn = db.get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM appointments ORDER BY created_at DESC;")
            # Convert UUID and datetime to string to ensure JSON serialization
            rows = []
            for row in cur.fetchall():
                row_dict = dict(row)
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
                rows.append(row_dict)
            return rows
    finally:
        db.release_connection(conn)
