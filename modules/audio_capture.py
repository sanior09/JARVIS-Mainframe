"""Shared raw PCM16 (16 kHz, Mono, int16) audio capture utilities for sounddevice."""

from __future__ import annotations

from collections import deque
import io
import math
import time
import wave
from typing import Callable, Optional

import numpy as np

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
SAMPLE_WIDTH = 2
DEFAULT_BLOCKSIZE = 512


def pcm16_rms(raw_bytes: bytes) -> float:
    """Compute RMS amplitude for little-endian 16-bit signed PCM bytes."""
    if not raw_bytes:
        return 0.0
    samples = np.frombuffer(raw_bytes, dtype=np.int16)
    if samples.size == 0:
        return 0.0
    return float(math.sqrt(float(np.mean(samples.astype(np.float64) ** 2))))


def pcm16_to_wav_bytes(
    pcm_bytes: bytes,
    sample_rate: int = SAMPLE_RATE,
    channels: int = CHANNELS,
) -> bytes:
    """Wrap raw PCM16 mono bytes in an in-memory RIFF/WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def record_utterance_from_stream(
    stream,
    *,
    sample_rate: int = SAMPLE_RATE,
    blocksize: int = DEFAULT_BLOCKSIZE,
    energy_threshold: float = 800.0,
    pause_threshold: float = 0.7,
    listen_timeout: Optional[float] = 5.0,
    phrase_limit: float = 30.0,
    should_stop: Optional[Callable[[], bool]] = None,
    preroll_chunks: int = 8,
) -> bytes:
    """Read one speech utterance from an already-started RawInputStream.

    Returns raw PCM16 bytes for the utterance, or b"" on timeout/stop before speech.
    """
    chunk_duration = blocksize / float(sample_rate)
    silence_chunks_needed = max(1, int(round(pause_threshold / chunk_duration)))
    max_speech_chunks = max(1, int(round(phrase_limit / chunk_duration)))

    preroll: deque[bytes] = deque(maxlen=max(0, preroll_chunks))
    speech_chunks: list[bytes] = []
    started = False
    silent_chunks = 0
    wait_start = time.monotonic()

    while True:
        if should_stop and should_stop():
            return b""

        if not started and listen_timeout is not None:
            if (time.monotonic() - wait_start) >= listen_timeout:
                return b""

        raw_data, _ = stream.read(blocksize)
        chunk = bytes(raw_data)
        rms = pcm16_rms(chunk)

        if not started:
            if rms >= energy_threshold:
                started = True
                speech_chunks.extend(preroll)
                speech_chunks.append(chunk)
                silent_chunks = 0
            else:
                preroll.append(chunk)
            continue

        speech_chunks.append(chunk)
        if rms >= energy_threshold:
            silent_chunks = 0
        else:
            silent_chunks += 1

        if silent_chunks >= silence_chunks_needed or len(speech_chunks) >= max_speech_chunks:
            break

    return b"".join(speech_chunks)
