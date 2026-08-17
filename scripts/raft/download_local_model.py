"""
CareFlow Intelligence: Reliable Model Downloader (Curl Backend)
Uses Windows native curl with auto-resume (-C -) and auto-retry to download Qwen3-4B.
"""

import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

LOCAL_MODEL_DIR = PROJECT_ROOT / "models" / "base_models" / "Qwen3-4B-bnb-4bit"
LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)

REPO_ID = "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit"
FILES = [
    "config.json",
    "generation_config.json",
    "chat_template.jinja",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "tokenizer.json",
    "model.safetensors",
]

token = os.getenv("HF_TOKEN") or os.getenv("HF_token")
auth_header = f"Authorization: Bearer {token}" if token else ""


def download_with_curl(filename: str):
    target = LOCAL_MODEL_DIR / filename
    if target.exists() and target.stat().st_size > 0 and filename != "model.safetensors":
        print(f"  [Cached] {filename} ({target.stat().st_size / 1024:.1f} KB)")
        return

    # Check if model.safetensors is already fully downloaded (~3.3 GB)
    if filename == "model.safetensors" and target.exists() and target.stat().st_size > 3400 * 1024 * 1024:
        print(f"  [Cached] model.safetensors ({target.stat().st_size / (1024*1024):.2f} MB)")
        return

    url = f"https://huggingface.co/{REPO_ID}/resolve/main/{filename}"
    print(f"\n>>> Downloading {filename} (Resumable)...")

    cmd = [
        "curl.exe",
        "-L",
        "-C", "-",                    # Resume partial download if interrupted
        "--retry", "10",              # Retry up to 10 times on network drop
        "--retry-delay", "2",
        "--connect-timeout", "30",
        "--progress-bar",
        url,
        "-o", str(target),
    ]
    if auth_header:
        cmd.extend(["-H", auth_header])

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"  [Warning] Curl exited with code {result.returncode} for {filename}")
    else:
        print(f"  [Complete] {filename} saved ({target.stat().st_size / (1024*1024):.2f} MB)")


def main():
    print("=" * 65)
    print("CAREFLOW RESUMABLE MODEL DOWNLOADER (QWEN 3 - 4B)")
    print(f"Repository: {REPO_ID}")
    print(f"Target:     {LOCAL_MODEL_DIR}")
    print("=" * 65)

    for f in FILES:
        download_with_curl(f)

    print("\n" + "=" * 65)
    print("ALL QWEN 3 (4B) MODEL ASSETS DOWNLOADED AND READY ON DISK!")
    print(f"Path: {LOCAL_MODEL_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
