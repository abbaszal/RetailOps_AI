from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
import faiss
from sentence_transformers import SentenceTransformer

OUT_DIR = Path("dat/out")
INDEX_PATH = OUT_DIR / "rag.faiss"
META_PATH = OUT_DIR / "rag_meta.jsonl"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class RAGHit:
    score: float
    doc_id: str
    doc_title: str
    chunk_id: int
    text: str

    def cite(self) -> str:
        return f"{self.doc_id}#chunk{self.chunk_id} ({self.doc_title})"


def _load_meta() -> List[Dict[str, Any]]:
    meta: List[Dict[str, Any]] = []
    with META_PATH.open("r", encoding="utf-8") as r:
        for line in r:
            meta.append(json.loads(line))
    return meta


def search(query: str, k: int = 5) -> List[RAGHit]:

    index = faiss.read_index(str(INDEX_PATH))
    meta = _load_meta()

    model = SentenceTransformer(MODEL_NAME)
    q = model.encode([query], normalize_embeddings=True).astype("float32")

    scores, ids = index.search(q, k)
    hits: List[RAGHit] = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        m = meta[int(idx)]
        hits.append(
            RAGHit(
                score=float(score),
                doc_id=m["doc_id"],
                doc_title=m["doc_title"],
                chunk_id=int(m["chunk_id"]),
                text=m["text"],
            )
        )
    return hits


def format_context(hits: List[RAGHit]) -> str:
    lines = []
    for i, h in enumerate(hits, start=1):
        lines.append(f"[{i}] {h.cite()}\n{h.text}\n")
    return "\n".join(lines).strip()
