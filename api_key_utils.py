import os
from typing import Optional, Tuple


PRIMARY_API_KEY_ENV_VARS = (
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "API_KEY",
)


def get_api_key_env() -> Optional[Tuple[str, str]]:
    for env_name in PRIMARY_API_KEY_ENV_VARS:
        value = os.getenv(env_name, "").strip()
        if value:
            return env_name, value

    for env_name in sorted(os.environ):
        if env_name.endswith("_API_KEY") and env_name not in PRIMARY_API_KEY_ENV_VARS:
            value = os.getenv(env_name, "").strip()
            if value:
                return env_name, value

    return None