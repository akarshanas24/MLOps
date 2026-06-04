# AgroMind AI — Complete RAG Application with Full Backend Connectivity

A production-ready Retrieval-Augmented Generation (RAG) application for agricultural intelligence. Combines local LLM inference (Ollama), vector search (FAISS), and a responsive web interface.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│  Browser (http://localhost:3010)                     │
│  - Interactive Chat                                  │
│  - Scheme Finder                                     │
│  - Real-time Metrics                                │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│  Node.js Frontend Server (port 3010)                 │
│  - Static file serving                               │
│  - API Gateway & Proxy                               │
│  - CORS handling                                     │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│  FastAPI Backend (port 8000)                         │
│  - RAG Pipeline                                      │
│  - Vector Search (FAISS)                             │
│  - Ollama Integration                                │
│  - Document Ingestion                                │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│  Ollama LLM Service (port 11434)                     │
│  - Local model execution (llama3)                    │
│  - No internet required                              │
│  - Full privacy                                      │
└─────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** with pip
- **Node.js 14+** with npm
- **Ollama** (https://ollama.ai) installed and running
- **Windows/macOS/Linux**

### 1️⃣ Automatic Startup (Recommended)
```powershell
# Windows PowerShell
.\startup.ps1

# This will:
# ✓ Start Ollama service (port 11434)
# ✓ Start FastAPI backend (port 8000)  
# ✓ Start Node.js frontend (port 3010)
# ✓ Open browser to http://localhost:3010
```

### 2️⃣ Manual Startup (See Service Order Below)

## 📋 Detailed Setup Instructions

### Step 1: Install Dependencies

```bash
# Create Python virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Prepare Ollama

```bash
# Start Ollama service (in a separate terminal)
ollama serve

# In another terminal, ensure model is available
ollama pull llama3
```

**Verify Ollama is running:**
```bash
curl http://127.0.0.1:11434/api/tags
```

### Step 3: Start Backend Services

#### Terminal 1: FastAPI Backend
```bash
# Activate venv (if not already)
.venv\Scripts\activate

# Start FastAPI
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

#### Terminal 2: Node.js Frontend Server
```bash
# Start Node server
node server.js

# Output should show: AgriIntel backend running at http://localhost:3010
```

### Step 4: Access the Application

Open your browser to: **http://localhost:3010**

## 🔗 Full Connectivity Verification

### Check Ollama
```bash
curl http://127.0.0.1:11434/api/tags
# Returns: list of available models
```

### Check FastAPI
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What are government schemes?","model":"llama3"}'
# Returns: RAG-generated response
```

### Check Node.js Frontend
```bash
curl http://127.0.0.1:3010
# Returns: HTML page content
```

### Test Full Chat Flow
1. Go to http://localhost:3010
2. Click on the chat section
3. Ask a question about agriculture
4. Response should come from the RAG pipeline through Ollama

## 📚 API Endpoints

### FastAPI Backend (Direct Calls)

#### Ingest Documents
```http
POST /ingest
Content-Type: application/json

{
  "paths": ["/absolute/path/to/document.pdf"],
  "doc_type": "scheme",      # optional
  "crop": "rice"             # optional
}

Response:
{
  "status": "ok",
  "ingested_files": 1
}
```

#### Query RAG
```http
POST /query
Content-Type: application/json

{
  "query": "What are soil health grants?",
  "model": "llama3",         # optional, default: llama3
  "top_k": 5                 # optional, default: 5
}

Response:
{
  "answer": "Based on available information...",
  "sources": [
    {
      "source": "/path/to/document.pdf",
      "chunk_id": 0,
      "doc_type": "scheme",
      "crop": "rice",
      "text": "Relevant excerpt...",
      "score": 0.123
    }
  ]
}
```

### Frontend Server Proxy Endpoints (Via Node.js)

The Node.js server proxies all `/api/*` requests to FastAPI, so you can call them through the frontend server:

```http
# These work from browser/frontend code:
POST http://localhost:3010/api/query
POST http://localhost:3010/api/ingest
POST http://localhost:3010/api/chat
GET http://localhost:3010/api/insights
GET http://localhost:3010/api/schemes
```

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t agromind-rag .
```

### Run Container
```bash
# Make sure Ollama is running on host
docker run -p 8000:8000 \
  -e OLLAMA_HOST=host.docker.internal:11434 \
  agromind-rag
```

## 📝 Document Ingestion

### Supported Formats
- PDF (.pdf)
- Text (.txt)
- CSV (.csv)

### Example: Ingest PDFs
```bash
# Via Python script
python query_example.py

# Via cURL
curl -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"paths":["/path/to/scheme.pdf"],"doc_type":"government_scheme","crop":"rice"}'
```

## 🔧 Configuration

### Environment Variables
```bash
# Frontend port (default: 3010)
export PORT=3010

# FastAPI URL (default: http://127.0.0.1:8000)
export FASTAPI_URL=http://127.0.0.1:8000

# Ollama host (default: 127.0.0.1:11434)
export OLLAMA_HOST=127.0.0.1:11434
```

### Vector Store Location
Documents are stored in `./faiss_store/`:
- `index.faiss` — Vector index
- `metadata.json` — Document metadata

### Chunk Configuration
Edit `rag/core.py` to adjust chunking:
- `min_tokens` — Minimum chunk size (default: 300)
- `max_tokens` — Maximum chunk size (default: 500)
- `overlap` — Token overlap between chunks (default: 50)

## 🐛 Troubleshooting

### "Ollama CLI not found"
```bash
# Install Ollama: https://ollama.ai
# Add to PATH or use full path in ollama_client.py
```

### "Model llama3 not found"
```bash
ollama pull llama3
```

### "FastAPI won't start"
```bash
# Check port 8000 is free
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # macOS/Linux

# Kill process using port 8000
taskkill /PID <PID> /F         # Windows
kill -9 <PID>                  # macOS/Linux
```

### "Frontend won't connect to backend"
1. Ensure FastAPI is running: Check `http://127.0.0.1:8000/docs`
2. Ensure Node.js is running: Check terminal output
3. Check browser console for errors (F12)
4. Verify no firewall blocking localhost connections

### "Responses are slow"
- First query on a model is slow (model loading): normal
- Reduce `top_k` parameter (fewer documents to process)
- Use a smaller model: `ollama pull mistral` or `ollama pull neural-chat`
- Increase Ollama timeout in `rag/ollama_client.py`

### "Chat returns 'backend unavailable'"
- Check Ollama is running: `ollama serve` in terminal
- Check FastAPI is running: Terminal should show `Uvicorn running`
- Wait a moment (services may be starting)
- Check no errors in FastAPI terminal

## 📊 Performance Tips

1. **Embedding Model**: Uses `sentence-transformers/all-MiniLM-L6-v2`
   - Fast, lightweight, good quality
   - Can change in `rag/core.py`: `EmbeddingModel(model_name="...")`

2. **Chunking**: Token-aware with overlap
   - Maintains context across chunks
   - Adjust in `rag/core.py` for longer/shorter responses

3. **Vector Search**: FAISS with L2 distance
   - `top_k=5` balances speed and relevance
   - Adjust in API calls for more/fewer results

4. **LLM Model**: Ollama with llama3
   - Replace with `ollama pull mistral` for faster inference
   - Adjust via `model` parameter in API calls

## 🔐 Security Notes

- **Local Execution**: All processing stays on your machine
- **No API Keys**: No external service dependencies
- **Privacy**: Documents never leave your system
- **CORS**: Enabled for development (restrict in production)

## 📦 Project Structure

```
.
├── app.py                    # FastAPI application
├── server.js                 # Node.js frontend server
├── index.html                # Web interface
├── script.js                 # Frontend logic
├── styles.css                # Frontend styles
├── package.json              # Node.js dependencies
├── requirements.txt          # Python dependencies
├── query_example.py          # Example query script
├── rag/
│   ├── core.py              # Vector store & ingestion
│   └── ollama_client.py      # Ollama integration
├── samples/                  # Sample documents (ingested here)
├── faiss_store/             # Vector index storage
├── startup.ps1              # Automated startup script
├── STARTUP_GUIDE.md         # Detailed setup guide
└── Dockerfile               # Docker configuration
```

## 🚀 Next Steps

1. **Ingest documents**: Add PDFs to start RAG
2. **Fine-tune responses**: Adjust prompts in `app.py`
3. **Deploy**: Use Docker for production
4. **Extend**: Add more models, enhance UI, integrate external APIs

## 📖 Additional Resources

- **FastAPI Docs**: http://127.0.0.1:8000/docs (when running)
- **Ollama Models**: https://ollama.ai/library
- **FAISS Guide**: https://github.com/facebookresearch/faiss
- **Sentence Transformers**: https://www.sbert.net/

## 📄 License

Open source educational project.

---

**Version**: 1.1 (Full Backend Connectivity)  
**Last Updated**: 2026-06-04

