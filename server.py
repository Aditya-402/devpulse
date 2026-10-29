"""DevPulse server: stdlib only. Serves index.html and a small JSON API
backed by data/tasks.json.

Usage: python server.py [port]
"""
import json
import os
import re
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "index.html")
STREAK_PATH = os.path.join(BASE_DIR, "streak.js")
DATA_PATH = os.environ.get("DEVPULSE_DATA", os.path.join(BASE_DIR, "data", "tasks.json"))
MAX_BODY = 10 * 1024
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

lock = threading.Lock()


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------- storage ----------

def load_tasks():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("tasks.json is not a list")
        return data
    except FileNotFoundError:
        return []
    except (ValueError, OSError):
        # Corrupt file: keep it aside instead of overwriting it.
        try:
            os.replace(DATA_PATH, DATA_PATH + ".bad")
        except OSError:
            pass
        return []


def load_standup():
    """Text of standup.md (next to tasks.json), or "" if it hasn't been written."""
    try:
        with open(os.path.join(os.path.dirname(DATA_PATH), "standup.md"), "r", encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def save_tasks(tasks):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, DATA_PATH)


# ---------- validation ----------

def valid_date(value):
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def clean_title(title):
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
        raise ApiError(400, "title must be 1-200 characters")
    return title.strip()


def clean_tag(tag):
    if tag is None or (isinstance(tag, str) and not tag.strip()):
        tag = "general"
    if not isinstance(tag, str):
        raise ApiError(400, "tag must be a string")
    tag = tag.strip().lower()
    if len(tag) > 30 or "," in tag:
        raise ApiError(400, "tag must be 1-30 characters with no commas")
    return tag


def clean_minutes(minutes):
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 1440:
        raise ApiError(400, "minutes must be an integer from 1 to 1440")
    return minutes


def validate_new_task(body):
    if not isinstance(body, dict):
        raise ApiError(400, "Body must be a JSON object")

    title = clean_title(body.get("title"))
    tag = clean_tag(body.get("tag"))
    minutes = clean_minutes(body.get("minutes"))

    date = body.get("date")
    if not valid_date(date):
        raise ApiError(400, "date must be a valid YYYY-MM-DD")

    return {
        "id": uuid.uuid4().hex,
        "title": title,
        "tag": tag,
        "minutes": minutes,
        "date": date,
        "done": False,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# ---------- handler ----------

class Handler(BaseHTTPRequestHandler):
    server_version = "DevPulse/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status, payload=None, content_type="application/json; charset=utf-8"):
        if payload is None:
            body = b""
        elif isinstance(payload, bytes):
            body = payload
        else:
            body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if status != 204:
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ApiError(400, "Bad Content-Length")
        if length > MAX_BODY:
            raise ApiError(413, "Body too large")
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "Invalid JSON")

    def _task_id(self, path):
        m = re.fullmatch(r"/api/tasks/([0-9a-f]{32})", path)
        return m.group(1) if m else None

    def _dispatch(self, fn):
        try:
            fn()
        except ApiError as e:
            self._send(e.status, {"error": e.message})
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("Unhandled error: %r\n" % (e,))
            self._send(500, {"error": "Internal server error"})

    # --- verbs ---

    def do_GET(self):
        self._dispatch(self._get)

    do_HEAD = do_GET

    def _get(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            with open(INDEX_PATH, "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif url.path == "/streak.js":
            with open(STREAK_PATH, "rb") as f:
                self._send(200, f.read(), "text/javascript; charset=utf-8")
        elif url.path == "/api/standup":
            self._send(200, {"text": load_standup()})
        elif url.path == "/api/tasks":
            q = parse_qs(url.query)
            start = q.get("from", [None])[0]
            end = q.get("to", [None])[0]
            for v in (start, end):
                if v is not None and not valid_date(v):
                    raise ApiError(400, "from/to must be YYYY-MM-DD")
            with lock:
                tasks = load_tasks()
            if start:
                tasks = [t for t in tasks if t.get("date", "") >= start]
            if end:
                tasks = [t for t in tasks if t.get("date", "") <= end]
            self._send(200, tasks)
        else:
            raise ApiError(404, "Not found")

    def do_POST(self):
        self._dispatch(self._post)

    def _post(self):
        if urlparse(self.path).path != "/api/tasks":
            raise ApiError(404, "Not found")
        task = validate_new_task(self._read_json())
        with lock:
            tasks = load_tasks()
            tasks.append(task)
            save_tasks(tasks)
        self._send(201, task)

    def do_PATCH(self):
        self._dispatch(self._patch)

    def _patch(self):
        task_id = self._task_id(urlparse(self.path).path)
        if not task_id:
            raise ApiError(404, "Not found")
        body = self._read_json()
        if not isinstance(body, dict):
            raise ApiError(400, "Body must be a JSON object")
        updates = {}
        if "done" in body:
            if not isinstance(body["done"], bool):
                raise ApiError(400, "done must be true or false")
            updates["done"] = body["done"]
        if "title" in body:
            updates["title"] = clean_title(body["title"])
        if "tag" in body:
            updates["tag"] = clean_tag(body["tag"])
        if "minutes" in body:
            updates["minutes"] = clean_minutes(body["minutes"])
        if not updates:
            raise ApiError(400, "Nothing to update (done, title, tag or minutes)")
        with lock:
            tasks = load_tasks()
            task = next((t for t in tasks if t.get("id") == task_id), None)
            if task is None:
                raise ApiError(404, "Task not found")
            task.update(updates)
            save_tasks(tasks)
        self._send(200, task)

    def do_DELETE(self):
        self._dispatch(self._delete)

    def _delete(self):
        task_id = self._task_id(urlparse(self.path).path)
        if not task_id:
            raise ApiError(404, "Not found")
        with lock:
            tasks = load_tasks()
            remaining = [t for t in tasks if t.get("id") != task_id]
            if len(remaining) == len(tasks):
                raise ApiError(404, "Task not found")
            save_tasks(remaining)
        self._send(204)


def make_server(port=8000, host="127.0.0.1"):
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    httpd = make_server(port)
    print("DevPulse running at http://127.0.0.1:%d  (data: %s)" % (port, DATA_PATH))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBye.")
