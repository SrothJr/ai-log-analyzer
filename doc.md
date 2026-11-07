# Implementation Progress

## Current phase

Detection and correlation correction implemented; live-model verification remains.

## Completed

- Inspected the assessment requirements and existing repository.
- Confirmed the repository contains no existing application implementation.
- Added project-specific `.gitignore` rules for runtime databases, uploads, local models, llama.cpp build output, frontend dependencies, and local configuration.
- Added a pinned backend dependency specification.
- Added a development dependency specification for tests and linting.
- Added environment configuration documentation through `.env.example`.
- Added the initial FastAPI application structure.
- Added SQLite initialization and a health endpoint.
- Created a Python 3.14 virtual environment and installed the pinned development dependencies.
- Kept the Python 3.14-compatible Pydantic 2.14 wheel and used string UUID values for SQLModel job IDs after testing showed the older Pydantic core required an unsupported Python 3.14 Rust build.
- Added upload validation and persisted queued analysis jobs in SQLite.
- Added a llama.cpp HTTP tokenizer client and line-preserving asynchronous splitter.
- Added serialized llama.cpp chat completion, strict structured-output validation, and safe retry handling.
- Added persisted sequential analysis chunks and findings.
- Added deterministic cross-chunk deduplication and a final local-model correlation pass with fallback behavior.
- Added structured deterministic observations, source-file evidence validation, actor consistency checks, and generic SQL injection, brute-force, scanning, path-traversal, and request-rate detectors.
- Changed the final report to use deterministic findings as the evidence authority; the local model can only provide explanations for already validated candidates.
- Rebalanced the design into a hybrid: deterministic observations are hints and safety guards, while validated LLM findings can add novel attack categories.
- Added semantic normalization so model aliases such as `DoS attack`, `endpoint_scan`, and `authentication_failure` merge into the canonical report instead of creating duplicate cards.
- Made deterministic findings authoritative for known attack families, while retaining validated novel LLM findings and rejecting generic placeholder labels.
- Added concise reason/action aggregation and a generic security-signal check for novel model findings.
- Added the React/Vite upload, progress, error, and final-report dashboard.
- Added CORS configuration for the local Vite development server.

## Why these changes were made

- Runtime data and model artifacts must not be committed.
- Pinned dependencies make the project reproducible.
- Configuration must be externalized so resource limits and local service URLs can be changed without editing code.
- A health endpoint, database bootstrap, and upload boundary provide small, independently testable foundations before inference work begins.

## Tests completed

- `pytest -q`: **34 passed** including supplied-log ground-truth detection tests.
- `ruff check app tests`: **passed**.
- Verified the health endpoint returns `{"status": "ok"}` through FastAPI's test client.
- Upload tests cover UTF-8 validation, extension rejection, job creation, and job retrieval.
- Splitter tests cover exact rendered-token budgets, complete-line boundaries, line ranges, and invalid budgets.
- Tokenizer tests cover llama.cpp token responses and malformed responses.
- Pipeline tests verify chunk and finding persistence with a fake local model.
- Correlation tests verify duplicate merging, evidence preservation, and severity selection.
- Ground-truth tests verify SQL injection, endpoint scanning, path traversal, request-rate anomalies, prompt-injection isolation, login correlation, evidence validation, and actor consistency.
- Full backend result: `34 passed`; `ruff check app tests`: passed.
- Frontend `npm run build`: passed.
- Frontend `npm run lint`: passed.
- Runtime artifacts remain ignored; no Git commit was created.

The test run emits dependency deprecation warnings under Python 3.14, but no test failures.

## Remaining work

1. Restart the backend so SQLite creates the new `observationrecord` table.
2. Run a new analysis job using `test-data/Cultive8_Workspace_Agrigen_Server.log`; do not restart the existing baseline job.
3. Verify the live report contains the five requested attack categories and excludes ordinary GETs/timeouts.
4. Record the live model checksum and llama.cpp commit in `README.md`.
5. Perform manual browser verification of progress, failure, and report states.

## Confirmed decisions

- Use the configured placeholder path `models/qwen3.5-0.8b-q4.gguf`.
- Use the matching llama.cpp HTTP tokenizer endpoint without loading a second model.
