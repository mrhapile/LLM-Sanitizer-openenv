# 🛡️ Vault Sanitizer: AI Training Data Auditor

> An OpenEnv-compliant environment designed to evaluate AI agents acting as Data Compliance Engineers.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-green)
![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-orange)

## 📌 Project Context

As large language models consume vast amounts of data, the risk of inadvertently memorizing and leaking sensitive information (PII, API keys, corporate secrets) is a critical AI safety challenge.

**Vault Sanitizer** simulates a messy, real-world data preparation pipeline. It provides an OpenEnv interface where an AI agent acts as a **Data Compliance Engineer**. The environment rigorously evaluates whether an autonomous agent can:
- **Detect and selectively remove** sensitive data.
- **Preserve useful information** (penalizing over-redaction).
- **Navigate messy, real-world text** (emails, logs, noise, signatures).

---

## 🏆 Project Value

1. **Solves a Real-World AI Safety Problem:** Sanitizing petabytes of pre-training data is currently a highly manual or hard-coded heuristic process. Automating this reliably with AI agents is a frontier problem.
2. **Beyond Simple Data Cleaning:** Unlike basic regex that fails on edge cases or context-dependent secrets (e.g., distinguishing a CTO's name linked to credentials vs. a generic name), Vault Sanitizer tests contextual understanding.
3. **Evaluating Agentic Capabilities:** It provides a deterministic, highly structured scoring system measuring True Positives, False Positives (over-redaction), and False Negatives (leaks), making it a perfect benchmark for LLM agent performance.

---

## 🎯 Hackathon Requirements

This project adheres strictly to the OpenEnv specification:
- Exposes standard OpenEnv API endpoints: `/step`, `/reset`, and state management.
- Utilizes `Pydantic` models for Observations, Actions, and Rewards.
- Features **3 progressive levels of difficulty** (easy, medium, hard).
- Employs deterministic graders returning normalized `[0.0 - 1.0]` scores.
- Includes baseline inference scripts for agent evaluation.
- Fully deployable via Docker and optimized for Hugging Face Spaces.

---

## ✅ Current Status

- [x] **Phase 0 — Repo Setup:** Clean GitHub repo and proper folder structure initialized.
- [x] **Phase 1 — Foundation:** FastAPI server running, `/reset` & `/step` endpoints implemented, Docker wrapper complete (port 7860), spaCy pre-installed.
- [x] **Phase 2 — Data Engineering:** `build_dataset.py` implemented. A highly realistic, deterministic dataset containing 15 noisy email samples has been generated successfully along with a gold-truth manifest. Tested and verified for sensitive data matching.
- [x] **Phase 3 — Core Environment (OpenEnv Engine):** `env/environment.py` and `env/models.py` created to strictly adhere to OpenEnv specifications using Pydantic validation. The simulated dataset is officially connected to the environment state engine, successfully managing tracking attributes (`current_chunk_index`, `utility_budget`, `steps_taken`), maintaining episode termination (`done`) logic bounds, and accurately connecting OpenEnv action structures (`action_type: redact, delete, bypass`) to FastAPI.

---

## 🚧 Remaining Work (Contribution Guide)

For developers looking to continue the build, here are the sequential phases remaining:

### Phase 4 — Grader System
- **Implement** `grader/grader.py`.
- **Load** `gold_manifest.json` as the ground truth.
- **Compute metrics:** True Positives (TP), False Negatives (FN), False Positives (FP).
- **Implement scoring formula:** `R = (TP * 1.0) - (FN * 2.0) - (FP * 0.5)`
- **Normalize** final score to a `[0,1]` scale.
- **Implement entity-relation matching** to evaluate hard tasks.

### Phase 5 — Baseline Agents
- **Implement** `inference.py` to test the environment.
- **Create internal baseline agents:**
  - `RandomAgent`
  - `RegexAgent`
  - `LLM Agent` (OpenAI client)
- **Run evaluations** on all tasks and generate a baseline score performance table.

### Phase 6 — Testing & Validation
- **Add** unit tests within `tests/`.
- **Validate core environment loop:**
  - `reset()` returns the correct initial Observation.
  - `step()` processes actions and returns valid outputs.
  - Reward range stays logically bounded.
- **Run** `openenv validate`.

### Phase 7 — Documentation & Finalization
- **Finalize** this README with actual baseline results.
- **Add details** regarding the final architecture, action/observation spaces, and explicit task descriptions.
- **Publish** the Hugging Face Space link.

---

## 🧱 Tech Stack

- **Python 3.10**
- **FastAPI** (Web server)
- **Pydantic v2** (Data validation & typing)
- **spaCy (`en_core_web_sm`)** (NLP processing)
- **Pandas** (Data manipulation)
- **OpenAI API** (Baseline agent inference)
- **Docker** (Environment containerization)

---

## 📂 Project Structure

```text
vault-sanitizer/
│
├── env/                   # OpenEnv logic (State, Actions, Step)
├── data/                  # Dataset generator, JSONL, and Gold Truth
│   ├── build_dataset.py
│   ├── dataset.jsonl
│   └── gold_manifest.json
├── grader/                # Deterministic scoring logic
├── tests/                 # Unit and validation tests
│
├── main.py                # FastAPI server and OpenEnv endpoints
├── openenv.yaml           # OpenEnv specification metadata
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container configuration (HF Spaces Ready)
├── inference.py           # Evaluation script for Baseline agents
├── README.md              # Project documentation
├── .env                   # Environment variables (Ignored in git)
└── .gitignore             # Git ignore file
```

---

## 🚀 Setup Instructions

### 1. Local Virtual Environment
```bash
# Create and activate virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### 2. Running Locally
Start the FastAPI environment server:
```bash
uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```
The server will be available at `http://localhost:7860`.

### 3. Docker Deployment
Requirements for Hugging Face Spaces:
```bash
# Build the image
docker build -t vault-sanitizer .

# Run the container (binds to port 7860)
docker run -p 7860:7860 vault-sanitizer
```

---

## 🧪 API Usage

The environment exposes two primary API endpoints simulating the OpenEnv standard interactively:

### `POST /reset`
Initializes a new episode and returns the first observation.
**Response:**
```json
{
  "observation": {
    "data_chunk": "Sample text with email test@gmail.com",
    "risk_report": ["Possible email detected"],
    "attempts_left": 3
  }
}
```

### `POST /step`
Advances the environment by taking an action (e.g., redacting text).
**Request Body:**
```json
{
  "action_type": "redact",
  "content": "test@gmail.com"
}
```
**Response:**
```json
{
  "observation": {
    "data_chunk": "Updated sample",
    "risk_report": [],
    "attempts_left": 2
  },
  "reward": {
    "score": 0.5
  },
  "done": false,
  "info": {}
}
```
