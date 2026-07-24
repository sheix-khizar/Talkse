import os
import sys
from dotenv import load_dotenv
from google import genai

# Add parent directory to path so we can import modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retriever import retrieve

load_dotenv()

def answer_question(question: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    results = retrieve(question, api_key, top_k=2)

    context_block = "\n\n---\n\n".join(r["chunk"] for r in results)

    system_prompt = (
        "You are a phone receptionist for SkinSpirit, speaking OUT LOUD to a caller — "
        "not writing a webpage. Follow these rules strictly:\n"
        "1. Answer in 1-2 short spoken sentences MAX, like a real receptionist would on a call.\n"
        "2. NEVER read out bullet lists, multiple service names, or full menus. "
        "If the caller asks a yes/no question ('do you offer X'), just say yes or no, "
        "then ask ONE natural follow-up question (e.g. what day works for them).\n"
        "3. Only mention specific details (prices, durations, specific treatment names) "
        "if the caller explicitly asked for that detail.\n"
        "4. Never say phrases like 'according to our website' or 'our services include' "
        "followed by a list — speak like a person, not a document reader.\n"
        "5. Use ONLY the provided context for facts. If you don't know, say so briefly "
        "and offer to have someone call them back.\n"
        "6. Do not use markdown, bullet points, or numbered lists — this is spoken audio."
    )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=f"Context:\n{context_block}\n\nQuestion: {question}",
        config={
            "system_instruction": system_prompt,
            "temperature": 0.3,
            "max_output_tokens": 80
        }
    )

    sources = list({(r["title"], r["url"]) for r in results})  # dedupe

    return {
        "answer": response.text,
        "sources": [{"title": t, "url": u} for t, u in sources]
    }

if __name__ == "__main__":
    result = answer_question("What is Botox?")
    print(result["answer"])
    print("\nSources:")
    for s in result["sources"]:
        print(f"  ✓ {s['title']} — {s['url']}")
