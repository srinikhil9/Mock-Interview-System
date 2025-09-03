# Contributing

Thanks for your interest in contributing! This project focuses on practical multi‑agent coordination. Please keep changes incremental and well‑scoped.

## How to contribute
1. Fork the repo and create a feature branch.
2. Install dev tools: `pip install -r requirements-dev.txt` then `pre-commit install`.
3. Run linters/formatters: `ruff check .` and `black .`.
4. Add/update tests if applicable (smoke imports must pass in CI).
5. Open a pull request with a clear description and rationale.

## Coding guidelines
- Prefer async/await for agent interactions; avoid blocking calls in the hot path.
- Keep agent responsibilities small with explicit message contracts.
- Handle errors defensively; avoid silent failures.
- Write readable code: descriptive names, early returns, minimal nesting.

## Commit messages
- Use concise, imperative subject lines (e.g., "Add evaluator fallback").
- Reference issues when relevant.

## Reporting issues
- Provide reproduction steps, expected vs. actual behavior, and logs if available.
