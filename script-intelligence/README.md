# VERSE — Continuity Script Intelligence

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/FastAPI-0.139.2-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/LLM-IBM%20Granite%204.1%20%7C%20Ollama-8A2BE2.svg" alt="LLM Engine">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/Ecosystem-VERSE-orange.svg" alt="VERSE Ecosystem">
  <img src="https://img.shields.io/badge/Tests-Passing-brightgreen.svg" alt="Tests">
</p>

> *Every story lives in its own VERSE.*

**Continuity Script Intelligence** is a production-grade, research-ready AI intelligence backend for film screenplay and production document workflows. Part of the **VERSE (Visual & Explainable Reasoning for Semantic Evolution)** ecosystem, this system transforms unstructured filmmaking documents into structured, validated JSON data for automated continuity tracking.

---

## 📌 Executive Summary & Motivation

In professional film production, maintaining continuity across thousands of camera takes and script revisions is a high-stakes challenge. A single oversight — such as a prop changing hands or wardrobe inconsistency between shot setups — results in costly reshoots.

**VERSE Continuity Script Intelligence** automates semantic document breakdown and continuity entity extraction using **local IBM Granite 4.1 / Ollama** inference:

- 📄 **Multimodal Document Processing:** Screenplays (`PDF`, `DOCX`, `TXT`) & Production Call Sheets.
- 🎬 **Granular Scene Splitting:** Detects complex slug lines (`INT.`, `EXT.`, `INT./EXT.`, `I/E.`, scene numbers).
- 🧠 **Local LLM Extraction:** Extracts character wardrobe/movement, prop states, lighting setups, and flags continuity risks.
- 🔒 **Zero Cloud Costs & Total Privacy:** Runs 100% locally via OpenAI-compatible endpoints (Ollama / vLLM).
- ⚡ **High Throughput:** Multi-threaded parallel scene analysis (`ThreadPoolExecutor`).

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Screenplay & Call Sheet Documents                    │
│                        PDF   •   DOCX   •   TXT                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application Gateway                     │
│    Path Traversal Defense  •  MIME Validation  •  Size Limit Guard     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Document Parsing Engine                          │
│     PyMuPDF (PDF)  •  python-docx (DOCX)  •  Table Extractors          │
│                    Text Cleaning & Normalisation                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Scene Splitting Engine                           │
│  Regex Heading Detector (INT., EXT., INT./EXT., I/E., Scene Numbers)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Parallel Local AI Analysis Engine (verse.llm)            │
│                 ThreadPoolExecutor Parallel Worker Pool                │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                Granite / Ollama Client Integration               │  │
│  │  Exponential Backoff Retries  •  Timeouts  •  JSON Repair       │  │
│  └────────────────────────────────┬─────────────────────────────────┘  │
│                                   │                                    │
│  ┌────────────────────────────────▼─────────────────────────────────┐  │
│  │                Pydantic v2 Validation Layer                      │  │
│  │  SceneContinuity • Character • Prop • Lighting • ContinuityNote  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Structured Production JSON Output                    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Project Structure

```text
continuity-script-intelligence/
├── app/
│   ├── api/                     # API routes (/api/v1 endpoints)
│   │   ├── v1/                  # Versioned API routes (health, scripts, scenes, call sheets)
│   │   └── router.py            # APIRouter aggregator
│   ├── core/                    # System core (config, custom errors, logging)
│   │   ├── config.py            # Central settings & env loader
│   │   ├── errors.py            # Domain exception hierarchy
│   │   └── logging.py           # Structured logger & execution timer
│   ├── llm/                     # AI & Inference layer
│   │   ├── granite_client.py    # IBM Granite / Ollama client & JSON parser
│   │   └── retry.py             # Exponential backoff retry logic
│   ├── parsers/                 # Document & text parsing engines
│   │   ├── call_sheet_parser.py # Production call sheet extractor
│   │   ├── document_parser.py   # PDF, DOCX, TXT reader with table support
│   │   └── scene_splitter.py    # Screenplay scene splitter & heading parser
│   ├── prompts/                 # Prompt templates
│   │   └── templates.py         # System prompt & prompt wrappers
│   ├── schemas/                 # Pydantic v2 Data Models
│   │   ├── call_sheet.py        # Call sheet data models
│   │   ├── continuity.py        # Continuity models (Character, Prop, Lighting)
│   │   ├── requests.py          # Request payload envelopes
│   │   └── responses.py         # Response payload envelopes
│   ├── services/                # Business logic separation
│   │   ├── call_sheet_service.py# Call sheet pipeline orchestration
│   │   ├── continuity_service.py# Full script parallel AI analysis service
│   │   └── script_service.py    # Upload & parsing service
│   ├── utils/                   # Utilities & security guards
│   │   ├── file_utils.py        # Filename sanitization & path safety
│   │   └── text_utils.py        # Text cleaning & truncation
│   ├── main.py                  # FastAPI app entrypoint
│   ├── schema.py                # Backwards-compatibility model exports
│   ├── parser.py                # Backwards-compatibility parser exports
│   └── granite.py               # Backwards-compatibility client exports
├── tests/                       # Comprehensive Pytest test suite
│   ├── test_api.py              # Endpoint integration tests
│   ├── test_call_sheet.py       # Call sheet parser tests
│   ├── test_llm.py              # LLM client & retry tests
│   ├── test_parsers.py          # Document reader & scene splitter tests
│   └── test_security.py         # Security defense tests
├── .env.example                 # Environment template
├── pyproject.toml               # Project metadata & tool config
├── requirements.txt             # Python dependencies
├── CHANGELOG.md                 # Release history
├── CONTRIBUTING.md              # Contribution guide
├── LICENSE                      # MIT License
├── SECURITY.md                  # Security policy
└── README.md                    # Research documentation
```

---

## ⚡ Quick Start & Installation

### Prerequisites

- **Python 3.9+**
- Local LLM Runner (e.g. **Ollama** or **vLLM**) serving IBM Granite 4.1

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/ayubarslaan/Continuity-script-intelligence.git
cd continuity-script-intelligence

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch Local Granite / Ollama Inference Server

**Option A: Ollama (Recommended)**
```bash
ollama run granite3.1-dense:2b
```

**Option B: vLLM**
```bash
python -m vllm.entrypoints.openai.api_server --model ibm-granite/granite-4.1
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env`:

```env
GRANITE_BASE_URL=http://localhost:11434/v1
GRANITE_MODEL=granite3.1-dense:2b
LLM_TIMEOUT_SECONDS=60.0
LLM_MAX_RETRIES=3
MAX_PARALLEL_SCENE_ANALYSES=4
```

### 4. Start VERSE Backend

```bash
uvicorn app.main:app --reload
```

Interactive OpenAPI documentation is available at:
`http://127.0.0.1:8000/docs`

---

## 🛠️ API Reference & Usage

### 1. Health Check (`GET /api/v1/health`)

```bash
curl http://127.0.0.1:8000/api/v1/health
```

**Response:**
```json
{
  "status": "ok",
  "version": "2.0.0",
  "granite_configured": true
}
```

---

### 2. Full Script AI Continuity Analysis (`POST /api/v1/analyse-script`)

Upload a screenplay document for parallel AI scene analysis.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyse-script \
  -F "file=@screenplay.pdf"
```

**Response Schema:**
```json
{
  "filename": "screenplay.pdf",
  "scene_count": 2,
  "scenes": [
    {
      "metadata": {
        "scene_id": "SCENE_001",
        "heading": "INT. SARAH'S APARTMENT - KITCHEN - NIGHT",
        "interior_exterior": "INT.",
        "location": "SARAH'S APARTMENT",
        "sub_location": "KITCHEN",
        "time": "NIGHT"
      },
      "characters": [
        {
          "name": "SARAH",
          "costume": "blue jacket",
          "position": "standing at the kitchen counter",
          "movement": "holds coffee mug in right hand",
          "emotional_state": "anxious"
        }
      ],
      "props": [
        {
          "name": "coffee mug",
          "hand_usage": "right",
          "state": "hot",
          "owner": "SARAH"
        }
      ],
      "lighting": {
        "description": "indoor artificial light",
        "source": "overhead light",
        "mood": "tense",
        "time_of_day": "NIGHT"
      },
      "continuity_notes": [
        {
          "note": "Verify coffee mug hand usage between setup shots",
          "severity": "LOW",
          "category": "PROP",
          "affected_characters": ["SARAH"]
        }
      ],
      "confidence_score": 1.0
    }
  ],
  "errors": []
}
```

---

### 3. Single Scene Analysis (`POST /api/v1/analyse-scene`)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyse-scene \
  -H "Content-Type: application/json" \
  -d '{
    "scene_text": "INT. OFFICE - DAY\nJohn picks up the phone with his left hand.",
    "scene_id": "SCENE_005"
  }'
```

---

### 4. Production Call Sheet Parsing (`POST /api/v1/parse-call-sheet`)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/parse-call-sheet \
  -F "file=@call_sheet.pdf"
```

---

## 🧪 Testing & Quality Assurance

Run the automated Pytest suite:

```bash
pytest
```

To run tests with coverage reporting:

```bash
pytest --cov=app --cov-report=term-missing
```

---

## 🛡️ Security & Hardening

- **Path Traversal Defense:** Filenames sanitized using regex sanitization (`sanitize_filename`).
- **File Size Guard:** Configurable limit (`MAX_UPLOAD_SIZE_MB`, default 25MB).
- **MIME Allowed Types:** Strictly checked against allowed extensions (`.pdf`, `.docx`, `.txt`).
- **Exception Sanitization:** Production errors suppress raw python tracebacks.

---

## 🗺️ Roadmap

- [x] Production Modular Architecture (`app/core`, `app/services`, `app/llm`)
- [x] Exponential Backoff Retries & Timeout Guards
- [x] Parallel Scene Execution (`ThreadPoolExecutor`)
- [x] Automated Pytest Test Suite
- [ ] SQLite / PostgreSQL Persistence for Cross-Scene Diffing
- [ ] Multimodal Vision Integration (Frame vs Script Verification)
- [ ] Real-time Scene Analysis Streaming Websocket Endpoint

---

## 📄 License & Citation

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

Part of the **VERSE** ecosystem (Visual & Explainable Reasoning for Semantic Evolution).

**Author:** Mohd Arslaan Ayub  
*Script Intelligence Engineer*
