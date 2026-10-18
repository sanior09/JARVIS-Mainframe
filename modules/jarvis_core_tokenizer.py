"""
JarvisCore — Custom Bilingual Tokenizer (Thai & English)
========================================================
100% In-House Pure Python Character-Level & Subword Tokenizer.
Zero external library dependencies.
Supports:
- Thai alphabet (ก-ฮ, สระ, วรรณยุกต์, ฯ, ๆ, ฯลฯ)
- English alphabet (a-z, A-Z)
- Digits (0-9, ๐-๙)
- Code & Punctuation symbols
- Special Tokens (<PAD>, <UNK>, <BOS>, <EOS>)
"""

from __future__ import annotations

from typing import Dict, List, Optional


class CharacterTokenizer:
    """Bilingual Thai-English Tokenizer built from scratch with zero external dependencies."""

    PAD_TOKEN = "<PAD>"
    UNK_TOKEN = "<UNK>"
    BOS_TOKEN = "<BOS>"
    EOS_TOKEN = "<EOS>"

    def __init__(self) -> None:
        self.chars: List[str] = []
        self.vocab_size: int = 0
        self.stoi: Dict[str, int] = {}
        self.itos: Dict[int, str] = {}
        self.special_tokens = [self.PAD_TOKEN, self.UNK_TOKEN, self.BOS_TOKEN, self.EOS_TOKEN]

    def train(self, text: str) -> None:
        """Extracts unique characters from the training corpus and builds the vocabulary mapping."""
        # Find all unique characters in text
        unique_chars = sorted(list(set(text)))

        # Build vocabulary: Special tokens first, followed by unique characters
        self.chars = list(self.special_tokens)
        for ch in unique_chars:
            if ch not in self.chars:
                self.chars.append(ch)

        self.vocab_size = len(self.chars)
        self.stoi = {ch: i for i, ch in enumerate(self.chars)}
        self.itos = {i: ch for i, ch in enumerate(self.chars)}

    def encode(self, text: str, add_special_tokens: bool = False) -> List[int]:
        """Converts a string of text into integer token IDs."""
        if self.vocab_size == 0:
            raise ValueError("Tokenizer has not been trained yet.")

        unk_id = self.stoi.get(self.UNK_TOKEN, 1)
        tokens = [self.stoi.get(c, unk_id) for c in text]

        if add_special_tokens:
            bos_id = self.stoi.get(self.BOS_TOKEN, 2)
            eos_id = self.stoi.get(self.EOS_TOKEN, 3)
            return [bos_id] + tokens + [eos_id]

        return tokens

    def decode(self, tokens: List[int], skip_special_tokens: bool = True) -> str:
        """Converts token IDs back into human-readable text."""
        if self.vocab_size == 0:
            raise ValueError("Tokenizer has not been trained yet.")

        special_set = set(self.special_tokens) if skip_special_tokens else set()
        chars_out = []
        for i in tokens:
            ch = self.itos.get(i, "")
            if ch not in special_set:
                chars_out.append(ch)

        return "".join(chars_out)
