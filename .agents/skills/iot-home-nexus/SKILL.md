---
name: iot-home-nexus
description: |
  Smart home device orchestration, Home Assistant REST & WebSocket integration,
  ESP32 microcontroller telemetry, and LAN automation standards.
license: MIT
metadata:
  version: v1
  author: Nachapol Industries
---

# IoT & Smart Home Orchestration Protocol

## Overview
Standards for bidirectional control of smart home ecosystems, Home Assistant entity coordination, ESP32 sensor telemetry, and ambient environment automation.

## Core Directives
1. **Asynchronous Dispatch:** All Home Assistant API calls (`modules/home_assistant.py`) must be executed non-blocking via asyncio or daemon workers to prevent UI stutter.
2. **State Caching:** Cache device states locally in SQLite to allow instantaneous voice responses without waiting for cloud IoT roundtrips.
3. **Safety Fallback:** If smart lock or relay disconnects, enter a safe locked state and alert the owner immediately.
4. **Auto-Discovery:** Automatically inspect mDNS / SSDP packets on the local subnet to detect new smart home appliances.
