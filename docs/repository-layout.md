# Repository Layout

The repository separates implementation, tests, evaluations, generated evidence, and explanatory documentation. The distinction is intentional.

```text
safe-web-research/
├── src/safe_web_research/    library and CLI implementation
├── tests/                    pytest suites and test-only fixtures
│   └── fixtures/             static inputs used only by tests
├── benchmarks/               executable evaluation code and case definitions
│   ├── security/             deterministic compromised-model containment benchmark
│   └── research_quality/     live research quality/efficiency benchmark
├── reports/                  generated evidence artifacts from clean commits
│   ├── test_runs/            quality-gate execution records
│   ├── security_benchmark/   deterministic benchmark results
│   └── research_quality/     live benchmark results
├── scripts/                  developer/release helper commands
└── docs/                     explanatory docs and architecture decisions
    └── adr/                  Architecture Decision Records
```

## `src/`

Product code only. Provider-specific wire handling belongs behind provider-neutral interfaces. Empty placeholders for future REST/MCP adapters are intentionally not kept in the tree; an adapter directory should appear only when an adapter exists.

## `tests/`

Regression tests that answer "does this invariant or behavior still work?"

- `unit/`: isolated component contracts;
- `integration/`: multiple real components with fake external providers;
- `adversarial/`: security invariants under hostile inputs/compromised fake-model behavior;
- `live/`: opt-in external provider/network checks;
- `benchmark/`: deterministic tests for benchmark implementation itself;
- `fixtures/`: static test input files.

Test fixtures live under `tests/` because they are not a runtime feature.

## `benchmarks/`

Executable evaluations that answer broader comparative or quality questions. A benchmark directory owns its code, case definition, and methodology README.

Benchmark code does **not** store its generated results beside the implementation. Results go to `reports/` so changing benchmark code is visually distinct from recording a new execution.

## `reports/`

Committed evidence produced by scripts/benchmarks from identifiable Git revisions. Reports are outputs, not executable logic.

Each report family has a README explaining how it is generated. Timestamped files preserve a specific run; `latest.*` is a convenience copy. Historical reports may mention repository paths that were valid at the commit recorded inside that report.

## `docs/`

Long-lived explanation of the current system. Public documentation should describe capabilities, not internal development milestone labels.

Consequential architectural choices belong in `docs/adr/`. Direct documentation such as `architecture.md` describes the current state; ADRs explain *why* important decisions were made and what tradeoffs were accepted.

## `scripts/`

Small developer/release workflows that do not belong to the importable package, such as standard quality gates, real-provider smoke checks, and report recording.
