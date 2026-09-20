# Test run

- Timestamp (UTC): `2026-09-20T13:08:55.453183+00:00`
- Git commit: `da9626d3d4be`
- Git dirty: `False`
- Python: `3.12.13`
- Platform: `macOS-15.7.4-arm64-arm-64bit`
- OpenRouter live-test model: `openai/gpt-5-mini`

## Results

| Gate | Exit | Passed | Failed | Errors | Skipped | Tests | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ruff-format | 0 | — | — | — | — | — | — |
| ruff | 0 | — | — | — | — | — | — |
| mypy | 0 | — | — | — | — | — | — |
| deterministic | 0 | 146 | 0 | 0 | 0 | 146 | 0.228 |
| adversarial | 0 | 5 | 0 | 0 | 0 | 5 | 0.092 |
| live | 0 | 5 | 0 | 0 | 0 | 5 | 38.095 |

## Commands

- **ruff-format**: `uv run python -m ruff format --check .`
- **ruff**: `uv run python -m ruff check .`
- **mypy**: `uv run python -m mypy src`
- **deterministic**: `uv run python -m pytest -m not live and not adversarial -q`
- **adversarial**: `uv run python -m pytest -m adversarial -q`
- **live**: `uv run python -m pytest tests/live -m live -q`

> This report records one concrete execution environment. Live-provider results can vary with external availability, provider routing, and rate limits.
