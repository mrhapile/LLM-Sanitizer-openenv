from fastapi import FastAPI
from env.environment import VaultSanitizerEnv
from env.models import Action

app = FastAPI()

env = VaultSanitizerEnv()

@app.get("/")
def root():
    return {"status": "Vault Sanitizer running"}

@app.post("/reset")
def reset():
    obs = env.reset()
    return {"observation": obs.dict()}

@app.post("/step")
def step(action: Action):
    obs, reward, done, info = env.step(action)

    return {
        "observation": obs.dict() if obs else None,
        "reward": reward.dict(),
        "done": done,
        "info": info
    }

@app.get("/state")
def state():
    return env.state()
