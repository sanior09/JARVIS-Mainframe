---
name: autonomous-self-healer
description: |
  Autonomous exception diagnosis, AST syntax tree analysis, hot-patching,
  and self-repair protocols for runtime resilience without restarting J.A.R.V.I.S.
license: MIT
metadata:
  version: v1
  author: Nachapol Industries
---

# Autonomous Self-Healer & Runtime Patch Protocol

## Overview
Standards and implementation patterns for automated stack trace analysis, AST validation, hot-reload monkey patching, and automated rollback across J.A.R.V.I.S. core subsystems.

## Core Directives
1. **Zero Downtime:** Runtime self-healing must prioritize in-memory fallback without tearing down active daemon threads.
2. **AST Verification:** Any code patches must pass AST parsing (`ast.parse`) and lint checks before hot-reloading (`modules/jarvis_self_patch.py`).
3. **Rollback Journaling:** Always maintain an uncorrupted snapshot of modified modules in `.patch_backup/` to allow single-cycle reversion.
4. **Error Telemetry:** Log all healed exceptions with contextual hardware telemetry and notify the user via HUD toast notifications.
