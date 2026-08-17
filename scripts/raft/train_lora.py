"""
CareFlow Intelligence: RAFT LoRA / QLoRA Fine-Tuning Script
-----------------------------------------------------------
Fine-tunes open-weights medical LLMs (e.g. Llama-3.1-8B-Instruct or Qwen-2.5-7B-Instruct)
on the RAFT clinical dataset.
Can be executed locally with CUDA or on cloud GPU instances (Colab, RunPod, Lambda).
"""

import argparse
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raft"
OUTPUT_DIR = PROJECT_ROOT / "models" / "careflow_raft_lora"


def train(
    base_model_name: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
    train_file: str = str(DATA_DIR / "raft_chat_train.jsonl"),
    val_file: str = str(DATA_DIR / "raft_chat_val.jsonl"),
    output_dir: str = str(OUTPUT_DIR),
    epochs: int = 3,
    batch_size: int = 2,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
):
    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
        )
        from trl import SFTTrainer
    except ImportError:
        print("[RAFT Trainer] Missing ML training dependencies.")
        print("To run local fine-tuning, install: pip install torch transformers datasets peft trl bitsandbytes accelerate")
        return

    print("=" * 60)
    print(f"CAREFLOW RAFT FINE-TUNING HARNESS")
    print(f"Base Model: {base_model_name}")
    print(f"Train Dataset: {train_file}")
    print(f"Output Adapter: {output_dir}")
    print("=" * 60)

    # 1. 4-bit Quantization Config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # 2. Load Base Model & Tokenizer
    print("\n[1/4] Loading base model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)

    # 3. LoRA Configuration
    print("\n[2/4] Initializing LoRA adapters...")
    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 4. Load Datasets
    print("\n[3/4] Loading RAFT training datasets...")
    data_files = {"train": train_file}
    if os.path.exists(val_file):
        data_files["validation"] = val_file

    dataset = load_dataset("json", data_files=data_files)

    # 5. Training Arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        logging_steps=5,
        save_strategy="epoch",
        evaluation_strategy="epoch" if "validation" in dataset else "no",
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        max_grad_norm=0.3,
        optim="paged_adamw_8bit",
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        dataset_text_field="messages",
        max_seq_length=2048,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("\n[4/4] Starting RAFT Training...")
    trainer.train()

    print(f"\n[RAFT] Saving fine-tuned LoRA weights to {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("[RAFT] Training complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CareFlow RAFT LoRA Training")
    parser.add_argument("--model", type=str, default="meta-llama/Meta-Llama-3.1-8B-Instruct")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    args = parser.parse_args()

    train(base_model_name=args.model, epochs=args.epochs, batch_size=args.batch_size)
