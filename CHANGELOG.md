# Changelog

All notable changes to this project will be documented in this file.

## 0.1.0 - Unreleased

- Initial read-only Home Assistant integration for DVBViewer Media Server.
- Native config flow, coordinator-based updates and diagnostics.
- Sensors for connectivity, server status, timers, recordings, channels and tuners.
- Optional VideoREC ffprobe verification through `videorec_url`.
- Europe/Rome-aware timer timestamps.
- Conservative future VideoREC contract: bounded verification of recent files,
  strict ffprobe-response validation and no archive-wide probing.
- Treat DMS recording duration as non-authoritative metadata; handle invalid
  values and timers that cross midnight safely.
