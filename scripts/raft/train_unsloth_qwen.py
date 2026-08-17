"""
CareFlow Intelligence: Unsloth Qwen-3 RAFT Fine-Tuning Script
--------------------------------------------------------------
Fine-tunes Qwen3-4B-Instruct-2507 on CareFlow's clinical RAFT dataset
using Unsloth for 2x-5x faster training and 70% reduced VRAM.
Exports to GGUF for instant local deployment via Ollama / vLLM.
"""

import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Ensure HuggingFace token and environment variables are active
hf_token = os.getenv("HF_TOKEN") or os.getenv("HF_token")
if hf_token:
    os.environ["HF_TOKEN"] = hf_token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token
    try:
        import huggingface_hub
        huggingface_hub.login(token=hf_token, add_to_git_credential=False)
    except Exception:
        pass

os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Clean up any stale incomplete download locks on Windows
try:
    cache_hub = Path.home() / ".cache" / "huggingface" / "hub"
    if cache_hub.exists():
        for inc in cache_hub.rglob("*.incomplete"):
            try:
                inc.unlink(missing_ok=True)
            except Exception:
                pass
except Exception:
    pass

DATA_DIR = PROJECT_ROOT / "data" / "raft"
OUTPUT_DIR = PROJECT_ROOT / "models" / "careflow_qwen_raft"
GGUF_DIR = PROJECT_ROOT / "models" / "careflow_qwen_gguf"
LOCAL_BASE_MODEL = PROJECT_ROOT / "models" / "base_models" / "Qwen3-4B-bnb-4bit"


def resolve_model_path(model_identifier: str | None = None) -> str:
    """Resolve model to local cached directory if available to prevent network stalls."""
    if model_identifier and Path(model_identifier).exists():
        return model_identifier

    # 1. Check local models/base_models directory (must be full file > 500MB)
    local_safetensor = LOCAL_BASE_MODEL / "model.safetensors"
    if local_safetensor.exists() and local_safetensor.stat().st_size > 500 * 1024 * 1024:
        return str(LOCAL_BASE_MODEL)

    # 2. Check local Hugging Face cache snapshots (e.g. Qwen2.5-1.5B)
    hub_cache = Path.home() / ".cache" / "huggingface" / "hub"
    for pattern in ["models--Qwen--Qwen2.5-1.5B/snapshots/*", "models--unsloth--qwen3-4b-instruct-2507-unsloth-bnb-4bit/snapshots/*"]:
        matches = list(hub_cache.glob(pattern))
        if matches:
            sf = matches[0] / "model.safetensors"
            if sf.exists() and sf.stat().st_size > 500 * 1024 * 1024:
                return str(matches[0])

    return model_identifier or "Qwen/Qwen2.5-1.5B"


def run_unsloth_training(
    model_name: str | None = None,
    max_seq_length: int = 2048,
    train_file: str = str(DATA_DIR / "raft_chat_train.jsonl"),
    val_file: str = str(DATA_DIR / "raft_chat_val.jsonl"),
    output_dir: str = str(OUTPUT_DIR),
    gguf_dir: str = str(GGUF_DIR),
    export_gguf: bool = True,
    quant_method: str = "q4_k_m",
    epochs: int = 3,
    batch_size: int = 2,
    grad_accum_steps: int = 4,
    learning_rate: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 16,
):
    model_name = resolve_model_path(model_name)
    try:
        import torch
        from unsloth import FastLanguageModel
        from unsloth.chat_templates import get_chat_template
        from datasets import load_dataset
        from transformers import TrainingArguments
        from trl import SFTTrainer
    except ImportError:
        print("[Unsloth] Required ML packages not found.")
        print("Install: pip install 'unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git' trl peft accelerate")
        return

    print("=" * 65)
    print("CAREFLOW RAFT UNSLOTH TRAINING (QWEN 2.5)")
    print(f"Base Model:     {model_name}")
    print(f"Dataset:        {train_file}")
    print(f"Max Seq Length: {max_seq_length}")
    print("=" * 65)

    # 1. Load Pre-quantized Model
    print("\n[1/5] Loading Qwen model via FastLanguageModel...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )

    # 2. Add LoRA Adapters
    print("\n[2/5] Setting up LoRA configuration...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_r,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=lora_alpha,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    # 3. Apply Chat Template & Format Dataset
    print("\n[3/5] Formatting clinical ChatML dataset...")
    tokenizer = get_chat_template(tokenizer, chat_template="qwen-2.5")

    def formatting_prompts_func(examples):
        convos = examples["messages"]
        texts = [
            tokenizer.apply_chat_template(convo, tokenize=False, add_generation_prompt=False)
            for convo in convos
        ]
        return {"text": texts}

    data_files = {"train": train_file}
    dataset = load_dataset("json", data_files=data_files)
    dataset = dataset.map(formatting_prompts_func, batched=True)

    # 4. Training
    print("\n[4/5] Starting SFTTrainer execution...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"],
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        dataset_num_proc=1,
        packing=False,
        args=TrainingArguments(
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=grad_accum_steps,
            warmup_ratio=0.1,
            learning_rate=learning_rate,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            seed=3407,
            output_dir=output_dir,
            report_to="none",
        ),
    )
    trainer.train()

    # 5. Save LoRA & Optional GGUF export
    print(f"\n[5/5] Saving fine-tuned LoRA model to: {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    if export_gguf:
        print(f"\n[Export] Exporting to GGUF ({quant_method}) for Ollama/vLLM to: {gguf_dir}...")
        model.save_pretrained_gguf(gguf_dir, tokenizer, quantization_method=quant_method)
        print(f"[Export] GGUF file generated in: {gguf_dir}")

    print("\n" + "=" * 65)
    print("UNSLOTH RAFT FINE-TUNING COMPLETED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CareFlow Unsloth Qwen RAFT Fine-Tuning")
    parser.add_argument("--model", type=str, default=None, help="HuggingFace model ID or local directory")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--no-gguf", action="store_true", help="Skip GGUF export")
    args = parser.parse_args()

    run_unsloth_training(
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        export_gguf=not args.no_gguf,
    )
