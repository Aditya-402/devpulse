"""Build docs/index.html, a public "What I'm building" page, from tasks tagged "public"."""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.environ.get("DEVPULSE_DATA") or os.path.join(ROOT, "data", "tasks.json")
OUT_PATH = os.path.join(ROOT, "docs", "index.html")


def fmt(m):
    h, r = divmod(m, 60)
    if not h:
        return f"{r} min"
    return f"{h} h {r} min" if r else f"{h} h"


def load_public_tasks():
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            tasks = json.load(f)
    except FileNotFoundError:
        return []
    return sorted((t for t in tasks if t.get("tag") == "public"),
                  key=lambda t: t["date"], reverse=True)


def render(tasks):
    # Only title, minutes, date and done are published; ids and timestamps stay private.
    rows = "\n".join(
        f'    <li class="{"done" if t["done"] else "open"}">'
        f'<span class="check">{"&#10003;" if t["done"] else "&#9675;"}</span>'
        f'<span class="title">{html.escape(t["title"])}</span>'
        f'<span class="meta">{html.escape(t["date"])} &middot; {fmt(t["minutes"])}</span></li>'
        for t in tasks
    ) or '    <li class="empty">Nothing public yet.</li>'
    total = fmt(sum(t["minutes"] for t in tasks))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>What I'm building</title>
<style>
  :root {{ --bg: #fff; --fg: #1c1c1e; --muted: #6b6b70; --line: #e4e4e7; --accent: #2563eb; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #121214; --fg: #ececee; --muted: #9a9aa0; --line: #2a2a2e; --accent: #60a5fa; }}
  }}
  body {{ font: 16px/1.5 system-ui, sans-serif; background: var(--bg); color: var(--fg);
         max-width: 40rem; margin: 0 auto; padding: 2rem 16px; }}
  h1 {{ margin: 0 0 .25rem; }}
  .total {{ color: var(--muted); margin: 0 0 1.5rem; }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  li {{ display: grid; grid-template-columns: 1.5rem 1fr auto; gap: .5rem; padding: .6rem 0;
       border-top: 1px solid var(--line); }}
  .check {{ color: var(--accent); }}
  .meta {{ color: var(--muted); white-space: nowrap; }}
  li.empty {{ display: block; color: var(--muted); }}
  @media (max-width: 480px) {{ li {{ grid-template-columns: 1.5rem 1fr; }} .meta {{ grid-column: 2; }} }}
</style>
</head>
<body>
  <h1>What I'm building</h1>
  <p class="total">{len(tasks)} items &middot; {total} so far</p>
  <ul>
{rows}
  </ul>
</body>
</html>
"""


def main():
    tasks = load_public_tasks()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(render(tasks))
    print(f"Wrote {OUT_PATH} with {len(tasks)} public task(s)")


if __name__ == "__main__":
    sys.exit(main())
