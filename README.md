# Release Desk OpenEnv

Release Desk is a deterministic OpenEnv environment for a real enterprise workflow: reviewing internal documents before they are released into an LLM training or retrieval pipeline. An agent must decide whether to pass a document through unchanged, redact literal secrets, rewrite a document into a safe form, or escalate for human review.

The environment now covers phases 1 through 8:

1. Full typed OpenEnv contract
2. Real-world task simulation across multiple document formats
3. Stronger task and grader system with easy, medium, and hard tracks
4. Shaped rewards with partial progress signals
5. Reproducible baseline runner with local and OpenAI-backed agents
6. Adversarial hardening for prompt injection, obfuscated secrets, and contextual identity leakage
7. Judge-facing visual demo report
8. Deployment and packaging hardening for Docker and Hugging Face Spaces

## Real-world task

Security, compliance, and AI platform teams already do this work before:

- training internal copilots
- indexing documents into RAG systems
- exporting support and incident data to vendors
- sharing redacted reports across teams

Release Desk turns that workflow into a deterministic environment for agent evaluation and learning.

## OpenEnv API

The FastAPI service exposes the standard interface:

- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /healthz`

Typed models live in [env/models.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/env/models.py).

### Observation fields

- `document_id`
- `task_type`
- `task_name`
- `instruction`
- `policy_mode`
- `content_format`
- `data_chunk`
- `risk_report`
- `adversarial_signals`
- `preferred_action`
- `attempts_left`
- `documents_remaining`
- `cumulative_score`

### Actions

- `redact`
- `rewrite`
- `escalate`
- `bypass`

### Reward fields

- `score`
- `progress`
- `leak_free_ratio`
- `utility_ratio`
- `format_ratio`
- `policy_ratio`
- `action_ratio`
- `adversarial_ratio`

All reward components are bounded in `[0.0, 1.0]`.

## Task tracks

The deterministic corpus in [data/tasks.json](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/data/tasks.json) currently contains nine documents:

- `easy`: direct support-ticket and vendor-email cleanup, plus a true-safe bypass case
- `medium`: malformed JSON repair, key-value config cleanup, and obfuscated secret removal
- `hard`: contextual de-identification, prompt-injection cleanup, and cross-system escalation memos

Each task declares:

- a policy mode such as `training_safe`, `external_sharing`, or `legal_hold`
- a preferred action
- literal or compact-match forbidden targets
- required safe phrases
- policy checks
- adversarial checks

## Grading and reward shaping

The grader in [grader/grader.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/grader/grader.py) combines:

- `leak_free_ratio`: removal of sensitive targets
- `utility_ratio`: overlap with the expected safe output
- `format_ratio`: JSON or key-value validity when structure matters
- `policy_ratio`: compliance with inclusion and exclusion rules
- `action_ratio`: whether the chosen action matches the task
- `adversarial_ratio`: whether prompt injections and obfuscated secrets were actually neutralized

Difficulty tiers weight these components differently so hard tasks emphasize policy and adversarial resilience more than easy tasks.

## Baselines

The benchmark runner in [inference.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/inference.py) provides:

- `RandomAgent`
- `RulesAgent`
- `LLMAgent` via the OpenAI API

The runner prints deterministic per-tier scores and failure counts. If the OpenAI API call fails because of quota or provider issues, the benchmark still completes and reports the local baselines.

Sample local benchmark result:

```text
RandomAgent: overall=0.225 easy=0.411 medium=0.000 hard=0.263
RulesAgent: overall=0.971 easy=1.000 medium=0.916 hard=0.998
```

## How To Run

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the OpenEnv API

```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

### 3. Check that it is healthy

```bash
curl http://localhost:7860/
curl http://localhost:7860/healthz
curl -X POST http://localhost:7860/reset
curl http://localhost:7860/state
```

### 4. Run the baseline benchmark

```bash
python inference.py
```

Optional benchmark export:

```bash
BENCHMARK_OUTPUT_JSON=benchmark.json python inference.py
```

### 5. Run the demo report

```bash
python demo.py
```

This generates `release_desk_demo.html` with:

- before vs after panels for easy, medium, and hard tasks
- RandomAgent versus RulesAgent comparisons
- per-case reward metrics
- risk, adversarial, and failure breakdowns

### 6. Run everything in one command

```bash
python scripts/run_release_checks.py
```

This command:

- runs `pytest`
- compiles the demo and API modules
- starts a local `uvicorn` server
- runs the benchmark and writes `benchmark.json`
- generates `release_desk_demo.html`

## Optional OpenAI baseline

```bash
export OPENAI_API_KEY=...
export MODEL_NAME=gpt-4o-mini
python inference.py
```

If the OpenAI API returns quota or provider errors, the run will skip the LLM baseline and keep the local benchmark results.

## Demo UX

Run the visual report generator:

```bash
python demo.py
```

It produces `release_desk_demo.html` with:

- before vs after panels for easy, medium, and hard tasks
- RandomAgent versus RulesAgent comparisons
- per-case reward metrics
- risk, adversarial, and failure breakdowns

## Tests

```bash
pytest -q
```

Current verification in this repo:

- unit tests for environment state, graders, normalization, and API metadata
- in-process FastAPI smoke tests
- live HTTP benchmark smoke test against `uvicorn`

## Docker

```bash
docker build -t release-desk-openenv .
docker run -p 7860:7860 release-desk-openenv
curl http://localhost:7860/healthz
```

The container:

- runs as a non-root user
- exposes a `/healthz` endpoint
- includes a Docker health check suitable for HF Spaces

## Hugging Face Spaces

This repo is container-ready for a Docker Space. Use the Dockerfile in the repo root, expose port `7860`, and tag the Space with `openenv`.

Recommended HF configuration:

- Space SDK: `Docker`
- App port: `7860`
- Health route: `/healthz`
- Space tags: `openenv`, `ai-safety`, `enterprise-data`

## Repo layout

- [main.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/main.py) - FastAPI entrypoint
- [env/environment.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/env/environment.py) - OpenEnv state machine
- [env/models.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/env/models.py) - typed models
- [grader/grader.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/grader/grader.py) - deterministic grading and reward shaping
- [grader/normalization.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/grader/normalization.py) - normalization and compact matching
- [data/tasks.json](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/data/tasks.json) - deterministic task corpus
- [inference.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/inference.py) - baseline runner
- [demo.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/demo.py) - judge-facing HTML report
- [scripts/run_release_checks.py](/Users/mrhapile/Hackathon/LLM-Sanitizer-openenv/scripts/run_release_checks.py) - one-command smoke runner
