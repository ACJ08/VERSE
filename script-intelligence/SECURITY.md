# Security Policy & Guidelines

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

---

## Reporting Vulnerabilities

If you discover a potential security issue in **VERSE Continuity Script Intelligence**, please report it responsibly by contacting the maintainer via email: `arslaan@verse.ai`.

Please include:
- A description of the issue.
- Steps to reproduce.
- Proof of concept (if applicable).

Do NOT open public GitHub issues for security vulnerabilities.

---

## Security Features Implemented

1. **Path Traversal Protection:**
   - All uploaded filenames undergo strict sanitization (`sanitize_filename`) removing directory components and dangerous characters.
2. **File Size Limits:**
   - Enforced maximum upload size (`MAX_UPLOAD_SIZE_MB`, default 25MB) to protect against memory exhaustion.
3. **MIME & Extension Validation:**
   - Allowed file types restricted to `.pdf`, `.docx`, and `.txt`.
4. **Stack Trace Suppression:**
   - Production error handlers mask internal python stack traces from HTTP responses.
