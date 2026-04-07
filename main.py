from fastapi import FastAPI

from env.environment import ReleaseDeskEnv
from env.models import Action

app = FastAPI(title="OpenEnv Release Desk")

env = ReleaseDeskEnv()


@app.get("/")
def root():
    return {
        "status": "ok",
        "environment": "release_desk",
        "documents": env.max_steps,
    }


@app.post("/reset")
def reset():
    observation = env.reset()
    return {"observation": observation.dict()}


@app.post("/step")
def step(action: Action):
    observation, reward, done, info = env.step(action)
    return {
        "observation": observation.dict() if observation else None,
        "reward": reward.dict(),
        "done": done,
        "info": info,
    }


@app.get("/state")
def state():
    return env.state()
