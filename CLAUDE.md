# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Run the app: `python server.py [port]` (default port 8000, binds 127.0.0.1)
- Run all tests: `python test_server.py`
- Run a single test: `python -m unittest test_server.ServerTest.test_crud_and_persistence`

No dependencies, build step, or linter — Python stdlib only.

## Rules

- The server uses only the Python standard library — no third-party packages.
- The front end is plain JavaScript in `index.html` — no npm packages or frameworks.
- Run the app with `python server.py`.
- Run the tests with `python test_server.py`.
- Always display times in the format "1 h 30 min".

## Architecture

DevPulse is a task/time tracker with two files that matter:

- `server.py` — stdlib `http.server` (`ThreadingHTTPServer`) that serves `index.html` at `/` and a JSON API under `/api/tasks` (`GET` with optional `from`/`to` YYYY-MM-DD filters, `POST`, `PATCH /api/tasks/<32-hex id>` which accepts any of `done`, `title`, `tag`, `minutes` (at least one, validated like POST), `DELETE`).
- `index.html` — the entire frontend (inline CSS/JS, no build, light/dark via `prefers-color-scheme`), talking to the API above.

Storage is a single JSON list in `data/tasks.json` (override with the `DEVPULSE_DATA` env var). Every request re-reads the file under a global `lock`; writes go through `save_tasks`, which writes a `.tmp` file and `os.replace`s it. A corrupt file is moved aside to `tasks.json.bad` and treated as empty rather than overwritten.

Validation lives in `validate_new_task` (title 1–200 chars, tag lowercased/≤30 chars/no commas and defaulting to `general`, minutes int 1–1440 and not bool, valid date). Errors are raised as `ApiError(status, message)` and turned into `{"error": ...}` responses by `Handler._dispatch`.

## Testing notes

`test_server.py` starts a real server on an ephemeral port (`make_server(0)`) and points `server.DATA_PATH` at a temp directory, so tests never touch `data/tasks.json`. Tests that use `DATA_PATH` must set it on the `server` module (it is read at call time).
