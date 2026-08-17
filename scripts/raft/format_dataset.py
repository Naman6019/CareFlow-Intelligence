import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = PROJECT_ROOT / "data" / "raft"

SYSTEM_PROMPT = """You are CareFlow Intelligence, a high-precision clinical AI assistant.
Answer clinical questions using ONLY the provided evidence blocks.
Your reasoning must explain why irrelevant distractors are rejected.
Cite every supporting factual statement with exact chunk markers like `[chunk: 123]`."""


def format_dataset():
    raw_file = DATASET_DIR / "raft_raw_dataset.json"
    if not raw_file.exists():
        print(f"Error: {raw_file} not found. Run generate_dataset.py first.")
        return

    with raw_file.open("r", encoding="utf-8") as f:
        samples = json.load(f)

    if not samples:
        print("Error: No samples in dataset.")
        return

    random.seed(42)
    random.shuffle(samples)

    split_idx = int(len(samples) * 0.8)
    train_samples = samples[:split_idx]
    val_samples = samples[split_idx:]

    print(f"[RAFT Formatter] Total samples: {len(samples)} -> Train: {len(train_samples)}, Val: {len(val_samples)}")

    # 1. Export OpenAI / OpenRouter ChatML format (jsonl)
    def to_chat_format(sample: dict) -> dict:
        user_content = f"### Clinical Context:\n{sample['context_text']}\n\n### Question:\n{sample['question']}"
        assistant_content = f"### Clinical Reasoning:\n{sample['chain_of_thought']}\n\n### Answer:\n{sample['answer']}"
        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ]
        }

    for name, subset in [("train", train_samples), ("val", val_samples)]:
        chat_file = DATASET_DIR / f"raft_chat_{name}.jsonl"
        with chat_file.open("w", encoding="utf-8") as f:
            for s in subset:
                f.write(json.dumps(to_chat_format(s)) + "\n")
        print(f"  [Exported] {chat_file}")

    # 2. Export HuggingFace / Unsloth Alpaca instruction format (jsonl)
    def to_alpaca_format(sample: dict) -> dict:
        return {
            "instruction": f"Answer the clinical question based strictly on the provided context with citations.\n\nQuestion: {sample['question']}",
            "input": sample["context_text"],
            "output": f"## Clinical Reasoning\n{sample['chain_of_thought']}\n\n## Answer\n{sample['answer']}",
        }

    for name, subset in [("train", train_samples), ("val", val_samples)]:
        alpaca_file = DATASET_DIR / f"raft_alpaca_{name}.jsonl"
        with alpaca_file.open("w", encoding="utf-8") as f:
            for s in subset:
                f.write(json.dumps(to_alpaca_format(s)) + "\n")
        print(f"  [Exported] {alpaca_file}")

    print("\n[RAFT Formatter] Dataset preparation complete!")


if __name__ == "__main__":
    format_dataset()
