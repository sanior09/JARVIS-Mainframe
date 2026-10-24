---
name: neural-audio-dsp
description: |
  Ultra-low latency speech processing, Voice Activity Detection (VAD) barge-in,
  Microsoft Edge Neural TTS, and WebSocket streaming STT protocols.
license: MIT
metadata:
  version: v1
  author: Nachapol Industries
---

# Neural Audio DSP & Real-Time Barge-In Protocol

## Overview
Standards for acoustic voice processing, speech-to-text streaming, neural text-to-speech rendering, and instantaneous user interruption handling.

## Core Directives
1. **Zero-Stutter Barge-In:** When the user begins speaking while J.A.R.V.I.S. is speaking, trigger an immediate stop signal to the audio playback buffer within 50ms (`modules/jarvis_vad_bargein.py`).
2. **Dual-Channel Processing:** Maintain independent microphone capture and audio output streams to eliminate acoustic echo feedback.
3. **Smart Silence Awareness:** Suppress proactive voice announcements if media playback (YouTube, Netflix, Spotify) is detected on the active audio endpoint.
4. **Resilient TTS Fallback:** If Microsoft Edge TTS loses internet connectivity, instantly switch to local Windows SAPI5 or offline piper TTS.
