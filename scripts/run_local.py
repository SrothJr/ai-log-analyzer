"""Recreate and run the local workflow on Windows, macOS, or Linux."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
MODEL_FILENAME = "Qwen3.5-0.8B-Q4_0.gguf"
MODEL_PATH = ROOT / "models" / MODEL_FILENAME
MODEL_URL = (
    "https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/resolve/"
    "4c11520cef475dd40ed72ec4a1e68b26721bd769/"
    f"{MODEL_FILENAME}?download=true"
)
MODEL_SHA256 = "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"
LLAMA_REPOSITORY = "https://github.com/ggml-org/llama.cpp.git"
LLAMA_COMMIT = "cd959bae9"


def run(command: list[str], cwd: Path = ROOT) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def require_commands() -> None:
    required = ["git", "cmake", "npm"]
    missing = [name for name in required if not command_exists(name)]
    if missing:
        raise RuntimeError(
            "Missing system prerequisite(s): "
            + ", ".join(missing)
            + ". Install Git, CMake, a C/C++ compiler toolchain, and Node.js/npm using your platform's package manager."
        )


def executable(candidates: list[Path], fallback: str) -> str:
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return fallback


def python_in_venv() -> Path:
    candidates = [
        ROOT / "backend" / ".venv" / "bin" / "python",
        ROOT / "backend" / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError("The backend virtual environment could not be created.")


def setup_python() -> Path:
    venv_python = (
        ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else ROOT / "backend" / ".venv" / "bin" / "python"
    )
    if not venv_python.exists():
        run([sys.executable, "-m", "venv", str(ROOT / "backend" / ".venv")])
    venv_python = python_in_venv()
    run([str(venv_python), "-m", "pip", "install", "-r", "requirements-dev.txt"], ROOT / "backend")
    return venv_python


def setup_frontend() -> None:
    run(["npm.cmd" if os.name == "nt" else "npm", "install"], ROOT / "frontend")


def setup_llama() -> Path:
    llama_directory = ROOT / "llama.cpp"
    if not llama_directory.exists():
        run(["git", "clone", LLAMA_REPOSITORY, str(llama_directory)])
    run(["git", "fetch", "--tags", "origin"], llama_directory)
    current = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=llama_directory, check=True, capture_output=True, text=True
    ).stdout.strip()
    if not current.startswith(LLAMA_COMMIT):
        run(["git", "checkout", LLAMA_COMMIT], llama_directory)

    build_directory = llama_directory / "build"
    run(
        [
            "cmake",
            "-S",
            str(llama_directory),
            "-B",
            str(build_directory),
            "-DGGML_NATIVE=OFF",
            "-DGGML_CUDA=OFF",
            "-DGGML_OPENCL=OFF",
            "-DGGML_VULKAN=OFF",
        ]
    )
    run(["cmake", "--build", str(build_directory), "--config", "Release", "--parallel", "2"])
    return Path(
        executable(
            [
                build_directory / "bin" / "llama-server",
                build_directory / "bin" / "llama-server.exe",
                build_directory / "bin" / "Release" / "llama-server.exe",
            ],
            "llama-server",
        )
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def setup_model() -> None:
    if MODEL_PATH != ROOT / "models" / MODEL_FILENAME:
        if not MODEL_PATH.exists():
            raise RuntimeError(f"Model not found: {MODEL_PATH}")
        return
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        print(f"Downloading {MODEL_FILENAME} (approximately 563 MB)...")
        temporary = MODEL_PATH.with_suffix(".download")
        request = Request(MODEL_URL, headers={"User-Agent": "ai-log-analyzer-setup"})
        with urlopen(request, timeout=60) as response, temporary.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
        temporary.replace(MODEL_PATH)
    print("Verifying model checksum...")
    if sha256(MODEL_PATH) != MODEL_SHA256:
        raise RuntimeError(f"SHA-256 mismatch for {MODEL_PATH}")


def setup_environment() -> tuple[Path, Path]:
    require_commands()
    setup_model()
    llama_binary = setup_llama()
    backend_python = setup_python()
    setup_frontend()
    env_file = ROOT / "backend" / ".env"
    if not env_file.exists():
        shutil.copyfile(ROOT / ".env.example", env_file)
    return llama_binary, backend_python


def wait_for(url: str, process: subprocess.Popen[bytes], timeout: float = 45) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Process exited before becoming ready: {url}")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except (OSError, URLError):
            time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for {url}")


def stop_processes(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    for process in reversed(processes):
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    global MODEL_PATH
    parser = argparse.ArgumentParser(description="Set up and run the complete local workflow.")
    parser.add_argument("--model", type=Path, default=MODEL_PATH, help="Override the GGUF model path")
    parser.add_argument("--no-frontend", action="store_true", help="Start only llama.cpp and FastAPI")
    parser.add_argument("--skip-setup", action="store_true", help="Use already-installed dependencies")
    args = parser.parse_args()

    if args.model != MODEL_PATH:
        MODEL_PATH = args.model if args.model.is_absolute() else ROOT / args.model

    processes: list[subprocess.Popen[bytes]] = []
    try:
        if args.skip_setup:
            if not MODEL_PATH.exists():
                raise RuntimeError(f"Model not found: {MODEL_PATH}")
            llama_binary = Path(
                executable(
                    [
                        ROOT / "llama.cpp" / "build" / "bin" / "llama-server",
                        ROOT / "llama.cpp" / "build" / "bin" / "llama-server.exe",
                        ROOT / "llama.cpp" / "build" / "bin" / "Release" / "llama-server.exe",
                    ],
                    "llama-server",
                )
            )
            backend_python = python_in_venv()
        else:
            llama_binary, backend_python = setup_environment()

        llama_command = [
            str(llama_binary),
            "-m",
            str(MODEL_PATH),
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
            "-c",
            "2048",
            "-t",
            "2",
            "-ngl",
            "0",
            "-np",
            "1",
            "--reasoning",
            "off",
            "--reasoning-format",
            "none",
        ]
        backend_command = [str(backend_python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
        npm_binary = "npm.cmd" if os.name == "nt" else "npm"
        frontend_command = [npm_binary, "run", "dev", "--", "--host", "127.0.0.1"]

        print("Starting llama.cpp...")
        processes.append(subprocess.Popen(llama_command, cwd=ROOT))
        wait_for("http://127.0.0.1:8080/health", processes[-1])

        print("Starting FastAPI...")
        processes.append(subprocess.Popen(backend_command, cwd=ROOT / "backend"))
        wait_for("http://127.0.0.1:8000/health", processes[-1])

        if not args.no_frontend:
            print("Starting Vite at http://127.0.0.1:5173 ...")
            processes.append(subprocess.Popen(frontend_command, cwd=ROOT / "frontend"))

        print("Local workflow is running. Press Ctrl+C to stop all processes.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping local workflow...")
    except (OSError, RuntimeError, TimeoutError, subprocess.CalledProcessError) as error:
        print(f"Setup/startup failed: {error}", file=sys.stderr)
        return 1
    finally:
        stop_processes(processes)
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.default_int_handler)
    raise SystemExit(main())
