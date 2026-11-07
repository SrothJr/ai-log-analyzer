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
models/Qwen3.5-0.8B-Q4_0.gguf
```

The exact artifact used by this project is:

```text
Model:        Qwen3.5 0.8B
Repository:   ggml-org/Qwen3.5-0.8B-GGUF
Filename:     Qwen3.5-0.8B-Q4_0.gguf
Quantization: Q4_0
File size:    563 MB
Revision:     4c11520cef475dd40ed72ec4a1e68b26721bd769
SHA-256:      57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf
Download:     https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/resolve/4c11520cef475dd40ed72ec4a1e68b26721bd769/Qwen3.5-0.8B-Q4_0.gguf
```

```fish
sha256sum models/Qwen3.5-0.8B-Q4_0.gguf
```

Do not commit the model file.

## Manual setup and execution

The manual workflow is useful when reviewing or modifying one component at a time. The commands below are the exact commands used during development.

### 1. Build llama.cpp

```fish
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
git checkout cd959bae9
cmake -B build \
  -DGGML_NATIVE=OFF \
  -DGGML_CUDA=OFF \
  -DGGML_OPENCL=OFF \
  -DGGML_VULKAN=OFF
cmake --build build --config Release -j2
cd ..
```

The tested llama.cpp release was `v0.9.0`, commit `cd959bae9`.

Start the model server:

```fish
./llama.cpp/build/bin/llama-server \
  -m ./models/Qwen3.5-0.8B-Q4_0.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  -c 2048 \
  -t 2 \
  -ngl 0 \
  -np 1 \
  --reasoning off \
  --reasoning-format none
```

Verify the endpoints used by this project:

```fish
curl http://127.0.0.1:8080/health
curl -X POST http://127.0.0.1:8080/tokenize \
  -H 'Content-Type: application/json' \
  -d '{"content":"1: test log line","add_special":false}'
```

The application uses `/tokenize` and `/v1/chat/completions`. `/v1/models` is optional and a 404 there is harmless.

### 2. Install and start the backend

```fish
cd backend
python -m venv .venv
```

Activate the environment in the shell you are using:

```fish
# CachyOS/Linux with Fish
source .venv/bin/activate.fish
```

```bash
# macOS/Linux with Bash or Zsh
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Then continue with:

```text
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cp ../.env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

On Windows PowerShell, use `Copy-Item ..\.env.example .env` instead of `cp ../.env.example .env`.

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

### 3. Install and start the frontend

Open a second terminal:

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

## One-command recreation

After installing the system prerequisites, run the complete workflow from the repository root:

```text
python scripts/run_local.py
```

The launcher works on Windows, macOS, Linux, and CachyOS. It automatically downloads and verifies the exact model, clones/checks out and builds llama.cpp at `cd959bae9`, creates the Python virtual environment, installs backend and frontend dependencies, creates `backend/.env`, resolves platform-specific executable paths, starts llama.cpp with the exact tested flags, waits for both health endpoints, starts FastAPI with `python -m uvicorn`, and then starts Vite.

### Required system dependencies

These must be installed before running the script because they are operating-system tools, not project packages:

- Python 3 with the `venv` module
- Git
- CMake
- A native C/C++ compiler toolchain
- Node.js and npm

Examples:

- **CachyOS/Arch:** `sudo pacman -S --needed base-devel cmake git python python-pip python-venv nodejs npm`
- **Windows:** Python, Git, CMake, Node.js/npm, and Visual Studio Build Tools with C++ workload
- **macOS:** Xcode Command Line Tools, Homebrew Git/CMake/Node.js, and Python 3

### Dependencies installed by the script

The script installs or creates the project-specific dependencies automatically:

- `backend/.venv/` and the packages in `backend/requirements-dev.txt`
- `frontend/node_modules/` from `frontend/package.json`
- The pinned llama.cpp source and CPU-only build
- The exact Qwen3.5 GGUF model, including SHA-256 verification
- `backend/.env` copied from `.env.example`

The first run downloads approximately 563 MB and compiles llama.cpp, so it may take several minutes. Later runs reuse the downloaded model, build, virtual environment, and npm packages.

For a backend-only run:

```text
python scripts/run_local.py --no-frontend
```

To skip setup when everything is already installed:

```text
python scripts/run_local.py --skip-setup
```

Stop all three processes with `Ctrl+C`.

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

## Known limitations

- One analysis job runs at a time.
- The background task is process-local, not a distributed queue.
- Automatic restart-resume is not implemented.
- Inference speed depends on CPU performance and GGUF quantization.
- Novel LLM findings require a source-level security signal as false-positive protection.
