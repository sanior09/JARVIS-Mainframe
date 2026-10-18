"""
JarvisCore — SLM Training Pipeline (v2.0 Modernized)
====================================================
Trains the custom JarvisLanguageModel on the bilingual Thai-English corpus.
100% In-House from 0 to 100 with PyTorch CUDA acceleration.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add C:\JarvisCore to path
CORE_DIR = Path(r"C:\JarvisCore")
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

import torch
from tqdm import tqdm

from brain.model import JarvisLanguageModel
from brain.tokenizer import CharacterTokenizer
from data.dataset import get_dataloaders

# ─── Hyperparameters ───────────────
batch_size = 32
block_size = 256         # Expanded Context Window
max_iters = 600          # Fast & high convergence
eval_interval = 50
learning_rate = 5e-4
eval_iters = 10
n_embd = 256
n_head = 4
n_layer = 4
dropout = 0.15
device = "cuda" if torch.cuda.is_available() else "cpu"
dataset_path = str(CORE_DIR / "dataset" / "input.txt")
checkpoint_path = str(CORE_DIR / "model_ckpt.pt")
# ────────────────────────────────────


@torch.no_grad()
def estimate_loss(model, train_loader, val_loader, eval_iters):
    """Evaluates the model on train and val sets to get average loss."""
    out = {}
    model.eval()

    for split, loader in [("train", train_loader), ("val", val_loader)]:
        losses = torch.zeros(eval_iters)
        data_iter = iter(loader)

        for k in range(eval_iters):
            try:
                X, Y = next(data_iter)
            except StopIteration:
                data_iter = iter(loader)
                X, Y = next(data_iter)

            X, Y = X.to(device), Y.to(device)
            _, loss, _ = model(X, Y)
            losses[k] = loss.item()

        out[split] = losses.mean().item()

    model.train()
    return out


def main():
    print(f"--- JarvisCore SLM v2.0 Training (Device: {device.upper()}) ---")

    if not os.path.exists(dataset_path):
        print(f"Error: Dataset '{dataset_path}' not found.")
        return

    # 1. Load Dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        text = f.read()

    print(f"Loaded dataset: {len(text):,} characters")

    # 2. Train Tokenizer
    tokenizer = CharacterTokenizer()
    tokenizer.train(text)
    vocab_size = tokenizer.vocab_size
    print(f"Bilingual Vocab Size: {vocab_size} unique characters/tokens")

    # 3. Create DataLoaders
    train_loader, val_loader = get_dataloaders(text, tokenizer, block_size, batch_size)

    # 4. Initialize Modernized Architecture Model
    model = JarvisLanguageModel(
        vocab_size=vocab_size,
        n_embd=n_embd,
        n_head=n_head,
        n_layer=n_layer,
        block_size=block_size,
        dropout=dropout,
    )
    model.to(device)

    num_params = sum(p.numel() for p in model.parameters())
    print(f"Model Parameters: {num_params / 1e6:.2f} Million")

    # 5. Optimizer & Cosine Annealing LR Schedule
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_iters, eta_min=5e-5)

    # 6. Training Loop
    print("\nStarting In-House Neural Training...")
    train_iter = iter(train_loader)

    pbar = tqdm(range(max_iters), desc="Training SLM")
    for iter_num in pbar:
        if iter_num % eval_interval == 0 or iter_num == max_iters - 1:
            losses = estimate_loss(model, train_loader, val_loader, eval_iters)
            pbar.set_description(f"Iter {iter_num} | Train Loss: {losses['train']:.4f} | Val Loss: {losses['val']:.4f}")

            # Save checkpoint with full self-describing config
            torch.save(
                {
                    "iter": iter_num,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "train_loss": losses["train"],
                    "val_loss": losses["val"],
                    "chars": tokenizer.chars,
                    "config": {
                        "n_embd": n_embd,
                        "n_head": n_head,
                        "n_layer": n_layer,
                        "block_size": block_size,
                        "vocab_size": vocab_size,
                    },
                },
                checkpoint_path,
            )

        # Sample next training batch
        try:
            xb, yb = next(train_iter)
        except StopIteration:
            train_iter = iter(train_loader)
            xb, yb = next(train_iter)

        xb, yb = xb.to(device), yb.to(device)

        _, loss, _ = model(xb, yb)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

    print(f"\nTraining Complete! Checkpoint saved successfully to {checkpoint_path}")


if __name__ == "__main__":
    main()
