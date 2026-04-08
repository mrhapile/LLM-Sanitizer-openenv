import html
import json
import os
import webbrowser
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from openai import OpenAI

from api_key_utils import get_api_key_env
from inference import llm_agent_logic, random_agent_logic, rules_agent_logic


load_dotenv()


SHOWCASE_TASKS = {"easy", "medium", "hard"}


def run_episode(base_url: str, agent_name: str, agent_func) -> Tuple[List[Dict], Dict[str, float], Dict[str, int]]:
    response = requests.post(f"{base_url}/reset", timeout=30)
    response.raise_for_status()
    observation = response.json()["observation"]

    episodes: List[Dict] = []
    failure_counts: Dict[str, int] = {}
    totals = {"easy": [], "medium": [], "hard": []}

    while True:
        action = agent_func(observation)
        step = requests.post(f"{base_url}/step", json=action, timeout=30)
        step.raise_for_status()
        payload = step.json()

        record = {
            "agent_name": agent_name,
            "observation": observation,
            "action": action,
            "reward": payload["reward"],
            "info": payload["info"],
        }
        episodes.append(record)
        totals[payload["info"]["task_type"]].append(payload["reward"]["score"])
        for failure in payload["info"]["failure_reasons"]:
            failure_counts[failure] = failure_counts.get(failure, 0) + 1

        if payload["done"]:
            break
        observation = payload["observation"]

    averages = {
        task_type: round(sum(scores) / len(scores), 3) if scores else 0.0
        for task_type, scores in totals.items()
    }
    averages["overall"] = round(sum(sum(scores) for scores in totals.values()) / sum(len(scores) for scores in totals.values()), 3)
    return episodes, averages, dict(sorted(failure_counts.items()))


def build_case_lookup(records: List[Dict]) -> Dict[str, Dict]:
    lookup = {}
    for record in records:
        task_type = record["observation"]["task_type"]
        if task_type not in lookup:
            lookup[task_type] = record
    return lookup


def render_failures(failure_counts: Dict[str, int]) -> str:
    if not failure_counts:
        return "<li>None</li>"
    return "".join(f"<li><strong>{html.escape(name)}</strong>: {count}</li>" for name, count in failure_counts.items())


def render_score_items(summary: Dict[str, float]) -> str:
  return (
    f"<li><span>Overall</span><strong>{summary['overall']:.3f}</strong></li>"
    f"<li><span>Easy</span><strong>{summary['easy']:.3f}</strong></li>"
    f"<li><span>Medium</span><strong>{summary['medium']:.3f}</strong></li>"
    f"<li><span>Hard</span><strong>{summary['hard']:.3f}</strong></li>"
  )


def maybe_build_llm_agent() -> Tuple[Optional[Callable[[Dict], Dict]], str]:
  api_key_env = get_api_key_env()
  if not api_key_env:
    return None, "LLMAgent skipped: no API key env var found"

  api_key_name, api_key = api_key_env
  model_name = os.getenv("MODEL_NAME", "gpt-4o-mini").strip()
  api_base_url = os.getenv("API_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).strip()
  client = OpenAI(api_key=api_key, base_url=api_base_url)

  return lambda obs: llm_agent_logic(obs, client, model_name), f"LLMAgent configured via {api_key_name}"


def render_case(agent_name: str, record: Dict) -> str:
    observation = record["observation"]
    action = record["action"]
    reward = record["reward"]
    info = record["info"]

    risk_items = "".join(f"<li>{html.escape(item)}</li>" for item in observation["risk_report"])
    adversarial_items = "".join(f"<li>{html.escape(item)}</li>" for item in observation["adversarial_signals"]) or "<li>None</li>"
    failure_items = "".join(f"<li>{html.escape(item)}</li>" for item in info["failure_reasons"]) or "<li>None</li>"
    sensitive_items = "".join(f"<li>{html.escape(item)}</li>" for item in info["detected_sensitive_types"]) or "<li>None</li>"

    return f"""
    <section class="case-card">
      <div class="case-meta">
        <span class="pill pill-{html.escape(observation['task_type'])}">{html.escape(observation['task_type'])}</span>
        <span class="pill pill-agent">{html.escape(agent_name)}</span>
        <span class="pill pill-action">{html.escape(action['action_type'])}</span>
      </div>
      <h3>{html.escape(observation['task_name'])}</h3>
      <p class="instruction">{html.escape(observation['instruction'])}</p>
      <div class="metrics">
        <div><span>Score</span><strong>{reward['score']:.3f}</strong></div>
        <div><span>Leak</span><strong>{reward['leak_free_ratio']:.3f}</strong></div>
        <div><span>Policy</span><strong>{reward['policy_ratio']:.3f}</strong></div>
        <div><span>Adversarial</span><strong>{reward['adversarial_ratio']:.3f}</strong></div>
      </div>
      <div class="pane-grid">
        <div class="pane">
          <h4>Before</h4>
          <pre>{html.escape(observation['data_chunk'])}</pre>
        </div>
        <div class="pane">
          <h4>After</h4>
          <pre>{html.escape(action['content'])}</pre>
        </div>
      </div>
      <div class="list-grid">
        <div>
          <h4>Risk Report</h4>
          <ul>{risk_items}</ul>
        </div>
        <div>
          <h4>Adversarial Signals</h4>
          <ul>{adversarial_items}</ul>
        </div>
        <div>
          <h4>Detected Types</h4>
          <ul>{sensitive_items}</ul>
        </div>
        <div>
          <h4>Failure Reasons</h4>
          <ul>{failure_items}</ul>
        </div>
      </div>
    </section>
    """


def generate_html_report(
  output_path: Path,
  rules_records: List[Dict],
  random_records: List[Dict],
  rules_summary: Dict[str, float],
  random_summary: Dict[str, float],
  rules_failures: Dict[str, int],
  random_failures: Dict[str, int],
  llm_summary: Optional[Dict[str, float]] = None,
  llm_failures: Optional[Dict[str, int]] = None,
  llm_status: Optional[str] = None,
) -> None:
    rules_cases = build_case_lookup(rules_records)
    random_cases = build_case_lookup(random_records)

    showcase_sections = []
    for task_type in ["easy", "medium", "hard"]:
        showcase_sections.append(
            f"""
            <section class="showcase-block">
              <header>
                <h2>{task_type.title()} Task Showcase</h2>
                <p>Naive output versus task-aware sanitization on the same document class.</p>
              </header>
              <div class="showcase-grid">
                {render_case('RandomAgent', random_cases[task_type])}
                {render_case('RulesAgent', rules_cases[task_type])}
              </div>
            </section>
            """
        )

    llm_summary_card = ""
    llm_failures_card = ""
    llm_status_card = ""
    if llm_summary is not None and llm_failures is not None:
        llm_summary_card = f"""
      <section>
        <h2>LLMAgent Scores</h2>
        <ul class="summary-list">{render_score_items(llm_summary)}</ul>
      </section>"""
        llm_failures_card = f"""
      <section>
        <h2>LLMAgent Failure Counts</h2>
        <ul>{render_failures(llm_failures)}</ul>
      </section>"""
    elif llm_status:
        llm_status_card = f"""
      <section>
        <h2>LLMAgent Status</h2>
        <p>{html.escape(llm_status)}</p>
      </section>"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Release Desk Demo Report</title>
  <style>
    :root {{
      --paper: #f4efe4;
      --panel: rgba(255, 251, 245, 0.88);
      --panel-strong: #fffdf8;
      --ink: #1c1917;
      --muted: #655b53;
      --line: rgba(104, 81, 61, 0.18);
      --easy: #3b7a57;
      --medium: #c2741f;
      --hard: #9c2f2f;
      --agent: #335c81;
      --action: #735751;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 0% 0%, rgba(219, 186, 145, 0.22), transparent 35%),
        radial-gradient(circle at 100% 20%, rgba(130, 165, 143, 0.18), transparent 30%),
        linear-gradient(180deg, #faf5eb 0%, var(--paper) 52%, #ede4d7 100%);
      min-height: 100vh;
    }}
    .wrap {{
      width: min(1280px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 60px;
      display: grid;
      gap: 28px;
    }}
    .hero, .summary-grid > section, .showcase-block {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 26px;
      box-shadow: 0 16px 50px rgba(63, 47, 34, 0.08);
      backdrop-filter: blur(12px);
    }}
    .hero {{
      overflow: hidden;
      position: relative;
      padding: 34px;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(125deg, rgba(166, 75, 42, 0.12), transparent 38%),
        linear-gradient(310deg, rgba(59, 122, 87, 0.10), transparent 32%);
      pointer-events: none;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 3.6rem);
      line-height: 0.98;
      letter-spacing: -0.03em;
    }}
    .hero p {{
      max-width: 740px;
      color: var(--muted);
      font-size: 1.05rem;
      margin: 0;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 18px;
    }}
    .summary-grid > section {{
      padding: 22px;
    }}
    .summary-grid h2 {{
      margin: 0 0 12px;
      font-size: 1.1rem;
    }}
    .summary-list {{
      display: grid;
      gap: 10px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .summary-list li {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 10px 12px;
      border-radius: 14px;
      background: var(--panel-strong);
      border: 1px solid rgba(104, 81, 61, 0.1);
      font-size: 0.96rem;
    }}
    .showcase-block {{
      padding: 24px;
      display: grid;
      gap: 20px;
    }}
    .showcase-block header p {{
      margin: 6px 0 0;
      color: var(--muted);
    }}
    .showcase-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 18px;
    }}
    .case-card {{
      background: var(--panel-strong);
      border: 1px solid rgba(104, 81, 61, 0.12);
      border-radius: 22px;
      padding: 18px;
      display: grid;
      gap: 16px;
    }}
    .case-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      padding: 7px 11px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.72rem;
      font-weight: 700;
      color: white;
    }}
    .pill-easy {{ background: var(--easy); }}
    .pill-medium {{ background: var(--medium); }}
    .pill-hard {{ background: var(--hard); }}
    .pill-agent {{ background: var(--agent); }}
    .pill-action {{ background: var(--action); }}
    .instruction {{
      margin: 0;
      color: var(--muted);
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .metrics div {{
      padding: 12px;
      border-radius: 16px;
      background: #fff;
      border: 1px solid rgba(104, 81, 61, 0.12);
    }}
    .metrics span {{
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 5px;
    }}
    .metrics strong {{
      font-size: 1.25rem;
    }}
    .pane-grid, .list-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
    }}
    .pane, .list-grid > div {{
      background: #fff;
      border: 1px solid rgba(104, 81, 61, 0.12);
      border-radius: 16px;
      padding: 14px;
    }}
    h2, h3, h4 {{
      margin: 0;
    }}
    h3 {{
      font-size: 1.25rem;
    }}
    h4 {{
      margin-bottom: 10px;
      font-size: 0.92rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.83rem;
      line-height: 1.55;
      font-family: "SFMono-Regular", Consolas, monospace;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 7px;
    }}
    @media (max-width: 720px) {{
      .wrap {{
        width: min(100vw - 18px, 1280px);
        padding: 12px 0 28px;
      }}
      .hero {{
        padding: 24px;
      }}
      .metrics {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>Release Desk Demo Report</h1>
      <p>Judge-facing before/after showcase for enterprise data release review. Each section compares naive behavior with the task-aware baseline across easy, medium, and hard cases, including adversarial prompt injection and obfuscated secret removal.</p>
    </section>

    <section class="summary-grid">
      <section>
        <h2>RulesAgent Scores</h2>
        <ul class="summary-list">{render_score_items(rules_summary)}</ul>
      </section>
      <section>
        <h2>RandomAgent Scores</h2>
        <ul class="summary-list">{render_score_items(random_summary)}</ul>
      </section>
      {llm_summary_card}
      <section>
        <h2>RulesAgent Failure Counts</h2>
        <ul>{render_failures(rules_failures)}</ul>
      </section>
      <section>
        <h2>RandomAgent Failure Counts</h2>
        <ul>{render_failures(random_failures)}</ul>
      </section>
      {llm_failures_card}
      {llm_status_card}
    </section>

    {''.join(showcase_sections)}
  </main>
</body>
</html>"""

    output_path.write_text(html_body, encoding="utf-8")


def main():
    base_url = os.getenv("OPENENV_BASE_URL", "http://localhost:7860")

    random_records, random_summary, random_failures = run_episode(base_url, "RandomAgent", random_agent_logic)
    rules_records, rules_summary, rules_failures = run_episode(base_url, "RulesAgent", rules_agent_logic)

    llm_summary: Optional[Dict[str, float]] = None
    llm_failures: Optional[Dict[str, int]] = None
    llm_status = ""

    llm_agent_func, llm_status = maybe_build_llm_agent()
    if llm_agent_func is not None:
        try:
            _, llm_summary, llm_failures = run_episode(base_url, "LLMAgent", llm_agent_func)
            llm_status = "LLMAgent included in report"
        except Exception as exc:
            llm_status = f"LLMAgent skipped after API failure: {type(exc).__name__}: {exc}"

    output_path = Path(os.path.abspath("release_desk_demo.html"))
    generate_html_report(
        output_path,
        rules_records,
        random_records,
        rules_summary,
        random_summary,
        rules_failures,
        random_failures,
        llm_summary,
        llm_failures,
        llm_status,
    )
    webbrowser.open(output_path.as_uri())

    print(json.dumps({
        "random_summary": random_summary,
        "rules_summary": rules_summary,
        "random_failures": random_failures,
        "rules_failures": rules_failures,
    "llm_summary": llm_summary,
    "llm_failures": llm_failures,
    "llm_status": llm_status,
        "report": str(output_path),
    }, indent=2))


if __name__ == "__main__":
    main()
