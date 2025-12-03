```markdown
# Repository custom instructions — Crypto-sniper

Purpose
- Provide clear, actionable guidance for contributors and for any AI assistants (e.g., Copilot) working on this repository.
- Emphasize safety, reproducibility, and secure handling of secrets for a trading/crypto automation project.

Who should read this
- Contributors, reviewers, maintainers.
- AI assistants and code generators used to help develop this project.

High-level project description
- Crypto-sniper is a Python project for researching, backtesting, and (optionally) executing crypto trading strategies.
- It contains code for data ingestion, strategy logic, signal generation, backtesting, and interfaces to broker/exchange APIs.

Important safety & security rules (must follow)
- NEVER commit API keys, private keys, or passwords to the repository. Use environment variables (e.g., .env), a secrets manager, or CI secrets.
- All live-trading integration must be behind a clear opt-in flag and set to use testnet/sandbox by default.
- Require backtesting and simulation before any live execution. Include clear checks before enabling any live order submission.
- Keep privileged or dangerous operations (transfers, withdrawals, placing market orders on mainnet) separated by explicit confirmation steps and protected code paths.

Coding style & quality
- Language: Python (3.10+ recommended)
- Formatting: Black, isort. Run pre-commit hooks on commits.
- Type hints everywhere for public functions; mypy-friendly code is preferred.
- Write small, testable functions. Prefer composition over long monoliths.
- Use asyncio for I/O-bound tasks where appropriate and document concurrency choices.

Testing
- Every new feature must include unit tests and, where appropriate, integration tests.
- Provide backtest fixtures and deterministic datasets for strategy tests.
- Use pytest. Tests should be runnable locally with:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements-dev.txt
  - pytest

Environment & secrets
- Use a .env file for local development; add .env to .gitignore.
- Document required env variables in README or this file (e.g., EXCHANGE_API_KEY, EXCHANGE_API_SECRET, TESTNET_URL).
- Use dependency management (requirements.txt or Poetry). Prefer lock files for reproducible builds.

Commits, branches, and PRs
- Branch naming: feat/<short-description>, fix/<short-description>, chore/<short-description>
- Commit messages: Use conventional commits style (type(scope): short description).
- PRs: Provide a clear description of the change, testing performed, and any risks. Link related issues.
- Require at least one approving review before merging. Run CI and ensure all tests pass.

Documentation
- Keep README updated with setup, testing, backtesting, and live execution instructions.
- Document assumptions and any external data sources, API rate limits, and known limitations.

Guidance for AI assistants (how to help)
- When suggesting code changes:
  - Keep suggestions minimal and focused on a single responsibility.
  - Prefer safe defaults (testnet, dry-run modes) and clearly document side effects.
  - Insert TODO comments where the developer must provide secrets/credentials — do not generate real keys.
  - When recommending installation steps or running commands, include exact commands and context (e.g., activate venv).
  - Provide unit tests for any non-trivial logic you add or modify.
  - Include type hints and follow the project's formatting rules in suggestions.
- When asked to write strategies or trading logic:
  - Emphasize risk controls, position sizing, stop-loss logic, and max position limits.
  - Recommend backtesting with multiple market regimes and show statistical results.
  - Warn explicitly when code interacts with live markets.
- When asked to refactor or optimize:
  - Preserve behavior and tests. Provide a migration plan and run tests after each major change.

Issue and bug handling
- When opening issues, include:
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment (python version, OS, branch)
  - Minimal reproducible example or test when possible
- Tag issues with appropriate labels (bug, enhancement, docs, security).

Contacts and escalation
- For security or secrets exposure, immediately notify maintainers and open a private security issue (do not post secrets publicly).
- Add maintainers' contact information here or in the repo README for emergencies.

Appendix: Example env variables (document only — do not store values)
- EXCHANGE_API_KEY
- EXCHANGE_API_SECRET
- EXCHANGE_TESTNET_URL
- DATABASE_URL
- SENTRY_DSN (optional)

Thank you for following these rules — they keep the project safe, maintainable, and useful for everyone.
```