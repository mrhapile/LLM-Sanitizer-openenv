# Release Desk OpenEnv

Release Desk is a deterministic OpenEnv environment for a real enterprise workflow: reviewing internal documents before they are released into an LLM training or retrieval pipeline. An agent must decide whether to pass a document through unchanged, redact literal secrets, or rewrite the document into a safe form while preserving business meaning.

The environment is built around three task families:

1. `easy` - direct PII and secret removal from support tickets and email-like updates
2. `medium` - structured repair for malformed JSON and key-value configuration dumps
3. `hard` - contextual de-identification and prompt-injection cleanup for executive and incident memos

## Why this is a real task

Security, compliance, data engineering, and AI platform teams already do this work manually before:

- training internal copilots
- indexing documents into RAG systems
- exporting support and incident data to vendors
- sharing redacted reports across teams

Release Desk turns that workflow into a typed, deterministic evaluation environment for agent training.

## OpenEnv Interface

The app exposes the standard OpenEnv API:

- `POST /reset` -> returns the first `Observation`
- `POST /step` -> accepts an `Action`, returns `(observation, reward, done, info)`
- `GET /state` -> returns current environment state

Typed models live in [env/models.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/env/models.py).

### Observation

- `document_id`
- `task_type`
- `task_name`
- `instruction`
- `content_format`
- `data_chunk`
- `risk_report`
- `attempts_left`
- `documents_remaining`

### Action

- `redact`
- `rewrite`
- `escalate`
- `bypass`

`redact` is for literal replacement, `rewrite` is for structural repair or safe rephrasing, `escalate` spends limited review budget, and `bypass` is only correct for already-safe documents.

### Reward

- `score`
- `progress`
- `leak_free_ratio`
- `utility_ratio`
- `format_ratio`

All reward components are bounded in `[0.0, 1.0]`.

## Task Design

### Easy: Customer Support Cleanup

The agent removes direct emails, phone numbers, and tokens while preserving ticket context. There is also a safe bypass case so the policy does not collapse into "always redact".

### Medium: Structured Config Repair

The agent repairs malformed JSON or key-value config blobs, keeps the original keys, and replaces sensitive values with `[REDACTED]`.

### Hard: Contextual De-identification

The agent must strip executive identity clues, prompt-injection text, secrets, and contact details while keeping the business-safe summary intact.

## Grading

The grader is deterministic and task-aware:

- `leak_free_ratio`: how many forbidden values are fully removed
- `utility_ratio`: how much of the expected safe content is preserved
- `format_ratio`: whether JSON or key-value structure is valid
- `required_phrase_ratio`: whether critical safe context is retained on medium and hard tasks

The final score weights these components differently by difficulty. The runtime grader lives in [grader/grader.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/grader/grader.py).

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

Run the baseline benchmark:

```bash
python inference.py
```

Optional LLM baseline:

```bash
export OPENAI_API_KEY=...
export MODEL_NAME=gpt-4o-mini
python inference.py
```

## Tests

```bash
pytest -q
```

The tests cover:

- model validation
- environment state transitions
- escalation budget enforcement
- deterministic grader behavior
- structured parsing helpers

## Docker

Build and run locally:

```bash
docker build -t release-desk-openenv .
docker run -p 7860:7860 release-desk-openenv
```

## Hugging Face Spaces

This repo is container-ready for a Docker Space. Use the Dockerfile in the repo root, expose port `7860`, and tag the Space with `openenv`.

## Repo Layout

- [main.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/main.py) - FastAPI OpenEnv entrypoint
- [env/environment.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/env/environment.py) - environment state machine
- [env/models.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/env/models.py) - typed OpenEnv models
- [grader/grader.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/grader/grader.py) - deterministic task grader
- [data/tasks.json](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/data/tasks.json) - deterministic task corpus
- [inference.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/inference.py) - reproducible baselines
