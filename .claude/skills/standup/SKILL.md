---
name: standup
description: Write a three-line standup (Yesterday, Today, Blockers) to data/standup.md from data/tasks.json and the git log since yesterday. Use when the user asks for a standup or daily update.
---

# Standup

Generate a three-line standup and save it to `data/standup.md`.

## Steps

1. Work out today's and yesterday's local dates (YYYY-MM-DD).
2. Read `data/tasks.json` (a JSON list of `{id, title, tag, minutes, date, done, created}`). If it is missing or empty, treat it as no tasks. Never modify it.
3. Run `git log --since="yesterday 00:00" --pretty=format:"%h %ad %s" --date=short` to get recent commits.
4. Build the three lines:
   - **Yesterday**: tasks with `date` = yesterday (done ones first) plus yesterday's commit subjects. Summarize briefly, not a raw dump, and include the total time.
   - **Today**: tasks with `date` = today that are not done, plus today's done tasks and commits as "already". If nothing is planned, say so.
   - **Blockers**: tasks that are not done and dated before today. If there are none, write "None".
5. Write exactly this shape to `data/standup.md`, overwriting any previous file:

```
**Yesterday:** ...
**Today:** ...
**Blockers:** ...
```

6. Show the three lines to the user and confirm the file path.

## Rules

- Always display times as "1 h 30 min" (e.g. 90 minutes → "1 h 30 min", 45 → "45 min", 120 → "2 h"). Never use "90m" or "1.5h".
- Each section is a single line. No extra headings or bullets.
- Only use facts from the tasks and git log. Do not invent work or blockers.
- If both tasks and commits are empty for a section, write "Nothing logged".
