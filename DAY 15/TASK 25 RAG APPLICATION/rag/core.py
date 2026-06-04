import os
import json
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from PyPDF2 import PdfReader
import pandas as pd


def load_pdf_text(path: str) -> str:
    reader = PdfReader(path)
    texts = []
    for p in reader.pages:
        try:
            texts.append(p.extract_text() or "")
        except Exception:
            continue
    return "\n".join(texts)


def load_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_csv_as_text(path: str) -> str:
    df = pd.read_csv(path)
    rows = []
    for idx, row in df.iterrows():
        rows.append(" | ".join([f"{k}: {v}" for k, v in row.items()]))
    return "\n".join(rows)


try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENC = None


def chunk_text(text: str, min_tokens: int = 300, max_tokens: int = 500, overlap: int = 50) -> List[str]:
    """Chunk text into token-aware pieces. Falls back to word-based approx if tiktoken unavailable.

    Chunks of size up to `max_tokens` with `overlap` tokens of overlap.
    """
    if not text:
        return []
    if _ENC is not None:
        tokens = _ENC.encode(text)
        chunks = []
        i = 0
        while i < len(tokens):
            end = i + max_tokens
            chunk_tokens = tokens[i:end]
            try:
                chunk_text = _ENC.decode(chunk_tokens)
            except Exception:
                # fallback to joining white-space split if decode fails
                chunk_text = " ".join(text.split()[i:end])
            chunks.append(chunk_text)
            i += max_tokens - overlap
        return chunks

    # Fallback: approximate tokens by words
    words = text.split()
    chunks = []
    i = 0
    size = max_tokens
    while i < len(words):
        chunk = words[i:i+size]
        chunks.append(" ".join(chunk))
        i += size - overlap
    return chunks


class EmbeddingModel:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> np.ndarray:
        emb = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return emb.astype('float32')


class FaissStore:
    def __init__(self, store_dir: str = "./faiss_store"):
        os.makedirs(store_dir, exist_ok=True)
        self.store_dir = store_dir
        self.index_path = os.path.join(store_dir, "index.faiss")
        self.meta_path = os.path.join(store_dir, "metadata.json")
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        self.dim = None
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                self.dim = self.index.d
            except Exception:
                self.index = None

    def _save_meta(self):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def add_documents(self, embeddings: np.ndarray, metadatas: List[Dict[str, Any]]):
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        n, d = embeddings.shape
        if self.index is None:
            self.dim = d
            self.index = faiss.IndexFlatL2(d)
        if d != self.dim:
            raise ValueError("Embedding dimension mismatch")
        self.index.add(embeddings)
        self.metadata.extend(metadatas)
        faiss.write_index(self.index, self.index_path)
        self._save_meta()

    def search(self, query_emb: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        if query_emb.ndim == 1:
            query_emb = query_emb.reshape(1, -1)
        D, I = self.index.search(query_emb.astype('float32'), top_k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx].copy()
            meta.update({"score": float(dist)})
            results.append(meta)
        return results


def ingest_files(paths: List[str], store: FaissStore, embedder: EmbeddingModel, doc_type: str = None, crop: str = None):
    metadatas = []
    texts = []
    for p in paths:
        if p.lower().endswith('.pdf'):
            text = load_pdf_text(p)
        elif p.lower().endswith('.txt'):
            text = load_txt(p)
        elif p.lower().endswith('.csv'):
            text = load_csv_as_text(p)
        else:
            # try to read as text
            text = load_txt(p)
        chunks = chunk_text(text)
        for i, c in enumerate(chunks):
            texts.append(c)
            metadatas.append({
                "source": os.path.abspath(p),
                "chunk_id": i,
                "doc_type": doc_type,
                "crop": crop,
                "text": c[:2000]
            })
    if texts:
        embs = embedder.embed(texts)
        store.add_documents(embs, metadatas)
