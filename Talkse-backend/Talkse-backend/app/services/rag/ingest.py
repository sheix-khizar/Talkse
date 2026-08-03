import os
import hashlib
from dotenv import load_dotenv

from app.services.rag.clean import extract_clean_text
from app.services.rag.chunk import chunk_text
from app.services.rag.embeddings import embed_document
from app.services import db

load_dotenv()

def ingest_folder(clean_text_dir: str, api_key: str, tenant_id: str = db.DEFAULT_TENANT_ID):
    if not os.path.exists(clean_text_dir):
        print(f"[Ingest] Directory not found: {clean_text_dir}")
        return
        
    for category in os.listdir(clean_text_dir):
        cat_path = os.path.join(clean_text_dir, category)
        if not os.path.isdir(cat_path):
            continue
        for fname in os.listdir(cat_path):
            fpath = os.path.join(cat_path, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()

            content_hash = hashlib.sha256(text.encode()).hexdigest()
            source_url = f"https://www.bloomaesthetics.com/{category}/{fname.replace('.txt', '')}"
            title = fname.replace(".txt", "").replace("_", " ").title()

            existing_hash = db.get_document_hash(tenant_id, source_url)
            doc_id = db.upsert_document(tenant_id, source_url, category, title, content_hash)

            if existing_hash == content_hash:
                print(f"[Ingest] {fname} unchanged — skipping re-embedding.")
                continue

            for chunk in chunk_text(text):
                vector = embed_document(chunk, api_key)
                db.insert_chunk(tenant_id, doc_id, chunk, vector)

            print(f"[Ingest] {fname} -> {doc_id}")

if __name__ == "__main__":
    db.init_rag_tables()
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        ingest_folder("data/clean_text", api_key)
    else:
        print("[Ingest] GEMINI_API_KEY not found.")
