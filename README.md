# LLM Serving Cost

Profile local LLM inference and compare it to Cloud API pricing — so a
deployment decision is based on measurements, not guesses.

## Problem

Every LLM deployment reaches the same question: when does on-prem become
cheaper than API? And what exactly is the cost of running a model
yourself — TTFT, throughput, tail latency? This project builds the
measurement layer to answer those questions.

## Structure

### Entry points

| Command | Reads | Writes |
|---|---|---|
| `python run_bench.py` | `.env` (via `src/config.py`), `data/prompts.jsonl`, Ollama at `OLLAMA_HOST` | `results/bench_<sha8>.json`, `docs/results.md`, console table |
| `python -m src.report results/bench_<sha8>.json` | a stored results file | `docs/results.md` (no Ollama needed) |
| `python -m pytest -q` | `tests/` (no Ollama, no network) | nothing outside temp dirs |

### Run flow

```
python run_bench.py
└─ run_bench.py:main
   ├─ src/bench/provenance.py:check_provenance         git commit + clean-tree guard (refuses unless --allow-dirty)
   ├─ src/bench/benchmark.py:load_prompts              reads data/prompts.jsonl
   ├─ src/bench/benchmark.py:run_single                one streamed POST to Ollama /api/generate -> BenchmarkRun
   │                                                    (repeated for every model x prompt x RUNS_PER_CELL)
   ├─ src/bench/cost.py:build_cost_profile             mean tok/s per model -> CostProfile
   ├─ src/bench/results_writer.py:build_results_payload
   │  └─ src/bench/results_writer.py:build_aggregates  median TTFT, median tok/s, p95 total per (model, prompt class)
   ├─ run_bench.py:print_summary                       console table from the payload's aggregates
   ├─ src/bench/results_writer.py:write_results_json   -> results/bench_<sha8>.json
   └─ src/report.py:write_report                       -> docs/results.md (renders the same payload)
```

### Code map

| File | Responsibility |
|---|---|
| `run_bench.py` | Entry point: parse flags, run the benchmark loop, write the results |
| `src/config.py` | `settings` read from `.env`: Ollama host, models, runs per cell, hardware label |
| `src/schema.py` | `BenchmarkRun` (one request) and `CostProfile` (cost model for one model) |
| `src/bench/benchmark.py` | `load_prompts`, `run_single`: stream one request and time it |
| `src/bench/cost.py` | `build_cost_profile`: capacity, local vs API $/1M tokens, break-even |
| `src/bench/provenance.py` | `check_provenance`: record the git commit, refuse a dirty tree |
| `src/bench/results_writer.py` | Aggregates (median / p95), the results payload, `results/bench_<sha8>.json` |
| `src/report.py` | Render `docs/results.md` from a results payload; `python -m src.report` |
| `src/__init__.py`, `src/bench/__init__.py` | Empty package markers |
| `data/prompts.jsonl` | 6 Arabic prompts: 2 short, 2 medium, 2 long |
| `results/bench_f6042d92.json` | Raw per-request data, aggregates and cost inputs of the published run |
| `docs/results.md` | Generated report (do not edit by hand) |
| `docs/DESIGN.md` | Why the metrics and the cost model are built this way |
| `docs/cto-memo.md` | Decision memo for leadership (Arabic) |
| `tests/test_benchmark.py` | `run_single` timing and parsing against a fake stream |
| `tests/test_config.py` | `.env` parsing |
| `tests/test_cost.py` | Break-even, capacity and per-1M pricing |
| `tests/test_provenance.py` | Refusal rules, with `subprocess.run` faked |
| `tests/test_results_writer.py` | Median / p95 aggregation, payload fields, JSON writing |
| `tests/test_report.py` | Report rendering, including the published run's medians |
| `tests/__init__.py` | Empty package marker |
| `requirements.txt` | Runtime dependencies (httpx, rich, python-dotenv) and pytest |
| `requirements-ci.txt` | Test-only dependencies used by CI |
| `.github/workflows/tests.yml` | CI: run the test suite on every push and pull request |
| `.env.example` | Template for `.env` |
| `.gitattributes`, `.gitignore`, `LICENSE` | Repository housekeeping |

### Read the code in this order

1. `run_bench.py` — the whole run in one function.
2. `src/bench/benchmark.py:run_single` — what is measured and how.
3. `src/bench/results_writer.py` — how runs become medians / p95 and the JSON file.
4. `src/bench/cost.py` — the break-even arithmetic.
5. `src/report.py` — how the JSON becomes `docs/results.md`.
6. `src/bench/provenance.py` — why a run refuses to start on a dirty tree.

## Architecture

- **One source of truth per run.** Everything a run produces is first assembled into
  one payload dict (per-request rows, aggregates, cost profiles, git commit, hardware).
  That payload is written as `results/bench_<sha8>.json`; the console table and
  `docs/results.md` are rendered from it, so all three show the same numbers.
- **One aggregation.** Per (model, prompt class) cell: median TTFT, median tok/s, p95
  total latency, over successful runs. Medians, because the first request of each model
  includes loading it.
- **Provenance before measurement.** A run records the commit it ran on and refuses to
  start on an uncommitted tree, so every results file maps to exact code.
- **Model-free tests.** HTTP, git and the clock are faked; the suite needs no Ollama.

Design rationale: [`docs/DESIGN.md`](docs/DESIGN.md).

## Run

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1   macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env          # edit BENCH_MODELS if needed

ollama pull gemma3:4b
ollama pull qwen2.5-coder:3b

python run_bench.py           # benchmark -> results/bench_<sha8>.json + docs/results.md
```

Flags:

```bash
python run_bench.py --model gemma3:4b    # override BENCH_MODELS, repeatable
python run_bench.py --allow-dirty        # run despite uncommitted changes / no git repo
```

By default the run refuses to start unless it is inside a git repository
with a clean worktree (`git status --porcelain` empty), so every results
file can be traced back to the exact code that produced it.

> Windows: use `127.0.0.1`, not `localhost`, in `OLLAMA_HOST` — `localhost`
> can resolve to IPv6 `::1` and hang against a IPv4-only Ollama listener.

## Eval

There is no model-quality eval here — this project measures serving cost
and latency, not output correctness. What is measured, per (model, prompt)
pair, streamed from Ollama's `/api/generate`:

- **TTFT** (Time To First Token) — latency the user feels before anything
  appears.
- **tokens/sec** — output tokens / total request time. The total **includes the
  time to first token** (and model loading on a cold first request), so this is
  end-to-end throughput for one request, not decode-only throughput.
- **P95 total latency** — the tail, not just the typical request.

Each cell (model × prompt class) is run `RUNS_PER_CELL` times (from `.env`).
Streaming is what makes TTFT observable at all — without it only total
latency is visible.

## Results

Measured at commit `f6042d92` on a clean tree — raw file
[`results/bench_f6042d92.json`](results/bench_f6042d92.json).
24 streamed requests: 2 models × 6 Arabic prompts × 2 repetitions, no warm-up.
Hardware: Windows 11, 15.9 GB RAM, NVIDIA GTX 1050 Ti 4 GB (Ollama GPU offload).

| model | prompt class | runs | median TTFT ms | median tok/s | p95 total ms |
|---|---|---:|---:|---:|---:|
| `gemma3:4b` | short | 4/4 | 1,191 | 9.52 | 24,879 |
| `gemma3:4b` | medium | 4/4 | 845 | 10.14 | 30,112 |
| `gemma3:4b` | long | 4/4 | 982 | 9.73 | 30,883 |
| `qwen2.5-coder:3b` | short | 4/4 | 372 | 8.91 | 21,693 |
| `qwen2.5-coder:3b` | medium | 4/4 | 395 | 8.64 | 34,901 |
| `qwen2.5-coder:3b` | long | 4/4 | 578 | 8.32 | 36,180 |

**Cost.** At the measured mean throughput (9.77 and 8.37 tok/s), running 24/7 produces
~22–25M tokens/month. The break-even against illustrative hosted pricing ($0.15 / $0.60
per 1M input / output tokens) and an assumed ~$50/month server is ~119M tokens/month —
**not reachable on this hardware**; a local token costs about 4.7–5.5× the hosted price
($1.97 / $2.31 vs $0.42 per 1M) under these assumptions. Local serving on this class of machine is justified by data residency
or offline operation, not by cost.

Full report — cost table and every request: [`docs/results.md`](docs/results.md).

## Limitations

- **One machine, two small models.** Everything in `docs/results.md` comes
  from a single laptop (i7-8750H, 15.9 GB RAM, NVIDIA GTX 1050 Ti 4 GB,
  Windows 11) running `gemma3:4b` and `qwen2.5-coder:3b` through Ollama. Ollama does offload part of
  the model into the GPU, but how much VRAM was used for a given run was not
  logged, so CPU and GPU contributions cannot be separated from these
  numbers.
- **The cost model's local-server assumptions are hypothetical.** The
  $50/month local-server figure in `src/bench/cost.py` describes an assumed
  deployment target, not the machine the benchmark ran on — see the comment
  block at the top of that file and `docs/DESIGN.md`.
- **API pricing is a point-in-time input**, not a live lookup; change it as
  pricing changes.
- **No concurrency test.** Every run in this project is single-request;
  serving many requests concurrently would change both TTFT and tok/s.

## What this project does not prove

- That a GPU-equipped server would (or would not) change the recommendation
  in `docs/cto-memo.md` — no GPU server was benchmarked, only this laptop.
- That two 3–4B models are representative of other sizes or architectures.
- That the break-even token volume holds for a different API price, a
  different local-hardware cost, or a different workload mix — the formula
  in `src/bench/cost.py` is linear in both, so it is easy to recompute, but
  the shipped number is only valid for the stated inputs.
- Output quality, correctness, or suitability of either model for any given
  task — this project only measures serving latency/throughput/cost.

## Reproduction

Rebuild `docs/results.md` from the published raw data (no Ollama needed):

```bash
python -m src.report results/bench_f6042d92.json   # standard library only
```

Re-measure on your own machine (needs Ollama and the two models, see [Run](#run)):

```bash
python run_bench.py
```

This writes a new `results/bench_<sha8>.json` keyed by the current commit — every
per-request measurement, the aggregates, the models, Ollama host, hardware string,
timestamp and git commit — and regenerates `docs/results.md` from it.

Run the test suite (no Ollama or network required):

```bash
python -m pip install -r requirements-ci.txt
python -m pytest -q
```

## Tech

| Layer | Choice | Why |
|-------|--------|-----|
| HTTP | `httpx` streaming | Streaming is what exposes the first-token moment |
| LLM | Ollama `/api/generate` | Native streaming endpoint; reports `eval_count` per request |
| Reporting | Markdown tables | Renderable on GitHub without deps |
| Cost model | Break-even formula | Simple, self-contained, easy to adjust |
