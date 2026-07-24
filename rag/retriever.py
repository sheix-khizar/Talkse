import os
import sys

# Add parent directory to path so we can import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.embeddings import embed_query

def retrieve(query: str, api_key: str, top_k: int = 5) -> list[dict]:
    import db
    query_vec = embed_query(query, api_key)
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT dc.chunk_text, d.title, d.source_url,
                       1 - (dc.embedding <=> %s::vector) AS similarity
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                ORDER BY dc.embedding <=> %s::vector
                LIMIT %s;
            """, (query_vec, query_vec, top_k))
            rows = cur.fetchall()
            return [{"chunk": r[0], "title": r[1], "url": r[2], "score": r[3]} for r in rows]
    finally:
        conn.close()
