# Local AI Security Log Analyzer

An offline web application that analyzes large server logs with a local language model, preserves line-level evidence, correlates activity across chunks, and produces a concise security report.

## Technology

- **FastAPI** — backend API and analysis orchestration
- **SQLite** — local jobs, chunks, observations, and findings
- **React + Vite** — upload, progress, and report dashboard
- **llama.cpp** — local model server
- **Qwen3.5 0.8B GGUF** — local log interpretation

The project follows the assessment limits: CPU-only inference, two vCPUs, four GB total RAM, and a maximum 2,048-token model context.

## Features

- UTF-8 `.log` and `.txt` upload validation
- Complete-line, original-line-number-preserving chunking
- Token counting with the matching GGUF tokenizer
- One inference request at a time
- SQLite persistence after processing
- Deterministic security observations as LLM hints and safety guards
- LLM interpretation of known and novel behavior
- Source-file evidence and actor/IP validation
- Cross-chunk actor, event-type, and timestamp correlation
- Canonical attack-family normalization and deduplication
- Prompt-injection-safe log handling
- Browser progress and final-report display

Supported report families include brute force, possible account compromise, SQL injection, endpoint scanning, path traversal, and unusual request rate.

## Assessment compliance

| Requirement | Implementation |
|---|---|
| Local AI only | llama.cpp on `127.0.0.1` |
| CPU-only, no GPU | `-ngl 0`, two inference threads |
| Four GB RAM | One small GGUF model, one request at a time |
| 2,048-token context | llama.cpp context `2048` |
| Accurate token count | llama.cpp `/tokenize` |
| Large-log processing | Complete-line asynchronous chunks |
| Cross-chunk links | Persisted observations and timestamp correlation |
| Structured AI output | Pydantic JSON validation |
| Failed calls | Timeout, retry, malformed-JSON handling, fallback |
| Untrusted logs | Explicit system prompt and source validation |
| Dashboard | React/Vite frontend |

## Architecture

```text
React/Vite browser ──► FastAPI ──► SQLite
                         │
                         ├── tokenizer client ──► llama.cpp /tokenize
                         ├── chunk analyzer   ──► llama.cpp /v1/chat/completions
                         ├── observation detector
                         ├── evidence validator
                         └── correlation and report aggregation
```

### Hybrid analysis

Deterministic parsing extracts useful observations such as authentication events, suspicious query syntax, sensitive endpoint probes, traversal sequences, and request-rate signals. These are hints and safety guards, not the entire detector.

The LLM receives raw numbered log lines plus observations and can propose known or novel behavior. Before a finding reaches the report, the backend verifies that:

- Evidence exists in the original file.
- Evidence belongs to the cited actor/IP.
- Evidence is inside the current chunk.
- Known attack families have supporting observations.
- Placeholder labels and ordinary-traffic claims are rejected.

Known families are aggregated deterministically by validated actor and canonical attack family. Novel LLM findings are retained only when they have a source-level security signal.

## Resource and token budget

```text
CPU:              two llama.cpp threads
GPU:              disabled
Model context:    2,048 tokens
Log data budget:  1,100 tokens per chunk
Model output:     398 tokens maximum
Concurrency:      one inference request
```

The request budget includes instructions, observations, log text, and model output. The backend uses the model tokenizer through llama.cpp rather than character estimates.

## CachyOS and Hyprland setup

This project was developed on **CachyOS**, an Arch-based distribution, with a **Hyprland** desktop environment. It is terminal-first and does not depend on Hyprland-specific components.

Install prerequisites:

```fish
sudo pacman -S --needed base-devel cmake git python python-pip python-venv nodejs npm
```

Fish shell virtual-environment activation:

```fish
source backend/.venv/bin/activate.fish
```

## Model setup

Use the approved Qwen3.5 0.8B GGUF artifact and place it at:

```text
models/qwen3.5-0.8b-q4.gguf
```

Record the exact artifact details before submission:

```text
Model:        Qwen3.5 0.8B
Quantization: <exact GGUF quantization>
Source URL:   <approved download URL>
File size:    <size>
SHA-256:      <checksum>
llama.cpp:    <tested commit>
```

```fish
sha256sum models/qwen3.5-0.8b-q4.gguf
```

Do not commit the model file.

## Build and run llama.cpp

```fish
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
git checkout <tested-llama.cpp-commit>
cmake -B build \
  -DGGML_NATIVE=OFF \
  -DGGML_CUDA=OFF \
  -DGGML_OPENCL=OFF \
  -DGGML_VULKAN=OFF
cmake --build build --config Release -j2
cd ..
```

Start the model server:

```fish
./llama.cpp/build/bin/llama-server \
  -m ./models/qwen3.5-0.8b-q4.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  -c 2048 \
  -t 2 \
  -ngl 0
```

Verify the endpoints used by this project:

```fish
curl http://127.0.0.1:8080/health
curl -X POST http://127.0.0.1:8080/tokenize \
  -H 'Content-Type: application/json' \
  -d '{"content":"1: test log line","add_special":false}'
```

The application uses `/tokenize` and `/v1/chat/completions`. `/v1/models` is optional and a 404 there is harmless.

## Backend setup

```fish
cd backend
python -m venv .venv
source .venv/bin/activate.fish
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cp ../.env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check the backend:

```fish
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Runtime data is created in ignored locations:

```text
backend/data/       SQLite database
backend/uploads/    uploaded files
```

## Frontend setup

Open another terminal:

```fish
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`.

The frontend uses the existing API routes and does not connect to llama.cpp directly:

```text
Browser → FastAPI → llama.cpp
```

The dashboard supports upload, start, progress polling, errors, severity grouping, evidence expansion, and final findings.

## End-to-end test

Create a job:

```fish
curl -sS -X POST http://127.0.0.1:8000/api/jobs \
  -F 'file=@test-data/Cultive8_Workspace_Agrigen_Server.log'
```

Start it using the returned ID:

```fish
curl -sS -X POST http://127.0.0.1:8000/api/jobs/JOB_ID/start
```

Poll status:

```fish
curl -sS http://127.0.0.1:8000/api/jobs/JOB_ID | python -m json.tool
```

Read findings:

```fish
curl -sS http://127.0.0.1:8000/api/jobs/JOB_ID/findings | python -m json.tool
```

The supplied 258-line log should produce consolidated findings for:

- Brute force and possible compromise: `203.0.113.44`
- SQL injection: `203.0.113.72`
- Endpoint scanning: `203.0.113.90`
- Path traversal: `203.0.113.90`
- Unusual request rate: `203.0.113.155`

Normal GET requests, browser metadata, database timeouts, and prompt-injection text must not be reported as confirmed attacks. Create a new job after code changes; existing jobs retain their original results.

## API

```text
GET  /health
POST /api/jobs
POST /api/jobs/{job_id}/start
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/findings
```

Finding response structure remains:

```json
[
  {
    "attack_type": "sql_injection",
    "severity": "High",
    "actor_id": "203.0.113.72",
    "evidence": [{"line": 29, "summary": "..."}],
    "reason": "...",
    "suggested_action": "..."
  }
]
```

## Tests and quality checks

Backend:

```fish
cd backend
source .venv/bin/activate.fish
pytest -q
ruff check app tests
```

Frontend:

```fish
cd frontend
npm run build
npm run lint
```

Latest verification:

```text
Backend: 34 tests passed
Ruff: passed
Frontend production build: passed
Frontend lint: passed
```

Backend tests mock llama.cpp; live testing requires the local model server.

## GitHub submission hygiene

Commit source, tests, and documentation. Do not commit:

- `backend/.venv/`, `backend/data/`, or `backend/uploads/`
- `frontend/node_modules/` or `frontend/dist/`
- `models/*.gguf`
- `llama.cpp/`
- `.env` files, SQLite databases, or runtime logs
- `VIDEO_SCRIPT.md` (local presentation material)

Review before committing:

```fish
git status --short --ignored
git diff --check
```

`.env.example`, source code, tests, `README.md`, `AI_USAGE.md`, `doc.md`, and `test-data/` remain submission-visible.

## Known limitations

- One analysis job runs at a time.
- The background task is process-local, not a distributed queue.
- Automatic restart-resume is not implemented.
- Inference speed depends on CPU performance and GGUF quantization.
- The exact model URL, checksum, and tested llama.cpp commit must be recorded before submission.
- Novel LLM findings require a source-level security signal as false-positive protection.
