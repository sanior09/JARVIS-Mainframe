"""
JarvisCore — Language Model Architecture (v2.0 Modernized)
===========================================================
100% In-House Decoder-only Transformer model built from scratch using PyTorch.
Features:
- RMSNorm (Root Mean Square Layer Normalization) for high numerical stability
- GELU Feed-Forward Networks with residual skip connections
- Multi-Head Self-Attention with O(1) Key-Value (KV) Cache inference
- Weight Tying between Embedding and LM Head for maximum parameter efficiency
- Fully autonomous from 0 to 100 with zero external dependencies.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import torch
import torch.nn as nn
from torch.nn import functional as F


class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization (modern LLaMA/Gemma standard)."""

    def __init__(self, dim: int, eps: float = 1e-6) -> None:
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        variance = x.pow(2).mean(-1, keepdim=True)
        return x * torch.rsqrt(variance + self.eps) * self.weight


class Head(nn.Module):
    """Single attention head with causal masking and Key-Value (KV) caching."""

    def __init__(self, n_embd: int, head_size: int, block_size: int, dropout: float) -> None:
        super().__init__()
        self.key = nn.Linear(n_embd, head_size, bias=False)
        self.query = nn.Linear(n_embd, head_size, bias=False)
        self.value = nn.Linear(n_embd, head_size, bias=False)

        self.register_buffer("tril", torch.tril(torch.ones(block_size, block_size)))
        self.dropout = nn.Dropout(dropout)
        self.scale = 1.0 / math.sqrt(head_size)

    def forward(
        self,
        x: torch.Tensor,
        past_kv: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        B, T, C = x.shape
        k = self.key(x)    # (B, T, head_size)
        q = self.query(x)  # (B, T, head_size)
        v = self.value(x)  # (B, T, head_size)

        if past_kv is not None:
            past_k, past_v = past_kv
            k = torch.cat((past_k, k), dim=1)
            v = torch.cat((past_v, v), dim=1)

        present_kv = (k, v) if use_cache else None

        # Scaled dot-product attention
        wei = (q @ k.transpose(-2, -1)) * self.scale  # (B, T, T_total)
        T_total = k.shape[1]
        T_past = T_total - T

        if T > 1:
            causal_mask = self.tril[:T, :T] == 0
            wei[:, :, T_past:] = wei[:, :, T_past:].masked_fill(causal_mask, float("-inf"))

        wei = F.softmax(wei, dim=-1)
        wei = self.dropout(wei)

        out = wei @ v  # (B, T, head_size)
        return out, present_kv


class MultiHeadAttention(nn.Module):
    """Parallel multi-head self-attention block."""

    def __init__(self, n_embd: int, num_heads: int, head_size: int, block_size: int, dropout: float) -> None:
        super().__init__()
        self.heads = nn.ModuleList([Head(n_embd, head_size, block_size, dropout) for _ in range(num_heads)])
        self.proj = nn.Linear(head_size * num_heads, n_embd, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x: torch.Tensor,
        past_kv: Optional[List[Tuple[torch.Tensor, torch.Tensor]]] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[List[Tuple[torch.Tensor, torch.Tensor]]]]:
        present_kvs = []
        head_outputs = []

        for i, h in enumerate(self.heads):
            head_past_kv = past_kv[i] if past_kv is not None else None
            out, p_kv = h(x, past_kv=head_past_kv, use_cache=use_cache)
            head_outputs.append(out)
            if use_cache and p_kv is not None:
                present_kvs.append(p_kv)

        out = torch.cat(head_outputs, dim=-1)
        out = self.dropout(self.proj(out))
        return out, (present_kvs if use_cache else None)


class FeedForward(nn.Module):
    """GELU feed-forward network with 4x expansion."""

    def __init__(self, n_embd: int, dropout: float) -> None:
        super().__init__()
        self.w1 = nn.Linear(n_embd, 4 * n_embd, bias=False)
        self.w2 = nn.Linear(4 * n_embd, n_embd, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.w2(F.gelu(self.w1(x))))


class TransformerBlock(nn.Module):
    """Pre-LN Transformer Block communicating via Attention then MLP."""

    def __init__(self, n_embd: int, n_head: int, block_size: int, dropout: float) -> None:
        super().__init__()
        head_size = n_embd // n_head
        self.sa = MultiHeadAttention(n_embd, n_head, head_size, block_size, dropout)
        self.ffwd = FeedForward(n_embd, dropout)
        self.norm1 = RMSNorm(n_embd)
        self.norm2 = RMSNorm(n_embd)

    def forward(
        self,
        x: torch.Tensor,
        past_kv: Optional[List[Tuple[torch.Tensor, torch.Tensor]]] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[List[Tuple[torch.Tensor, torch.Tensor]]]]:
        sa_out, present_kv = self.sa(self.norm1(x), past_kv=past_kv, use_cache=use_cache)
        x = x + sa_out
        x = x + self.ffwd(self.norm2(x))
        return x, present_kv


class JarvisLanguageModel(nn.Module):
    """Complete Decoder-only SLM wrapper with weight tying and KV cache."""

    def __init__(
        self,
        vocab_size: int,
        n_embd: int = 256,
        n_head: int = 4,
        n_layer: int = 4,
        block_size: int = 256,
        dropout: float = 0.15,
    ) -> None:
        super().__init__()
        self.block_size = block_size
        self.vocab_size = vocab_size
        self.n_embd = n_embd
        self.n_head = n_head
        self.n_layer = n_layer

        self.token_embedding_table = nn.Embedding(vocab_size, n_embd)
        self.position_embedding_table = nn.Embedding(block_size, n_embd)

        self.blocks = nn.ModuleList(
            [TransformerBlock(n_embd, n_head, block_size, dropout) for _ in range(n_layer)]
        )

        self.norm_f = RMSNorm(n_embd)
        self.lm_head = nn.Linear(n_embd, vocab_size, bias=False)

        # Weight tying: shared embedding & projection weights
        self.token_embedding_table.weight = self.lm_head.weight

        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self,
        idx: torch.Tensor,
        targets: Optional[torch.Tensor] = None,
        past_kv: Optional[List[List[Tuple[torch.Tensor, torch.Tensor]]]] = None,
        use_cache: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], Optional[List[List[Tuple[torch.Tensor, torch.Tensor]]]]]:
        B, T = idx.shape

        if past_kv is not None and len(past_kv) > 0 and past_kv[0] is not None:
            T_past = past_kv[0][0][0].shape[1]
            pos = torch.arange(T_past, T_past + T, dtype=torch.long, device=idx.device)
        else:
            pos = torch.arange(0, T, dtype=torch.long, device=idx.device)

        # Bound position embedding safely within block_size
        pos = torch.clamp(pos, max=self.block_size - 1)

        tok_emb = self.token_embedding_table(idx)  # (B, T, n_embd)
        pos_emb = self.position_embedding_table(pos)  # (T, n_embd)
        x = tok_emb + pos_emb

        present_kvs = []
        for i, block in enumerate(self.blocks):
            block_past_kv = past_kv[i] if past_kv is not None else None
            x, p_kv = block(x, past_kv=block_past_kv, use_cache=use_cache)
            if use_cache and p_kv is not None:
                present_kvs.append(p_kv)

        x = self.norm_f(x)
        logits = self.lm_head(x)  # (B, T, vocab_size)

        loss = None
        if targets is not None:
            B_out, T_out, C_out = logits.shape
            logits_resh = logits.view(B_out * T_out, C_out)
            targets_resh = targets.view(B_out * T_out)
            loss = F.cross_entropy(logits_resh, targets_resh)

        return logits, loss, (present_kvs if use_cache else None)

    @torch.no_grad()
    def generate(self, idx: torch.Tensor, max_new_tokens: int, temperature: float = 0.8) -> torch.Tensor:
        """Generates new tokens sequentially using KV-Cache for extreme speed."""
        past_kv = None
        for _ in range(max_new_tokens):
            if past_kv is None:
                idx_cond = idx[:, -self.block_size:]
                logits, _, past_kv = self(idx_cond, use_cache=True)
            else:
                idx_cond = idx[:, -1:]
                logits, _, past_kv = self(idx_cond, past_kv=past_kv, use_cache=True)

            logits = logits[:, -1, :] / max(0.1, temperature)
            probs = F.softmax(logits, dim=-1)
            idx_next = torch.multinomial(probs, num_samples=1)
            idx = torch.cat((idx, idx_next), dim=1)

        return idx
