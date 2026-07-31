from app.services.rag.embeddings import embed_query

def retrieve(tenant_id: str, query: str, api_key: str, top_k: int = 5) -> list[dict]:
    from app.services import db
    query_vec = embed_query(query, api_key)
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT dc.chunk_text, d.title, d.source_url,
                       1 - (dc.embedding <=> %s::vector) AS similarity
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE d.tenant_id = %s
                ORDER BY dc.embedding <=> %s::vector
                LIMIT %s;
            """, (query_vec, tenant_id, query_vec, top_k))
            rows = cur.fetchall()
            return [{"chunk": r[0], "title": r[1], "url": r[2], "score": r[3]} for r in rows]
    finally:
        db.release_connection(conn)
