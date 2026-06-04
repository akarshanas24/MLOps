from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from rag.core import FaissStore, EmbeddingModel, ingest_files
from rag.ollama_client import call_ollama


app = FastAPI(title="AgroMind AI - RAG Backend")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = FaissStore(store_dir="./faiss_store")
embedder = EmbeddingModel()


class IngestRequest(BaseModel):
    paths: List[str]
    doc_type: Optional[str] = None
    crop: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    model: Optional[str] = "llama3"
    top_k: Optional[int] = 5


@app.post("/ingest")
def ingest(req: IngestRequest):
    try:
        ingest_files(req.paths, store, embedder, doc_type=req.doc_type, crop=req.crop)
        return {"status": "ok", "ingested_files": len(req.paths)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
def query(req: QueryRequest):
    # 1. embed query
    q_emb = embedder.embed([req.query])[0]
    # 2. search
    hits = store.search(q_emb, top_k=req.top_k)
    if not hits:
        return {"answer": "I don't have enough information.", "sources": []}
    # build context
    context_parts = []
    for h in hits:
        context_parts.append(f"Source: {h.get('source')}\nDocType: {h.get('doc_type')}\nCrop: {h.get('crop')}\nText: {h.get('text')}")
    context = "\n\n".join(context_parts)
    # 3. build prompt
    prompt = f"You are AgroMind AI, an agricultural expert assistant.\nYou must answer ONLY using the provided context. If the answer is not in the context, say \"I don't have enough information.\"\n\nContext:\n{context}\n\nQuestion:\n{req.query}\n\nRules:\n- Be simple and clear\n- Focus on Indian agriculture context\n- Provide practical suggestions if possible\n- Do not hallucinate\n- Keep answer short and useful\n\nAnswer:"
    # 4. call ollama
    resp = call_ollama(prompt, model=req.model)
    return {"answer": resp, "sources": hits}
