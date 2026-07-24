def chunk_text(text: str, max_words: int = 250, overlap: int = 40) -> list[str]:
    words = text.split()
    chunks = []
    step = max_words - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + max_words])
        if chunk.strip():
            chunks.append(chunk)
    return chunks
