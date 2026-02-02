import streamlit as st
import requests
import json

API_BASE = "http://127.0.0.1:8000"

TIER_COLORS = {
    "bronze": "#CD7F32",
    "silver": "#C0C0C0",
    "gold":   "#FFD700",
    "vip":    "#A855F7",
}

MODE_COLORS = {
    "optimistic": "#22C55E",
    "cautious":   "#EF4444",
}

TIER_ICON = {
    "bronze": "🟤",
    "silver": "⚪",
    "gold":   "🟡",
    "vip":    "🟣",
}

def badge(label: str, color: str) -> str:
    return f"""
    <span style="
        display:inline-block;
        padding: 0.20rem 0.55rem;
        border-radius: 999px;
        background: {color};
        color: #111;
        font-weight: 700;
        font-size: 0.85rem;
        margin-left: 0.25rem;
    ">{label}</span>
    """

st.set_page_config(page_title="Fashion RAG Demo", layout="wide")

def api_get(path):
    r = requests.get(f"{API_BASE}{path}")
    return r.json()

def api_post(path, payload):
    r = requests.post(f"{API_BASE}{path}", json=payload)
    return r.json()

with st.sidebar:
    model_choice = st.selectbox(
        "Model",
        ["gemini-2.5-flash-lite", "gemini-2.5-flash"],
        index=0,
        key="model_choice"
    )

st.title("🛍️ Fashion RAG Demo Platform")
st.markdown(
    """
This demo shows:
- **Client loyalty tiers & mode (optimistic vs cautious)**
- **Policy-grounded AI support**
- **Suggested email drafts (display-only, not sent)**
"""
)

with st.expander("🔎 How tiers & modes work (click to expand)", expanded=False):
    st.markdown("**Tier = loyalty level (spend + purchase frequency, percentile-based)**")
    tier_data = [
        ("BRONZE", TIER_COLORS['bronze'], "below **P50** on spend **and** purchases"),
        ("SILVER", TIER_COLORS['silver'], "**≥ P50** on spend **or** purchases"),
        ("GOLD",   TIER_COLORS['gold'],   "**≥ P80** on spend **or** purchases"),
        ("VIP",    TIER_COLORS['vip'],    "**≥ P95** on spend **or** purchases")
    ]

    for label, color, desc in tier_data:
        col_badge, col_text = st.columns([1, 5])
        with col_badge:
            st.markdown(badge(label, color), unsafe_allow_html=True)
        with col_text:
            st.markdown(f"**{label.capitalize()}:** {desc}")

    st.markdown("---")
    st.markdown("**Mode = interaction style (ratings + rating coverage)**")
    
    m_col1, m_col2 = st.columns([1, 5])
    with m_col1:
        st.markdown(badge('optimistic', MODE_COLORS['optimistic']), unsafe_allow_html=True)
    with m_col2:
        st.markdown("avg_rating ≥ **3.8** and rating_coverage ≥ **0.30**")

    m_col1_b, m_col2_b = st.columns([1, 5])
    with m_col1_b:
        st.markdown(badge('cautious', MODE_COLORS['cautious']), unsafe_allow_html=True)
    with m_col2_b:
        st.markdown("otherwise")

    st.markdown("---")
    st.markdown("**What it changes**")
    st.markdown(
        """
- **Chat:** Tier affects benefits *within policy*; Mode affects tone
- **Email suggestions:** Tier sets **Suggestion Limit** (3/5/7/9); Mode changes suggestion style  
"""
    )

st.sidebar.header("Clients")

with st.sidebar:
    clients = api_get("/clients")
    client_map = {c["customer_id"]: c for c in clients}
    client_ids = list(client_map.keys())

    def format_client(cid: str) -> str:
        t = (client_map[cid].get("tier") or "bronze").lower()
        icon = TIER_ICON.get(t, "⬜")
        return f"{icon} {cid} ({t.upper()})"

    selected_id = st.selectbox("Select Client", client_ids, format_func=format_client)
    selected_client = client_map[selected_id]

    st.markdown("### Client Summary")
    tier = (selected_client["tier"] or "bronze").lower()
    mode = (selected_client["mode"] or "cautious").lower()

    st.markdown(f"**Tier:** {badge(tier.upper(), TIER_COLORS.get(tier, '#999'))}", unsafe_allow_html=True)
    st.markdown(f"**Mode:** {badge(mode, MODE_COLORS.get(mode, '#999'))}", unsafe_allow_html=True)

    coverage = selected_client.get("rating_coverage", None)
    if coverage is not None:
        st.markdown(f"**Rating coverage:** {coverage:.2f}")

    st.markdown(f"**Total Spend:** ${selected_client['total_spend']:.2f}")
    st.markdown(f"**Purchases:** {selected_client['purchase_count']}")
    st.markdown(f"**Avg Rating:** {selected_client['avg_rating']}")
    st.markdown(f"**Suggestion Limit:** {selected_client['suggestion_limit']}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("💬 Policy-Aware Support Chat")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        role = "**You:**" if msg["role"] == "user" else "**Assistant:**"
        st.markdown(f"{role} {msg['content']}")

    user_input = st.text_input("Ask (e.g., 'Can I return a handbag after 16 days?')", key="chat_input", autocomplete="off")

    if st.button("Send", key="send_btn") and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        resp = api_post("/chat", {"customer_id": selected_id, "question": user_input, "model": model_choice})

        answer = resp.get("answer", "")
        used_docs = resp.get("used_policy_docs", [])
        ctx = resp.get("client_context", {})

        if used_docs:
            answer += "\n\n---\n**Policy sources:** " + ", ".join(used_docs)
        answer += f"\n\n**Context:** Tier={ctx.get('tier')} | Mode={ctx.get('mode')}"

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

with col2:
    st.subheader("✉️ Suggested Email (Display Only)")
    occasion = st.text_input("Optional theme/occasion", key="email_occasion", autocomplete="off")

    if st.button("Generate Email Draft", key="generate_email_btn"):
        resp = api_post("/email_suggestion", {"customer_id": selected_id, "occasion": occasion, "model": model_choice})
        st.markdown(f"### Subject\n{resp.get('subject', '')}")
        st.text_area("", value=resp.get("body", ""), height=300)
        st.caption(f"Tier: {resp.get('tier')} | Mode: {resp.get('mode')}")

st.markdown("---")
st.caption("Demo platform: FastAPI + FAISS RAG + Gemini + Streamlit")
