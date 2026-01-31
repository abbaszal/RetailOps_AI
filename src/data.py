import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any

CSV_PATH = Path("fashion_data/Fashion_Retail_Sales.csv")


def load_sales_csv() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df.columns = [c.strip().lower() for c in df.columns]

    rename = {
        "customer reference id": "customer_id",
        "item purchased": "item",
        "purchase amount (usd)": "amount",
        "date purchase": "date",
        "review rating": "rating",
        "payment method": "payment_method",
    }
    df = df.rename(columns=rename)

    df["customer_id"] = df["customer_id"].astype(str)
    df["item"] = df["item"].astype(str)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    return df


def compute_tier(total_spend: float, purchase_count: int, avg_rating: float | None) -> str:
    if total_spend >= 20000 and (avg_rating is not None and avg_rating >= 4.2):
        return "vip"
    if total_spend >= 10000 or purchase_count >= 8:
        return "gold"
    if total_spend >= 5000 or purchase_count >= 3:
        return "silver"
    return "bronze"


def compute_mode(avg_rating: float | None, rating_coverage: float) -> str:
    if avg_rating is None:
        return "cautious"
    if avg_rating < 4.0:
        return "cautious"
    if rating_coverage < 0.4:
        return "cautious"
    return "optimistic"


def build_clients_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("customer_id", as_index=False)

    out = g.agg(
        total_spend=("amount", "sum"),
        purchase_count=("amount", "size"),
        last_purchase=("date", "max"),
        avg_rating=("rating", "mean"),
        rated_count=("rating", lambda s: s.notna().sum()),
        avg_amount=("amount", "mean"),
    )

    out["rating_coverage"] = out["rated_count"] / out["purchase_count"]
    out["avg_rating"] = out["avg_rating"].where(out["avg_rating"].notna(), None)


    spend = out["total_spend"].astype(float)
    cnt = out["purchase_count"].astype(int)

    spend_p50, spend_p80, spend_p95 = spend.quantile([0.50, 0.80, 0.95]).tolist()
    cnt_p50, cnt_p80, cnt_p95 = cnt.quantile([0.50, 0.80, 0.95]).tolist()

    def tier_row(r):
        s = float(r["total_spend"])
        c = int(r["purchase_count"])
        ar = r["avg_rating"]

        # VIP = top 5% spend or purchases + good satisfaction
        if ((s >= spend_p95) or (c >= cnt_p95)) and (ar is not None and ar >= 4.0):
            return "vip"
        # Gold = top 20%
        if (s >= spend_p80) or (c >= cnt_p80):
            return "gold"
        # Silver = middle
        if (s >= spend_p50) or (c >= cnt_p50):
            return "silver"
        return "bronze"

    out["tier"] = out.apply(tier_row, axis=1)


    def mode_row(r):
        ar = r["avg_rating"]
        cov = float(r["rating_coverage"])
        if ar is None:
            return "cautious"
        # optimistic if ratings are decent and we have enough ratings
        if ar >= 3.0 and cov >= 0.3:
            return "optimistic"
        return "cautious"

    out["mode"] = out.apply(mode_row, axis=1)
    out["suggestion_limit"] = out["tier"].map({"bronze": 3, "silver": 5, "gold": 7, "vip": 9})

    return out



def get_client_context(df: pd.DataFrame, clients: pd.DataFrame, customer_id: str) -> Dict[str, Any] | None:
    row = clients[clients["customer_id"] == str(customer_id)]
    if row.empty:
        return None

    r = row.iloc[0]
    history = df[df["customer_id"] == str(customer_id)].sort_values("date", ascending=False)

    # Top items and recency summary
    top_items = history["item"].value_counts().head(5).index.tolist()
    recent_items = history.head(8)["item"].tolist()

    avg_rating = r["avg_rating"] if r["avg_rating"] is not None else None

    return {
        "customer_id": str(customer_id),
        "tier": r["tier"],
        "mode": r["mode"],
        "total_spend": float(r["total_spend"]),
        "purchase_count": int(r["purchase_count"]),
        "avg_amount": float(r["avg_amount"]),
        "avg_rating": avg_rating,
        "rating_coverage": float(r["rating_coverage"]),
        "last_purchase": None if pd.isna(r["last_purchase"]) else str(pd.to_datetime(r["last_purchase"]).date()),
        "top_items": top_items,
        "recent_items": recent_items,
        "suggestion_limit": int(r["suggestion_limit"]),
    }
