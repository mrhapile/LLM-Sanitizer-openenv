import os
import random
import re
import json
import time
import sys
from collections import deque
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- HTML REPORTING DASHBOARD ---

def generate_html_report(original_text, sanitized_text, agent_name, score):
    # Style the redaction badge safely strictly within Python f-string bounds
    styled_sanitized = sanitized_text.replace('[REDACTED]', '<span class="redacted-badge">[REDACTED]</span>') if sanitized_text else sanitized_text
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vault Sanitizer Audit - {agent_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f7f6;
            color: #333;
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.06);
            padding: 30px;
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 5px;
            color: #1a1a1a;
        }}
        .meta {{
            font-size: 14px;
            color: #666;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eaeaea;
        }}
        .score-badge {{
            display: inline-block;
            background: #000;
            color: #fff;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 600;
            margin-left: 10px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .panel {{
            background: #fafafa;
            border: 1px solid #ebebeb;
            border-radius: 8px;
            padding: 20px;
        }}
        .panel h2 {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-top: 0;
            margin-bottom: 15px;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 13px;
            line-height: 1.6;
            margin: 0;
        }}
        .redacted-badge {{
            background-color: #e6f7ed;
            color: #1e7e4a;
            border: 1px dashed #1e7e4a;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
            display: inline-block;
            margin: 0 2px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Visual Audit Trail <span class="score-badge">Score: {score:.2f}</span></h1>
        <div class="meta">Agent Context: <strong>{agent_name}</strong></div>
        
        <div class="grid">
            <div class="panel">
                <h2>Raw Training Data</h2>
                <pre>{original_text}</pre>
            </div>
            <div class="panel">
                <h2>Sanitized Output</h2>
                <pre>{styled_sanitized}</pre>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    filename = f"audit_report_{agent_name}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  [+] Generated {filename}")



SYSTEM_PROMPT = (
    "You are a Data Compliance Engineer sanitizing text for Enterprise LLM training.\n"
    "\n"
    "You MUST find and replace ALL of the following sensitive items with [REDACTED]:\n"
    "1. Email addresses (e.g. john@gmail.com)\n"
    "2. Phone numbers (e.g. 9876543210)\n"
    "3. API keys (e.g. sk-1234567890abcd)\n"
    "4. Person names AND their associated corporate roles (e.g. \"Akash\" and \"CFO\" must BOTH be redacted)\n"
    "\n"
    "You have 3 available actions:\n"
    "- \"redact\": Replace sensitive items with [REDACTED] while keeping all other text intact. "
    "This is your PRIMARY action. Use it whenever the text contains any sensitive data.\n"
    "- \"bypass\": Pass the text through unchanged. Use ONLY when the text contains zero sensitive items.\n"
    "- \"delete\": Wipe the entire chunk. Use ONLY as a last resort when the text is so densely packed "
    "with sensitive data that surgical redaction is impossible. WARNING: heavy utility penalty.\n"
    "\n"
    "CRITICAL RULES:\n"
    "- Replace each sensitive item with exactly [REDACTED]\n"
    "- Do NOT remove, rearrange, or rephrase any non-sensitive words\n"
    "- Keep all formatting, punctuation, and whitespace exactly as-is\n"
    "- If a person's name appears, their role MUST also be redacted, and vice versa\n"
    "- Prefer \"redact\" over \"delete\" — surgical precision scores higher than blanket removal\n"
    "\n"
    "RESPONSE FORMAT (strict JSON, no markdown):\n"
    "{\"reasoning\": \"<1 sentence>\", \"action_type\": \"redact\", \"content\": \"<the text with [REDACTED] replacements>\"}"
)

# --- AGENT DEFINITIONS ---

class RequestRateLimiter:
    def __init__(self, max_requests, window_seconds, max_total_requests=None):
        self.max_requests = max(1, int(max_requests))
        self.window_seconds = max(1, int(window_seconds))
        self.max_total_requests = int(max_total_requests) if max_total_requests is not None else None
        self.request_timestamps = deque()
        self.total_requests = 0

    def acquire(self):
        if self.max_total_requests is not None and self.total_requests >= self.max_total_requests:
            return False

        now = time.time()
        while self.request_timestamps and (now - self.request_timestamps[0]) >= self.window_seconds:
            self.request_timestamps.popleft()

        if len(self.request_timestamps) >= self.max_requests:
            wait_for = self.window_seconds - (now - self.request_timestamps[0])
            if wait_for > 0:
                print(f"  [i] Rate limiter active. Sleeping {wait_for:.1f}s to respect provider quota...")
                time.sleep(wait_for)

            now = time.time()
            while self.request_timestamps and (now - self.request_timestamps[0]) >= self.window_seconds:
                self.request_timestamps.popleft()

        self.request_timestamps.append(time.time())
        self.total_requests += 1
        return True

def random_agent_logic(obs):
    """Establishes the absolute floor."""
    return {
        "action_type": random.choice(["redact", "delete", "bypass"]),
        "content": "random_replacement"
    }

def regex_agent_logic(obs):
    """Solves Easy tasks, fails Hard tasks."""
    text = obs["data_chunk"]
    
    # Replaces emails and standard 'sk-' keys to prevent full string over-redaction
    new_text = re.sub(r'[\w\.-]+@[\w\.-]+', '[REDACTED]', text)
    new_text = re.sub(r'sk-[a-zA-Z0-9]{16,}', '[REDACTED]', new_text) 
    new_text = re.sub(r'\b\d{10}\b', '[REDACTED]', new_text) # Phone numbers
    
    if new_text != text:
        return {"action_type": "redact", "content": new_text} 
        
    return {"action_type": "bypass", "content": text}

def enhanced_agent_logic(obs):
    """Slightly smarter than regex: catches names+roles."""
    text = obs["data_chunk"]

    # Step 1: regex cleaning
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '[REDACTED]', text)
    text = re.sub(r'sk-[a-zA-Z0-9]{16,}', '[REDACTED]', text)
    text = re.sub(r'\b\d{10}\b', '[REDACTED]', text)

    # Step 2: simple context reasoning
    text = re.sub(r'\b[A-Z][a-z]+, the (CFO|CEO|CTO|Manager)\b', '[REDACTED]', text)
    text = re.sub(r'\b[A-Z][a-z]+ \((CFO|CEO|CTO|Manager)\)\b', '[REDACTED]', text)

    return {"action_type": "redact", "content": text}


def is_api_failure(error, error_response=None):
    """Classify whether error is a true API failure (fallback-worthy) vs other issue."""
    error_str = str(error).lower()
    
    network_keywords = ["connectionerror", "timeout", "bad gateway", "gateway timeout", "unable to connect"]
    quota_keywords = ["429", "quota", "rate limit", "resource_exhausted"]
    auth_keywords = ["401", "403", "unauthorized", "forbidden", "invalid_api_key", "invalid api key"]
    
    if any(kw in error_str for kw in network_keywords):
        return True
    if any(kw in error_str for kw in quota_keywords):
        return True
    if any(kw in error_str for kw in auth_keywords):
        return True

    if error_response:
        code = getattr(error_response, "status_code", None)
        if code in [429, 503, 502, 504]:
            return True
        if code in [401, 403]:
            return True

    return False


def parse_json_forgiving(content):
    """Try to extract and parse JSON from LLM response, with multiple recovery strategies."""
    if content is None:
        raise ValueError("Empty content")

    if isinstance(content, dict):
        return content

    text = str(content).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    if text.startswith("```"):
        text = re.sub(r"^```(?:json|JSON)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{.*\}$", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response: {content[:100]}")

def llm_agent_logic(obs, client, model_name, rate_limiter=None):
    """The Frontier Agent."""
    user_msg = f"Data Chunk: {obs['data_chunk']}\nRisk Report: {obs['risk_report']}"
    fallback_reason = None
    
    try:
        if rate_limiter and not rate_limiter.acquire():
            fallback_reason = "QUOTA_LIMIT"
            print(f"  [*] FALLBACK[{fallback_reason}] LLM budget exhausted")
            action = enhanced_agent_logic(obs)
            action["is_fallback"] = True
            return action

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            response_format={"type": "json_object"}
        )

        content = None
        if hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content
        else:
            content = response

        result = parse_json_forgiving(content)
        
        # Map any non-standard actions to valid environment actions
        action_type = result.get("action_type", "bypass")
        if action_type not in ["redact", "delete", "bypass"]:
            print(f"  [i] INFO: LLM returned non-standard action '{action_type}', converting to 'redact'")
            action_type = "redact"

        content = result.get("content", obs['data_chunk'])
        if not isinstance(content, str) or not content.strip():
            print(f"  [i] INFO: LLM returned empty/invalid content, using original")
            content = obs['data_chunk']

        return {"action_type": action_type, "content": content}
    except Exception as e:
        error_response = getattr(e, 'response', None)

        if is_api_failure(e, error_response):
            fallback_reason = "API_FAILURE"
            print(f"  [*] FALLBACK[{fallback_reason}] {type(e).__name__}: {str(e)[:80]}")
            action = enhanced_agent_logic(obs)
            action["is_fallback"] = True
            action["fallback_reason"] = fallback_reason
            return action
        else:
            fallback_reason = "MODEL_OUTPUT_ERROR"
            print(f"  [!] WARN[{fallback_reason}] LLM response malformed: {str(e)[:80]}")
            raise

# --- EVALUATION LOOP ---

def evaluate_agent(agent_name, agent_func, base_url="http://localhost:7860"):
    print(f"\nEvaluating: {agent_name}...")
    resp = requests.post(f"{base_url}/reset")
    if resp.status_code != 200:
        print(f"  [!] Error: Could not reset environment for {agent_name}.")
        return 0.0, False
        
    obs = resp.json()["observation"]
    total_score = 0
    steps = 0
    used_fallback = False
    
    # Audit trail trackers
    first_original_chunk = obs.get("data_chunk", "")
    first_sanitized_chunk = ""
    first_score = 0.0
    
    while True:
        # Get action from the specific agent
        action_payload = agent_func(obs)
        if action_payload.pop("is_fallback", False):
            used_fallback = True
            
        if steps == 0:
            first_sanitized_chunk = action_payload.get("content", "")
        
        # Step the environment
        step_resp = requests.post(f"{base_url}/step", json=action_payload)
        if step_resp.status_code != 200:
            # Retry with fallback agent instead of aborting
            fallback = enhanced_agent_logic(obs)
            step_resp = requests.post(f"{base_url}/step", json=fallback)
            if step_resp.status_code != 200:
                print(f"  [!] Step failed even with fallback (status {step_resp.status_code}). Skipping.")
                break
            used_fallback = True
            
        step_data = step_resp.json()
        score = step_data["reward"]["score"]
        
        if steps == 0:
            first_score = score
            
        total_score += score
        steps += 1
        
        obs = step_data.get("observation")
        if step_data.get("done") or obs is None:
            break

    avg_score = total_score / steps if steps > 0 else 0
    print(f"  -> Finished {steps} steps. Average Score: {avg_score:0.2f}")
    
    # Generate the visual HTML audit report for the very first step chunk
    generate_html_report(first_original_chunk, first_sanitized_chunk, agent_name, first_score)
    
    return avg_score, used_fallback


def run_benchmark(api_key=None, model_name=None, dataset_name=None, api_base=None, base_url="http://localhost:7860"):
    dataset_name = (dataset_name or os.getenv("DATASET_NAME", "default")).strip()
    api_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    api_base = (api_base or os.getenv("API_BASE_URL", "https://api.openai.com/v1")).strip()
    model_name = (model_name or os.getenv("MODEL_NAME", "gpt-4o")).strip()

    results = {}

    print(f"\nUsing dataset: {dataset_name}")

    # 1. Run Baseline Agents
    results["RandomAgent"] = evaluate_agent("RandomAgent", random_agent_logic, base_url)
    results["RegexAgent"] = evaluate_agent("RegexAgent", regex_agent_logic, base_url)

    # 2. Setup LLM Client based on Hackathon rules
    rate_limiter = None

    if not api_key:
        print("\n[!] Skipping LLMAgent: Please set your OPENAI_API_KEY in the .env file")
    else:
        client = OpenAI(api_key=api_key, base_url=api_base)

        # Pass the client and model into the agent logic using a lambda
        llm_wrapper = lambda obs: llm_agent_logic(obs, client, model_name, rate_limiter)
        results["LLMAgent"] = evaluate_agent("LLMAgent", llm_wrapper, base_url)

    # 3. Print Final Hackathon Table
    print("\n" + "="*40)
    print("🏆 FINAL AGENT PERFORMANCE TABLE 🏆")
    print("="*40)
    for agent, (score, is_fallback) in results.items():
        if agent == "LLMAgent":
            suffix = "(fall-back)" if is_fallback else f"({model_name})"
            print(f"{agent.ljust(15)} -> Score: {score:0.2f} {suffix}")
        else:
            print(f"{agent.ljust(15)} -> Score: {score:0.2f}")
    print("="*40)

    return results


def _collect_run_config():
    api_key = input("api key: ").strip()
    model_name = input("model name: ").strip()
    dataset = input("dataset: ").strip()

    if not model_name:
        model_name = os.getenv("MODEL_NAME", "gpt-4o")
    if not dataset:
        dataset = "default"

    return {
        "api_key": api_key,
        "model_name": model_name,
        "dataset": dataset,
    }


def run_start_cli():
    print("Type 'start' to run inference, or 'exit' to quit.")
    while True:
        command = input("command> ").strip().lower()

        if command in {"exit", "quit"}:
            print("Exiting.")
            return

        if command != "start":
            print("Unknown command. Use 'start' or 'exit'.")
            continue

        config = _collect_run_config()
        run_benchmark(
            api_key=config["api_key"],
            model_name=config["model_name"],
            dataset_name=config["dataset"],
        )
        return

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "start":
        config = _collect_run_config()
        run_benchmark(
            api_key=config["api_key"],
            model_name=config["model_name"],
            dataset_name=config["dataset"],
        )
    elif len(sys.argv) > 1 and sys.argv[1].lower() == "run":
        run_benchmark()
    else:
        run_start_cli()
