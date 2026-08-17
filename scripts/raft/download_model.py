"""
CareFlow Intelligence: Reliable Model Pre-Downloader
Downloads Qwen3-4B-Instruct-2507-unsloth-bnb-4bit with clean progress tracking.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

token = os.getenv("HF_TOKEN") or os.getenv("HF_token")
if token:
    os.environ["HF_TOKEN"] = token

# 1. Clean stale locks in HF cache
cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
print(f"[1/3] Inspecting cache directory: {cache_dir}")
if cache_dir.exists():
    for lock in (cache_dir / ".locks").glob("**/*"):
        if lock.is_file():
            try:
                lock.unlink(missing_ok=True)
            except Exception:
                pass
    for inc in cache_dir.glob("**/*.incomplete"):
        try:
            inc.unlink(missing_ok=True)
        except Exception:
            pass
print("[1/3] Cleaned stale lock files.")

# 2. Download model snapshot with standard HTTP streaming
model_id = "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit"
print(f"[2/3] Downloading model snapshot: {model_id} (~3.38 GB)...")

try:
    from huggingface_hub import snapshot_download
    path = snapshot_download(
        repo_id=model_id,
        token=token,
        resume_download=True,
        max_workers=2,
    )
    print(f"\n[3/3] Successfully downloaded and cached model to:\n      {path}")
except Exception as e:
    print(f"\n[Error] Snapshot download failed: {e}")
    sys.exit(1)
