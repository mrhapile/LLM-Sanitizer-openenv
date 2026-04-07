import json
import os
import webbrowser
from html import escape

import requests


def generate_html_report(observation, action_payload, reward_payload, output_path):
    raw = escape(observation["data_chunk"])
    cleaned = escape(action_payload["content"])
    risk_items = "".join(f"<li>{escape(item)}</li>" for item in observation["risk_report"])
    failures = "".join(f"<li>{escape(item)}</li>" for item in reward_payload["info"]["failure_reasons"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Release Desk Demo</title>
  <style>
    :root {{
      --bg: #f4efe6;
      --panel: #fffaf2;
      --ink: #1f1a17;
      --accent: #a64b2a;
      --muted: #6d6258;
      --line: #ddcfbe;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: radial-gradient(circle at top, #fff8eb 0%, var(--bg) 60%);
      color: var(--ink);
      padding: 32px;
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
      display: grid;
      gap: 24px;
    }}
    .hero, .grid > section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 24px;
      box-shadow: 0 12px 30px rgba(61, 43, 28, 0.08);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 24px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 13px;
      line-height: 1.5;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      background: #f1d7c9;
      color: var(--accent);
      margin-right: 8px;
      font-size: 12px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    ul {{
      padding-left: 18px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="badge">{escape(observation["task_type"])}</div>
      <div class="badge">{escape(observation["task_name"])}</div>
      <h1>AI Data Release Desk Demo</h1>
      <p>{escape(observation["instruction"])}</p>
      <p>Score: <strong>{reward_payload["reward"]["score"]:.3f}</strong></p>
    </section>
    <div class="grid">
      <section>
        <h2>Original Document</h2>
        <pre>{raw}</pre>
      </section>
      <section>
        <h2>Agent Output</h2>
        <pre>{cleaned}</pre>
      </section>
      <section>
        <h2>Risk Report</h2>
        <ul>{risk_items}</ul>
      </section>
      <section>
        <h2>Failure Reasons</h2>
        <ul>{failures or "<li>None</li>"}</ul>
      </section>
    </div>
  </div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(html)


def main():
    base_url = os.getenv("OPENENV_BASE_URL", "http://localhost:7860")
    reset_response = requests.post(f"{base_url}/reset", timeout=30)
    reset_response.raise_for_status()
    observation = reset_response.json()["observation"]

    if observation["content_format"] == "json":
        content = "{\"service\":\"payments\",\"owner_email\":\"[REDACTED]\",\"on_call\":\"[REDACTED]\",\"api_key\":\"[REDACTED]\",\"status\":\"rotate before deploy\"}"
        action = {"action_type": "rewrite", "content": content, "notes": "demo json rewrite"}
    elif "No obvious high-risk markers detected" in observation["risk_report"]:
        action = {"action_type": "bypass", "content": observation["data_chunk"], "notes": "demo bypass"}
    else:
        content = observation["data_chunk"].replace("aria.cole@acme-retail.com", "[REDACTED]").replace("4155550132", "[REDACTED]").replace("sk-live-ACME99887766", "[REDACTED]")
        action = {"action_type": "redact", "content": content, "notes": "demo redaction"}

    step_response = requests.post(f"{base_url}/step", json=action, timeout=30)
    step_response.raise_for_status()
    payload = step_response.json()

    output_path = os.path.abspath("release_desk_demo.html")
    generate_html_report(observation, action, payload, output_path)
    webbrowser.open(f"file://{output_path}")
    print(json.dumps(payload["reward"], indent=2))


if __name__ == "__main__":
    main()
