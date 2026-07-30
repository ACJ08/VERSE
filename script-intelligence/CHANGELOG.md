# Changelog

All notable changes to **VERSE Continuity Script Intelligence** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-07-28

### Added
- Modular package layout (`app/core`, `app/api`, `app/services`, `app/parsers`, `app/llm`, `app/prompts`, `app/schemas`, `app/utils`).
- Complete Pytest test suite covering parsers, call sheets, security defenses, LLM retry mechanisms, and API endpoints.
- Path traversal defense (`sanitize_filename`), configurable file size limits (`MAX_UPLOAD_SIZE_MB`), and MIME type validation.
- Exponential backoff retry logic (`retry_with_backoff`) and configurable request timeouts for local Granite / Ollama inference.
- Parallel thread-pool execution (`ThreadPoolExecutor`) for full screenplay scene analysis.
- Structured logging system (`setup_logging`, `timed_execution`) with sensitive content masking.
- JSON repair fallback parser for LLM code fences and trailing comma syntax errors.
- Open source governance files: `LICENSE` (MIT), `CONTRIBUTING.md`, `SECURITY.md`, `pyproject.toml`.

### Changed
- Refactored `app/main.py` and `app/api.py` to use service layer separation.
- Enhanced scene heading detection to support `INT.`, `EXT.`, `INT./EXT.`, `I/E.`, `INT/EXT.`, `EXT/INT`, `EST.`, and scene numbers.
- Improved call sheet parsing regex rules for cast, crew, schedule, and time extraction.

### Preserved
- 100% backwards compatibility for legacy endpoints (`/upload-script`, `/parse-script`, `/parse-call-sheet`) and top-level module imports.
