# Validation Guide

## API Smoke Test

```bash
uvicorn main:app --host 0.0.0.0 --port 7860
curl -X POST http://localhost:7860/reset
curl -X POST http://localhost:7860/step -H "Content-Type: application/json" -d '{"action_type":"bypass","content":"Operations update\nThe billing queue returned to normal latency after the deploy.\nNext review: Wednesday at 14:00.\nOwner: Billing Ops","notes":"safe"}'
curl http://localhost:7860/state
```

## Unit Tests

```bash
pytest -q
```

## Baseline Runner

```bash
python inference.py
```

## Docker

```bash
docker build -t release-desk-openenv .
docker run -p 7860:7860 release-desk-openenv
```
