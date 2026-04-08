from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from env.environment import ReleaseDeskEnv
from env.models import Action, ResetRequest
from demo_service import DemoCompareRequest, DemoService, DemoRunRequest

app = FastAPI(title="OpenEnv Release Desk")

env = ReleaseDeskEnv()
demo_service = DemoService()
STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    return {
        "status": "ok",
        "environment": "release_desk",
        "documents": env.max_steps,
        "tasks": [task["task_name"] for task in env.available_tasks()],
        "actions": ["redact", "rewrite", "escalate", "bypass"],
    }


@app.get("/demo")
def demo_page():
    return FileResponse(STATIC_DIR / "demo.html")


@app.get("/judge")
def judge_page():
    return FileResponse(STATIC_DIR / "landing.html")


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "documents": env.max_steps,
    }


@app.post("/reset")
def reset(request: ResetRequest | None = None):
    try:
        observation = env.reset(request.task_name if request else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"observation": observation.model_dump()}


@app.post("/step")
def step(action: Action):
    observation, reward, done, info = env.step(action)
    return {
        "observation": observation.model_dump() if observation else None,
        "reward": reward.model_dump(),
        "done": done,
        "info": info,
    }


@app.get("/state")
def state():
    return env.state()


@app.get("/tasks")
def tasks():
    return {"tasks": env.available_tasks()}


@app.get("/demo/samples")
def demo_samples():
    return {"samples": demo_service.list_samples()}


@app.get("/demo/featured")
def demo_featured():
    return {"samples": demo_service.featured_samples()}


@app.get("/demo/leaderboard")
def demo_leaderboard():
    return {"leaderboard": demo_service.leaderboard()}


@app.get("/demo/report")
def demo_report():
    report_path = Path(__file__).resolve().parent / "release_desk_demo.html"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not generated yet")
    return FileResponse(report_path)


@app.post("/demo/run")
def demo_run(request: DemoRunRequest):
    return demo_service.run(request).model_dump()


@app.post("/demo/compare")
def demo_compare(request: DemoCompareRequest):
    return demo_service.compare(request).model_dump()
