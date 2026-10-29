"""DevPulse MCP server (stdio): log and review tasks in data/tasks.json.

Validation and storage come from server.py so the rules stay in one place.
Run with the project venv: .venv/Scripts/python mcp/devpulse_mcp.py
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server  # noqa: E402  (reuses validate_new_task, load_tasks, save_tasks, DATA_PATH)

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

mcp = MCPServer("devpulse")


def fmt_minutes(total):
    """Format minutes as "1 h 30 min" (drops a zero part: "2 h", "45 min")."""
    h, m = divmod(total, 60)
    if h and m:
        return "%d h %d min" % (h, m)
    return "%d h" % h if h else "%d min" % m


@mcp.tool()
def log_task(title: str, tag: str = "general", minutes: int = 30) -> str:
    """Log a task for today. title: 1-200 chars. tag: lowercase label, <=30 chars,
    no commas (default "general"). minutes: whole number 1-1440."""
    try:
        task = server.validate_new_task({
            "title": title,
            "tag": tag,
            "minutes": minutes,
            "date": date.today().isoformat(),
        })
    except server.ApiError as e:
        raise ToolError(e.message)
    with server.lock:
        tasks = server.load_tasks()
        tasks.append(task)
        server.save_tasks(tasks)
    return "Logged '%s' [%s] for %s on %s (id %s)" % (
        task["title"], task["tag"], fmt_minutes(task["minutes"]), task["date"], task["id"])


@mcp.tool()
def list_today() -> str:
    """List today's tasks with tag, duration and done status, plus the total time."""
    today = date.today().isoformat()
    with server.lock:
        tasks = [t for t in server.load_tasks() if t.get("date") == today]
    if not tasks:
        return "No tasks logged today (%s)." % today
    lines = ["%s %s [%s] %s" % ("[x]" if t.get("done") else "[ ]", t.get("title"),
                                t.get("tag"), fmt_minutes(t.get("minutes", 0))) for t in tasks]
    lines.append("Total: %s" % fmt_minutes(sum(t.get("minutes", 0) for t in tasks)))
    return "\n".join(lines)


@mcp.tool()
def week_summary() -> str:
    """Summarize the last 7 days (today included): total time, tasks done, and time per tag."""
    today = date.today()
    start = (today - timedelta(days=6)).isoformat()
    with server.lock:
        tasks = [t for t in server.load_tasks() if start <= t.get("date", "") <= today.isoformat()]
    if not tasks:
        return "No tasks from %s to %s." % (start, today.isoformat())
    by_tag = {}
    for t in tasks:
        by_tag[t.get("tag", "general")] = by_tag.get(t.get("tag", "general"), 0) + t.get("minutes", 0)
    lines = ["%s to %s: %d tasks (%d done), %s total" % (
        start, today.isoformat(), len(tasks), sum(1 for t in tasks if t.get("done")),
        fmt_minutes(sum(by_tag.values())))]
    for tag, mins in sorted(by_tag.items(), key=lambda kv: -kv[1]):
        lines.append("  %s: %s" % (tag, fmt_minutes(mins)))
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()  # stdio; never print to stdout here, it carries the protocol
