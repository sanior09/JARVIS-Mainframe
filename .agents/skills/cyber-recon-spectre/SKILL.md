---
name: cyber-recon-spectre
description: |
  Ethical penetration testing, Wi-Fi airwave analysis, network port mapping,
  vulnerability scanning, and autonomous switching to Local Uncensored Dark Mode.
license: MIT
metadata:
  version: v1
  author: Nachapol Industries
---

# Cyber Recon & Defensive Security Protocol

## Overview
Standards and guardrails for automated security assessments, passive LAN port scanning, Wi-Fi packet analysis, and ethical vulnerability detection.

## Core Directives
1. **Ethical Bounds:** Actions must strictly adhere to authorized network testing and defensive analysis.
2. **Uncensored Dark Mode Routing:** Automatically trigger `is_offensive_cyber` heuristics in `jarvis_core/ai_router.py` to route to local uncensored models (`dolphin-llama3` / `qwen-uncensored`), ensuring complete privacy without cloud censorship.
3. **LAN Protection:** Passive scanning only by default (`modules/cyber_inspector.py`); aggressive probing requires explicit confirmation from the owner.
4. **Traffic Encryption:** Verify all remote webhooks and tunnel endpoints utilize TLS 1.3 encryption.
