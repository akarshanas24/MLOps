# 🚀 RAG Application - Full Connectivity Setup

## Architecture Overview
- **Ollama**: Local LLM service (port 11434)
- **FastAPI**: RAG backend with vector search (port 8000)
- **Node.js**: Frontend server & API gateway (port 3010)
- **Browser**: Access at `http://localhost:3010`

## Startup Instructions (In Order)

### 1️⃣ Start Ollama Service (Windows)
```powershell
# If Ollama is installed, run in a separate terminal:
ollama serve
# This will start on http://localhost:11434

# Then in another terminal, ensure model is pulled:
ollama pull llama3
```

**What to look for:**
- Terminal shows: `Listening on 127.0.0.1:11434`
- No error messages about port conflicts

---

### 2️⃣ Start FastAPI Backend
```powershell
# In your activated Python environment:
cd d:\MLOps\DAY 15\TASK 25 RAG APPLICATION

# Start the FastAPI server (runs on port 8000)
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

**What to look for:**
- Terminal shows: `Uvicorn running on http://127.0.0.1:8000`
- No connection errors to Ollama
- You should see: `Application startup complete`

---

### 3️⃣ Start Node.js Frontend Server
```powershell
# In a DIFFERENT terminal (keep FastAPI running):
cd d:\MLOps\DAY 15\TASK 25 RAG APPLICATION

# Start Node server (runs on port 3010)
node server.js
```

**What to look for:**
- Terminal shows: `AgriIntel backend running at http://localhost:3010`
- No "port already in use" errors

---

## ✅ Verify Full Connectivity

### Check 1: Ollama Service
```powershell
curl http://127.0.0.1:11434/api/tags
# Should return list of available models
```

### Check 2: FastAPI Backend
```powershell
curl -X POST http://127.0.0.1:8000/query `
  -H "Content-Type: application/json" `
  -d '{\"query\":\"test\",\"model\":\"llama3\"}'
# Should return an answer (or "don't have enough information" if no docs ingested)
```

### Check 3: Frontend Server
```powershell
curl http://127.0.0.1:3010
# Should return HTML page
```

### Check 4: Full Stack Chat
Open browser to: **http://localhost:3010**
- Top stats should load from backend
- Chat should work and forward to FastAPI
- Schemes section should display

---

## 🔧 Environment Variables (Optional)

Create a `.env` file or set these before running:

```powershell
# Windows PowerShell
$env:PORT = 3010              # Frontend server port
$env:FASTAPI_URL = "http://127.0.0.1:8000"  # FastAPI backend URL
```

---

## 📝 First Time Usage

### Ingest Sample Documents (Optional)
```powershell
# Via Python:
python query_example.py

# Or via curl:
curl -X POST http://127.0.0.1:8000/ingest `
  -H "Content-Type: application/json" `
  -d '{\"paths\":[\"path/to/document.pdf\"],\"doc_type\":\"scheme\",\"crop\":\"rice\"}'
```

### Query the RAG Backend
```powershell
curl -X POST http://127.0.0.1:8000/query `
  -H "Content-Type: application/json" `
  -d '{\"query\":\"What are soil health grants?\",\"model\":\"llama3\",\"top_k\":5}'
```

---

## 🚨 Troubleshooting

### "ollama CLI not found"
- Install Ollama from https://ollama.ai
- Add to PATH: `C:\Users\<Your-User>\AppData\Local\Ollama`
- Restart terminal

### "Model llama3 not found"
```powershell
ollama pull llama3
```

### FastAPI can't connect to Ollama
- Verify Ollama is running: `ollama serve` in separate terminal
- Check port 11434 is not blocked

### Frontend won't load
- Ensure Node.js server is running
- Check no other process is using port 3010
- Verify FastAPI is running on 8000

### CORS errors in browser console
- This means FastAPI isn't running or unreachable
- Node.js server should proxy all `/api/*` requests to FastAPI
- Check both services are running

---

## 🎯 Full Data Flow

```
User Input (Browser)
    ↓
Node.js Frontend (port 3010)
    ↓
Proxy to FastAPI (port 8000)
    ↓
Vector Search (FAISS)
    ↓
Ollama LLM (port 11434)
    ↓
Response back through stack
    ↓
User sees AI-generated answer
```

---

## 📊 Expected Performance
- First query: 3-8 seconds (model loading)
- Subsequent queries: 2-5 seconds (depends on model size and query complexity)
- Chat interface should be responsive

---

## 🔗 Quick Links
- Frontend: http://localhost:3010
- FastAPI Docs: http://127.0.0.1:8000/docs
- FastAPI ReDoc: http://127.0.0.1:8000/redoc
- Ollama Status: http://127.0.0.1:11434/api/tags
