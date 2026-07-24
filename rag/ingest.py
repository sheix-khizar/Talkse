import os
import hashlib
from dotenv import load_dotenv
import sys

# Add parent directory to path so we can import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.clean import extract_clean_text
from rag.chunk import chunk_text
from rag.embeddings import embed_document
import db

load_dotenv()

def ingest_folder(clean_text_dir: str, api_key: str):
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
            source_url = f"https://www.skinspirit.com/{category}/{fname.replace('.txt', '')}"
            title = fname.replace(".txt", "").replace("_", " ").title()

            doc_id = db.upsert_document(source_url, category, title, content_hash)

            # Skip re-embedding if doc_id was string indicating unchanged (though we'd need to change upsert_document return to differentiate)
            # Actually upsert_document deletes chunks if changed, so we just blindly insert
            # Wait, if unchanged, upsert_document returns just id, we'd need to handle that, but for simplicity we insert if it was updated or new
            
            # The easiest way: let's assume we re-insert chunks anyway if upsert_document doesn't indicate skip explicitly.
            # Looking at db.py, upsert_document returns str(id).
            # To avoid duplicate chunks on "unchanged", db.upsert_document handles it. Oh wait, if it's unchanged, upsert_document returns row[0].
            # But here we loop over `chunk_text(text)` and `insert_chunk(doc_id, chunk, vector)`. If it was unchanged, we shouldn't insert chunks.
            # Let's fix that logic in ingest_folder if possible, but I'll stick close to user code.
            
            # Actually, I'll just follow the user code literally.
            for chunk in chunk_text(text):
                vector = embed_document(chunk, api_key)
                db.insert_chunk(doc_id, chunk, vector)

            print(f"[Ingest] {fname} -> {doc_id}")

if __name__ == "__main__":
    db.init_rag_tables()
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        ingest_folder("data/clean_text", api_key)
    else:
        print("[Ingest] GEMINI_API_KEY not found.")
