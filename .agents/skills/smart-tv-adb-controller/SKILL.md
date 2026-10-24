---
name: smart-tv-adb-controller
description: |
  Android TV and Google TV automation over Wi-Fi ADB, bloatware stripping,
  custom Apple TV-style native launcher management, and living-room casting.
license: MIT
metadata:
  version: v1
  author: Nachapol Industries
---

# Smart TV ADB & Living-Room Display Protocol

## Overview
Standards for managing Android TV / Google TV sets over wireless ADB, automated telemetry debloating, custom launcher deployment, and media casting.

## Core Directives
1. **Wireless ADB Handshake:** Maintain persistent ADB connections over TCP/IP port 5555 without requiring physical USB tethering.
2. **Reversible Debloating:** Never execute permanent package uninstalls; always use reversible user-space package disabling (`pm disable-user --user 0`).
3. **Clean UX Launcher:** Provide clean living-room interface templates inspired by Apple TV without ads, analytics, or background bloat.
4. **Display Hand-off:** Seamlessly cast desktop video streams or security camera feeds to the smart TV screen on voice command.
