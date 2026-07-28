# Changes — Local Ollama setup fixes

Got the local Granite/Ollama integration actually running end-to-end and fixed two real bugs found along the way: `.env` config was never being loaded, and the model was outputting the literal text `"null"` instead of leaving fields empty.

## 1. `.env` file wasn't being loaded at all

**Problem:** The README tells you to create a `.env` file with `GRANITE_BASE_URL` and `GRANITE_MODEL`, but nothing in the code ever actually read that file. The app only looked at real system environment variables, so anything you put in `.env` was silently ignored — the server always fell back to the hardcoded default (`http://localhost:8000/v1`), even with a correctly filled-in `.env`.

**Fix:** Added the standard `python-dotenv` package and load the `.env` file at the very top of `app/main.py`, before anything else runs. Now `.env` works the way the README says it should.

**Where:** `app/main.py`, lines 1-3 (new). Also added `python-dotenv>=1.0.0` to `requirements.txt` (line 12) since it's a new dependency.

## 2. Model sometimes returned the string `"null"` instead of leaving a field blank

**Problem:** When the local model didn't know a value (e.g. a character's costume wasn't mentioned in the scene), it would sometimes write the field as the *text* `"null"` instead of just leaving it out. That looks harmless in the raw JSON, but it silently passes validation and turns into a real bug later — any code checking "does this character have a costume?" would incorrectly say yes, because the text `"null"` counts as a value.

**Fix:** Added one instruction to the AI's system prompt telling it to omit any field it doesn't have an answer for, and explicitly telling it not to write `"null"`, `"None"`, `"N/A"`, or `"unknown"` as placeholder text.

**Where:** `app/granite.py`, line 111 (one new line in the system prompt).

## 3. Local Ollama configuration

**Problem:** Not a code change — just documenting the working local setup for reference.

**What:** `.env` (kept out of git, as it should be) is configured to point at a local Ollama server instead of a cloud API:
```
GRANITE_BASE_URL=http://localhost:11434/v1
GRANITE_MODEL=granite3.1-dense:2b
```
Note this uses port `11434` (Ollama's default), not port `8000` shown in the README's example — and `granite3.1-dense:2b` rather than `granite4.1`, since that's the actual model tag available in Ollama's library.

**Where:** `.env` (not committed — see `.gitignore`).
