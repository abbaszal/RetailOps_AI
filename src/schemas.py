from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    customer_id: str
    question: str
    model: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    used_policy_citations: List[str]
    used_policy_docs: List[str]
    client_context: Dict[str, Any]


class EmailSuggestionRequest(BaseModel):
    customer_id: str
    occasion: Optional[str] = None
    model: Optional[str] = None



class EmailSuggestionResponse(BaseModel):
    subject: str
    body: str
    tier: str
    mode: str



