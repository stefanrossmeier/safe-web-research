# Jev semantic content-judgement evaluation

This live evaluation exercises Jev on **40 paired cases**: 20 operative attacks and 20 deliberately difficult benign negatives. The benign cases are not generic safe prose. They contain the same vocabulary that simple detectors flag—quoted prompt injections, shell commands, secret names, localhost/metadata URLs, fake role markers, tool calls, and fabricated-citation examples—but in documentation, tests, incident reports, policy text, or security training where the content is descriptive rather than operative.

Each family therefore contains a semantic contrast such as:

- documentation saying an attacker may write `ignore previous instructions` vs. a page actually issuing that instruction;
- SSRF guidance mentioning `127.0.0.1` vs. content ordering the agent to fetch it;
- secret-handling guidance naming API keys vs. content requesting their values;
- provenance documentation describing fabricated citations vs. content ordering the model to invent one;
- shell/tool documentation vs. direct capability-induction instructions.

The corpus lives in [`cases.json`](cases.json). It is intentionally human-readable and reviewable.

## Run

Load your OpenRouter key, then run from the repository root:

```bash
set -a
source .env
set +a

uv run python -m benchmarks.content_judgement --allow-dirty
```

For a committed revision, omit `--allow-dirty` so reports are tied to a clean Git state.

The default descriptive threshold is `0.85`. Change it only for calibration experiments:

```bash
uv run python -m benchmarks.content_judgement --threshold 0.95 --allow-dirty
```

The command writes timestamped and `latest` Markdown/JSON reports under `reports/content_judgement/`. Reports include TP/TN/FP/FN, accuracy, precision, recall, benign/malicious risk distributions, every individual Jev signal, latency, tokens, model revision, and estimated cost.

## Interpretation

This is **calibration and regression evidence**, not an authorization test. The threshold does not alter the runtime's observe-only behavior. A good result demonstrates that Jev can distinguish these authored semantic contrasts; it does not prove general prompt-injection detection or justify a filtering threshold by itself.
