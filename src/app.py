from fastapi import FastAPI
from fastapi.responses import JSONResponse
from src.schemas import (
    ChatRequest, ChatResponse,
    EmailSuggestionRequest, EmailSuggestionResponse
)
from src.data import load_sales_csv, build_clients_table, get_client_context
from src.llm import gemini_text

from rag.search import search, format_context

app = FastAPI(title="Fashion Policy RAG Demo")


DF = load_sales_csv()
CLIENTS = build_clients_table(DF)


def tier_ack_line(tier: str, mode: str) -> str:
    tier = (tier or "").lower()
    mode = (mode or "").lower()

    if tier == "vip":
        base = "Thanks for being one of our VIP customers."
    elif tier == "gold":
        base = "Thanks for being a Gold customer."
    elif tier == "silver":
        base = "Thanks for being a Silver customer."
    else:
        base = "Thanks for reaching out."

    if mode == "optimistic":
        return base + " I’ll be proactive and share the best options available under our policy."
    return base + " I’ll help, but I may need a couple details to confirm eligibility under policy."


def safe_gemini_call(prompt: str, *, question: str, rag_context: str, tier: str, model: str | None = None):

    try:
        return gemini_text(prompt, question=question, rag_context=rag_context, tier=tier, model=model)
    except TypeError:
        return gemini_text(prompt, question=question, rag_context=rag_context, tier=tier)


def parse_email_sections(text: str) -> tuple[str, str, str]:
    platform_summary = ""
    subject = "Discover new picks for you"
    body = text.strip()

    lower = text.lower()
    if "section a:" in lower and "section b:" in lower:
        parts = text.split("SECTION B:", 1)
        a_part = parts[0]
        b_part = parts[1] if len(parts) > 1 else ""


        if "SECTION A:" in a_part:
            platform_summary = a_part.split("SECTION A:", 1)[1].strip()
        else:
            platform_summary = a_part.strip()


        b_lines = b_part.strip().splitlines()

        for i, line in enumerate(b_lines):
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip() or subject
                rest = "\n".join(b_lines[i+1:]).strip()
                if "Body:" in rest:
                    body = rest.split("Body:", 1)[1].strip()
                else:
                    body = rest
                break

        return platform_summary, subject, body


    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip() or subject
            rest = "\n".join(lines[i+1:]).strip()
            if "Body:" in rest:
                body = rest.split("Body:", 1)[1].strip()
            else:
                body = rest
            break

    return platform_summary, subject, body



@app.get("/health")
def health():
    return {"ok": True}


@app.get("/clients")
def list_clients():
    cols = [
        "customer_id", "tier", "mode", "total_spend",
        "purchase_count", "avg_rating", "rating_coverage",
        "suggestion_limit"
    ]
    out = CLIENTS[cols].copy()
    return out.to_dict(orient="records")


@app.get("/clients/{customer_id}")
def client_detail(customer_id: str):
    ctx = get_client_context(DF, CLIENTS, customer_id)
    history = DF[DF["customer_id"] == str(customer_id)].sort_values("date", ascending=False).head(25)
    return {"profile": ctx, "recent_purchases": history.to_dict(orient="records")}


@app.get("/thresholds")
def thresholds():

    spend = CLIENTS["total_spend"].astype(float)
    cnt = CLIENTS["purchase_count"].astype(int)

    return {
        "spend_quantiles": {
            "p50": float(spend.quantile(0.50)),
            "p80": float(spend.quantile(0.80)),
            "p95": float(spend.quantile(0.95)),
        },
        "count_quantiles": {
            "p50": float(cnt.quantile(0.50)),
            "p80": float(cnt.quantile(0.80)),
            "p95": float(cnt.quantile(0.95)),
        },
        "mode_rule": "optimistic if avg_rating >= 3.8 and rating_coverage >= 0.3 else cautious",
        "suggestion_limits": {"bronze": 3, "silver": 5, "gold": 7, "vip": 9},
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    ctx = get_client_context(DF, CLIENTS, req.customer_id)
    if not ctx:
        return ChatResponse(
            answer="Client not found.",
            used_policy_citations=[],
            used_policy_docs=[],
            client_context={},
        )


    hits = search(req.question, k=6)
    rag_context = format_context(hits)

    used_citations = [h.cite() for h in hits]
    used_docs = sorted({h.doc_id for h in hits})
    ack = tier_ack_line(ctx["tier"], ctx["mode"])


    prompt = f"""
You are a customer support assistant for a fashion retail platform.

HARD RULES:
- Use ONLY the POLICY CONTEXT below to answer policy questions.
- Do NOT invent rules, time windows, exceptions, or benefits.
- If the policy context is missing info, ask for exactly what you need.
- You MUST adapt your response to the customer's tier and mode.

TIER & MODE BEHAVIOR:
- Tier affects what benefits can be offered (shipping coverage, goodwill likelihood, priority).
- Mode affects communication style:
  - optimistic: warm, proactive, suggest best options within policy.
  - cautious: neutral, verification-first, stricter about timelines/evidence.

CUSTOMER CONTEXT:
- customer_id: {ctx["customer_id"]}
- tier: {ctx["tier"]}
- mode: {ctx["mode"]}
- total_spend: {ctx["total_spend"]}
- purchase_count: {ctx["purchase_count"]}
- avg_rating: {ctx["avg_rating"]}
- rating_coverage: {ctx["rating_coverage"]}
- last_purchase: {ctx["last_purchase"]}
- recent_items: {ctx["recent_items"]}

POLICY CONTEXT (authoritative):
{rag_context}

RESPONSE FORMAT:
1) First line MUST be a tier-aware acknowledgment (one sentence).
2) Then provide the answer grounded in policy.
3) Include citations like [1], [2] corresponding to the POLICY CONTEXT numbering.
4) End with "Next steps" bullets.

Customer question: {req.question}
""".strip()

    try:
        model = getattr(req, "model", None)
        answer, model_used = gemini_text(
            prompt,
            question=req.question,
            rag_context=rag_context,
            tier=ctx["tier"],
            model=req.model
        )

    except Exception as e:

        fallback = (
            f"{ack}\n\n"
            "I couldn’t reach the AI model right now, but here is the most relevant policy context I found:\n\n"
            f"{rag_context}\n\n"
            "Next steps:\n"
            "- Share the item name and purchase date\n"
            "- Tell us the reason (changed mind / wrong size / defective)\n"
        )
        return ChatResponse(
            answer=fallback,
            used_policy_citations=used_citations,
            used_policy_docs=used_docs,
            client_context={
                "tier": ctx["tier"],
                "mode": ctx["mode"],
                "suggestion_limit": ctx["suggestion_limit"],
                "model_used": "unavailable",
            },
        )


    if ctx["tier"].lower() not in answer.lower():
        answer = f"{ack}\n\n{answer}"

    return ChatResponse(
        answer=answer,
        used_policy_citations=used_citations,
        used_policy_docs=used_docs,
        client_context={
            "tier": ctx["tier"],
            "mode": ctx["mode"],
            "suggestion_limit": ctx["suggestion_limit"],
            "model_used": model_used,
        },
    )


@app.post("/email_suggestion", response_model=EmailSuggestionResponse)
def email_suggestion(req: EmailSuggestionRequest):
    ctx = get_client_context(DF, CLIENTS, req.customer_id)

    occasion = req.occasion or "general update"
    limit = int(ctx["suggestion_limit"])
    top_items = ctx["top_items"][:5]
    recent = ctx["recent_items"][:5]

    prompt = f"""
You are generating content to display inside a demo platform (do not send emails).

CLIENT CONTEXT:
- Tier: {ctx["tier"]}
- Mode: {ctx["mode"]}
- Top items: {top_items}
- Recent items: {recent}
- Avg purchase amount: {ctx["avg_amount"]}
- Total spend: {ctx["total_spend"]}

TASK:
Return TWO sections.

SECTION A: PLATFORM SUMMARY (2-4 sentences)
- Start with: "Based on this client’s history and status..."
- Explain why these suggestions fit and how tier/mode changes optimism/caution.

SECTION B: SUGGESTED EMAIL DRAFT
- Format exactly:
  Subject: ...
  Body:
  ...
- Suggest exactly {min(limit,5)} item ideas (categories like Jacket, Tunic, Handbag, etc.)
- No promises of discounts/refunds/exceptions.

Occasion/theme: {occasion}
""".strip()

    try:
        model = getattr(req, "model", None)
        text, model_used = gemini_text(
            prompt,
            question="email_suggestion",
            rag_context="",
            tier=ctx["tier"],
            model=req.model
        )

    except Exception:
        subject = "New picks for you"
        body = (
            f"Based on this client’s history and status ({ctx['tier']}/{ctx['mode']}), "
            f"we suggest focusing on items similar to: {', '.join(top_items[:3])}.\n\n"
            "Subject: New picks you may like\n"
            "Body:\n"
            f"Hi {ctx['customer_id']},\n\n"
            "Based on your recent choices, here are a few ideas you might like:\n"
            f"- {top_items[0] if len(top_items) > 0 else 'Jacket'}\n"
            f"- {top_items[1] if len(top_items) > 1 else 'Tunic'}\n"
            f"- {top_items[2] if len(top_items) > 2 else 'Handbag'}\n\n"
            "Reply with your occasion and budget, and we’ll refine the picks.\n"
        )
        return EmailSuggestionResponse(subject=subject, body=body, tier=ctx["tier"], mode=ctx["mode"])

    platform_summary, subject, body = parse_email_sections(text)

    if platform_summary.strip():
        body = platform_summary.strip() + "\n\n---\n\n" + body.strip()

    return EmailSuggestionResponse(subject=subject, body=body, tier=ctx["tier"], mode=ctx["mode"])
