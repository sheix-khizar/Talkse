"""One-time seed: embeds clinic_data.json's faq[] entries into the
document_chunks table for DEFAULT_TENANT_ID, so RAG has real (fictional)
Bloom Aesthetics content to retrieve instead of scraped third-party data.
Run with: python -m app.services.rag.seed_rag_from_faq
"""
import json
import os
from app.services import db
from app.services.rag.embeddings import embed_document

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "clinic_data.json")

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[Seed RAG] GEMINI_API_KEY not found.")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    tenant_id = db.DEFAULT_TENANT_ID
    for entry in data.get("faq", []):
        source_url = f"internal://faq/{entry['id']}"
        content_hash = entry["id"]  # static content, id is enough to detect "seen before"
        title = entry["question"]

        existing_hash = db.get_document_hash(tenant_id, source_url)
        doc_id = db.upsert_document(tenant_id, source_url, entry.get("category", "faq"), title, content_hash)
        if existing_hash == content_hash:
            continue

        vector = embed_document(entry["answer"], api_key)
        db.insert_chunk(tenant_id, doc_id, entry["answer"], vector)
        print(f"[Seed RAG] Embedded FAQ '{entry['id']}'")

if __name__ == "__main__":
    db.init_rag_tables()
    main()
