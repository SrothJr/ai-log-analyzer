# Local AI Security Log Analyzer

Offline security-log analysis using FastAPI, SQLite, React/Vite, and a local Qwen3.5 0.8B GGUF model served by llama.cpp.

## Resource limits

The application is designed for the assessment limits:

- CPU-only inference
- Two llama.cpp threads
- No GPU offload
- Four GB total RAM
- 2,048-token model context
- One model request at a time

## Prerequisites

On CachyOS:

```bash
sudo pacman -S --needed base-devel cmake git python python-pip python-venv nodejs npm
```

Use Python 3.11+ and Node.js 20+.

## Model and llama.cpp setup

Build llama.cpp for CPU only:

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
git checkout <tested-llama.cpp-commit>
cmake -B build -DGGML_NATIVE=OFF -DGGML_CUDA=OFF -DGGML_OPENCL=OFF -DGGML_VULKAN=OFF
cmake --build build --config Release -j2
```

Place the selected Qwen3.5 0.8B GGUF at:

```text
models/qwen3.5-0.8b-q4.gguf
```

Record the exact download URL, GGUF quantization, file size, SHA-256 checksum, and tested llama.cpp commit here before submission. The model is intentionally not committed to Git.

Start llama.cpp:

```bash
./llama.cpp/build/bin/llama-server \
  -m ./models/qwen3.5-0.8b-q4.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  -c 2048 \
  -t 2 \
  -ngl 0
```

The backend uses `/tokenize` for model-accurate token counting and `/v1/chat/completions` for analysis.

`/v1/models` is not required by this application. A 404 for that optional discovery endpoint is harmless; verify `/tokenize` and `/v1/chat/completions` instead.

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend creates its ignored SQLite database under `backend/data/` and uploaded files under `backend/uploads/`.

## Frontend setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the displayed Vite URL, normally `http://localhost:5173`.

## Analysis design

1. Upload accepts only UTF-8 `.log` and `.txt` files.
2. The file is saved incrementally without loading the entire upload into memory.
3. Lines are rendered with their original line numbers.
4. The matching llama.cpp tokenizer counts each candidate chunk.
5. Complete lines are grouped up to an 1,100-token log-data budget.
6. System prompt, compact prior context, and bounded model output remain inside 2,048 tokens.
7. Chunks are analyzed sequentially; no concurrent model calls are made.
8. Each deterministic observation and analyzed chunk is persisted immediately in SQLite.
9. Backend correlation uses actor, event type, and timestamps to merge duplicates and preserve evidence lines.
10. The local model receives raw chunks plus observations, proposes known or novel findings, and cannot create unvalidated evidence.

## API

```text
GET  /health
POST /api/jobs
POST /api/jobs/{job_id}/start
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/findings
```

## Tests and linting

```bash
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check app tests

cd ../frontend
npm run build
npm run lint
```

The backend tests mock llama.cpp for deterministic testing. A live test still requires the model and llama.cpp server.

## GitHub submission checklist

Commit source and documentation only. Do not commit:

- `backend/.venv/`
- `backend/data/` or `backend/uploads/`
- `frontend/node_modules/` or `frontend/dist/`
- `models/*.gguf`
- `llama.cpp/`
- `.env` files
- SQLite databases and runtime logs

Before committing, inspect:

```bash
git status --short --ignored
git diff --check
```

The ignored paths should appear only in the `!!` section. `.env.example`, `README.md`, `AI_USAGE.md`, `doc.md`, source code, tests, and `test-data/` should remain visible for review.

## Known limits

- The application intentionally runs one analysis job at a time through one llama.cpp process.
- The default background task is process-local and is not a distributed job queue.
- Uploads and SQLite data are local runtime artifacts.
- Exact model quality depends on the selected Qwen GGUF quantization.
- Restart-resume is not implemented; completed chunk records are retained, but automatic continuation is future work.
- The exact model URL, checksum, and llama.cpp commit must be recorded after local setup.
