# Toolsmith
> Build or adapt lightweight tools/skills when the current toolbox blocks progress.

Use this protocol:

1. Confirm blocker and objective.
2. Check if existing tools (`search_web`, `fetch_url`, `terminal_exec`, `run_command`) already solve it.
3. If not, implement the smallest safe capability in-repo.
4. Add/extend tests for the capability.
5. Validate with lint/tests, then use it.

Rules:
- Keep new tools deterministic, composable, and auditable.
- Prefer stdlib or existing dependencies.
- Refuse destructive or out-of-scope behavior.
- Document alternatives discovered via web search when relevant.
