import os
from dotenv import load_dotenv
from google import genai

load_dotenv(dotenv_path="src/.env")

API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")


client = genai.Client(api_key=API_KEY)

COMPLEX_KEYWORDS = {
    "refund", "return", "exchange", "late", "exception", "policy",
    "dispute", "chargeback", "damaged", "defective", "complaint",
    "escalate", "legal"
}

def _pick_model(question: str, rag_context: str, tier: str) -> str:
    q = (question or "").lower()
    t = (tier or "").lower()

    complex_q = any(k in q for k in COMPLEX_KEYWORDS)
    long_ctx = len(rag_context or "") > 1800
    high_tier = t in {"gold", "vip"}

    if complex_q or long_ctx or high_tier:
        return "gemini-2.5-flash"
    return "gemini-2.5-flash-lite"

ALLOWED_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
}

def gemini_text(prompt: str, *, question: str = "", rag_context: str = "", tier: str = "", model: str | None = None) -> tuple[str, str]:
    if model in ALLOWED_MODELS:
        model_name = model
    else:
        model_name = _pick_model(question, rag_context, tier)

    resp = client.models.generate_content(model=model_name, contents=prompt)
    return (resp.text or ""), model_name

