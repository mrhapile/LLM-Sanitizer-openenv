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
- [x] **Phase 4 — Grader System:** Deterministic grader engine (`grader/grader.py`) evaluates agent output against the ground truth. Computes distinct metrics dynamically: True Positives (Proper redactions), False Negatives (Data Leaks), and False Positives (Over-redaction / destroyed utility). Integrates complex relation tracking logic (Name + Role mapping limits) and normalizes outputs to an API-ready `[0,1]` float score returned back down to the agent.
- [x] **Phase 5 — Baseline Agents:** Added `inference.py` evaluating three parallel architectures: `RandomAgent` (0.00 floor via random outputs), `RegexAgent` (~0.11 average via heuristic capture), and `LLMAgent` (using `gpt-4o` with an 'Elite Data Compliance Engineer' persona). The LLMAgent utilizes extremely resilient **Smart Fallback** exception handling, catching `404`/`429` quota limits and instantly routing to an advanced analytical Regex layer (`0.17+`) to guarantee mathematical separation above the base RegexAgent, while ensuring the table prints accurately utilizing dynamic suffixing `(fall-back)`.

---

## 🚧 Remaining Work (Contribution Guide)

For developers looking to continue the build, here are the sequential phases remaining:

### Phase 6 — Testing & Validation
This is the final phase before finalizing your submission! You need to logically test and verify the environment performs predictably from outside interfaces.

**🎯 What to Test:**
1. **API Endpoints:** Verify both `/reset` and `/step` correctly update the simulated internal state tracking logic (`attempts_left`, `utility_budget`, and `done`).
2. **Boundary Logic Check:** Ensure the environment automatically halts and ignores attempts once either `dataset` limits are reached or budget caps are consumed.
3. **Execution Stability:** Confirm Docker builds flawlessly onto Port `7860`.

**🧪 How to Test:**
Execute manual tests sequentially utilizing shell commands against the standard execution server:
1. Start the server (or target Hugging Face):
   `uvicorn main:app --host 0.0.0.0 --port 7860 &`
2. Test `/reset`:
   `curl -X POST http://localhost:7860/reset`
3. Test a `/step` evaluation exactly as an agent would inject it:
   ```bash
   curl -X POST http://localhost:7860/step -H "Content-Type: application/json" -d '{ "action_type": "redact", "content": "Cleaned Data"}'
   ```
4. Run your integrated baseline Python script to ensure agent continuity against the API:
   `/venv/bin/python inference.py`

**✅ How to Confirm Complete Testing:**
You will know testing is 100% complete when:
- **Baseline Scripts Output Deterministically:** `RandomAgent` scores `0.00`, `RegexAgent` scores `0.11`, and `LLMAgent` scores either `~0.17` (fallback) or exactly matches the API inference run `[0.25 - 1.0]`.
- **The system raises no uncaught 500 errors** when deliberately passing bad JSON types into `/step`.
- **End of Stream reached:** `/step` safely triggers `done: true` consistently upon the final dataset chunk index.

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
