# Contributing to VERSE Continuity Script Intelligence

Thank you for your interest in contributing to **Continuity Script Intelligence**, a core component of the **VERSE** ecosystem.

## Code of Conduct

We expect all contributors to adhere to a high standard of professional communication, respectfulness, and constructive collaboration.

---

## Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/ayubarslaan/Continuity-script-intelligence.git
   cd continuity-script-intelligence
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. **Install development dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the test suite:**
   ```bash
   pytest
   ```

---

## Contribution Guidelines

1. **Architecture & Modular Design:**
   - Keep business logic in `app/services/` decoupled from API handlers in `app/api/`.
   - Maintain Pydantic v2 schemas in `app/schemas/`.
   - Preserve backwards compatibility for exported top-level module surfaces (`app/main.py`, `app/api.py`, `app/granite.py`, `app/parser.py`).

2. **Testing:**
   - Add unit/integration tests in `tests/` for any new parser feature, endpoint, or LLM utility.
   - Maintain high test coverage (`pytest --cov=app`).

3. **Code Quality:**
   - Follow PEP 8 style guidelines.
   - Add comprehensive docstrings and type annotations.

---

## Submitting Pull Requests

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Commit changes with clear, descriptive commit messages.
3. Push to your branch and open a Pull Request against `main`.
