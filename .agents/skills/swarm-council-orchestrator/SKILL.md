---
name: swarm-council-orchestrator
description: |
  Multi-agent parallel deliberation protocols, Selective Quorum routing,
  and Tree of Thoughts consensus building across the 6 Nachapol AI personas.
license: MIT
metadata:
  version: v1
  author: Nachapol Industries
---

# Multi-Agent Swarm Council Orchestrator Protocol

## Overview
Standards for concurrent multi-agent cognitive deliberation, persona quorum routing, prompt synthesis, and Tree of Thoughts strategic exploration (`jarvis_core/cognitive/swarm.py`).

## Core Directives
1. **Parallel Execution:** Agent deliberations must execute simultaneously using `ThreadPoolExecutor(max_workers=5)` to guarantee quorum completion in <1.5 seconds.
2. **Selective Quorum:** For specialized engineering tasks, summon only relevant personas (e.g., V.E.R.O.N.I.C.A. + D.U.M.-E. for hardware emergency, F.R.I.D.A.Y. + E.D.I.T.H. for code strategy).
3. **Synthesis Authority:** J.A.R.V.I.S. acts as the sole Council President, responsible for synthesizing divergent views into a singular, actionable master directive.
4. **HUD Telemetry:** Broadcast debate status, active agent avatars, and node colors to the desktop Dynamic Island and Hologram Web Portal in real time.
