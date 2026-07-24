from google import genai
from google.genai import types

_gemini_client = None

def get_client(api_key: str):
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client

def embed_document(text: str, api_key: str) -> list[float]:
    client = get_client(api_key)
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=768, task_type="RETRIEVAL_DOCUMENT")
    )
    return result.embeddings[0].values

def embed_query(text: str, api_key: str) -> list[float]:
    client = get_client(api_key)
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=768, task_type="RETRIEVAL_QUERY")
    )
    return result.embeddings[0].values
