from __future__ import annotations
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List
import faiss
from sentence_transformers import SentenceTransformer


DOC_DIR = Path("docs")


OUT_DIR = Path("dat/out")
INDEX_PATH = OUT_DIR / "rag.faiss"
META_PATH = OUT_DIR / "rag_meta.jsonl"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def clean_text(s: str) -> str:
    s = s.replace("\r", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 180) -> List[str]:
    text = clean_text(text)
    chunks: List[str] = []
    i = 0
    while i < len(text):
        j = min(len(text), i + chunk_size)
        chunk = text[i:j].strip()
        if chunk:
            chunks.append(chunk)
        i = max(j - overlap, i + 1)
    return chunks


def first_markdown_title(raw: str, fallback: str) -> str:
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip() or fallback
    return fallback


@dataclass
class ChunkMeta:
    doc_id: str      
    doc_title: str   
    chunk_id: int
    text: str


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(DOC_DIR.glob("*.md"))

    model = SentenceTransformer(MODEL_NAME)

    all_chunks: List[ChunkMeta] = []
    for f in md_files:
        raw = f.read_text(encoding="utf-8")
        title = first_markdown_title(raw, fallback=f.stem)
        chunks = chunk_text(raw)

        for idx, ch in enumerate(chunks):
            all_chunks.append(
                ChunkMeta(
                    doc_id=f.name,
                    doc_title=title,
                    chunk_id=idx,
                    text=ch,
                )
            )

    texts = [c.text for c in all_chunks]
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    emb = emb.astype("float32")

    dim = emb.shape[1]
    index = faiss.IndexFlatIP(dim)  # cosine similarity via normalized embeddings
    index.add(emb)

    faiss.write_index(index, str(INDEX_PATH))

    with META_PATH.open("w", encoding="utf-8") as w:
        for c in all_chunks:
            w.write(
                json.dumps(
                    {
                        "doc_id": c.doc_id,
                        "doc_title": c.doc_title,
                        "chunk_id": c.chunk_id,
                        "text": c.text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(f"Built index: {INDEX_PATH} (vectors={index.ntotal}, dim={dim})")
    print(f"Wrote metadata: {META_PATH} (chunks={len(all_chunks)})")
    print("Done. You can now run: python -m rag.search_demo")


if __name__ == "__main__":
    main()
