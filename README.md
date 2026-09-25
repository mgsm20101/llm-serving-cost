# LLM Serving Cost

Profile local LLM inference and compare it to Cloud API pricing — so a
deployment decision is based on measurements, not guesses.

## Problem

Every LLM deployment reaches the same question: when does on-prem become
cheaper than API? And what exactly is the cost of running a model
yourself — TTFT, throughput, tail latency? This project builds the
measurement layer to answer those questions.

## Architecture

```
run_bench.py
    │
    ├─ src/bench/benchmark.py    # stream one generation → BenchmarkRun (TTFT, tok/s, total_ms)
    ├─ src/bench/cost.py         # build_cost_profile → break-even token volume
    ├─ src/bench/provenance.py   # git commit / dirty-tree refusal guard
    ├─ src/bench/results_writer.py # raw per-request JSON → results/bench_<sha8>.json
    └─ src/report/generate.py    # write docs/results.md
         │
         └─▶ Ollama /api/generate (streaming)
                 └─▶ gemma3:4b · qwen2.5-coder:3b

src/schema.py      BenchmarkRun · BenchmarkSummary · CostProfile
src/config.py      settings from .env
data/prompts.jsonl short / medium / long Arabic prompts
docs/results.md    generated report
docs/cto-memo.md   cost/latency trade-off analysis for leadership
docs/DESIGN.md     design rationale
tests/             deterministic, model-free unit tests
```

## Run

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1   macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env          # edit BENCH_MODELS if needed

ollama pull gemma3:4b
ollama pull qwen2.5-coder:3b

python run_bench.py           # benchmark → docs/results.md + results/bench_<sha8>.json
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
- **tokens/sec** — sustained decode throughput after the first token.
- **P95 total latency** — the tail, not just the average.

Each cell (model × prompt class) is run `RUNS_PER_CELL` times (from `.env`).
Streaming is what makes TTFT observable at all — without it only total
latency is visible. See `docs/DESIGN.md` for the full rationale.

## Results

Measured at commit `f6042d92` on a clean tree — raw file
[`results/bench_f6042d92.json`](results/bench_f6042d92.json) (every request, the aggregates, and the cost inputs).
24 streamed requests: 2 models × 6 Arabic prompts × 2 repetitions,
no warm-up (the first request of each model includes loading it, which is why medians are
reported). Hardware: Windows 11, 15.9 GB RAM, NVIDIA GTX 1050 Ti 4 GB (Ollama GPU offload).

| model | prompt class | runs | median TTFT ms | median tok/s | p95 total ms |
|---|---|---:|---:|---:|---:|
| `gemma3:4b` | short | 4/4 | 1,191 | 9.52 | 24,879 |
| `gemma3:4b` | medium | 4/4 | 845 | 10.14 | 30,112 |
| `gemma3:4b` | long | 4/4 | 982 | 9.73 | 30,883 |
| `qwen2.5-coder:3b` | short | 4/4 | 372 | 8.91 | 21,693 |
| `qwen2.5-coder:3b` | medium | 4/4 | 395 | 8.64 | 34,901 |
| `qwen2.5-coder:3b` | long | 4/4 | 578 | 8.32 | 36,180 |

**Latency.** Once a model is loaded, the first token arrives in under 1.2 s for every prompt
class, and decoding runs at about 8–10 tokens/s. The p95 totals (22–36 s) are dominated by
generating up to 300 tokens at that rate, not by waiting for the first one.

**Cost.** A fixed ~$50/month server is compared with illustrative hosted pricing of $0.15 /
$0.60 per 1M input / output tokens. Both prices are inputs, not measurements; the throughput is
measured.

| model | mean tok/s | capacity, tok/month (24/7) | local $/1M tok | API $/1M tok | break-even tok/month | reachable |
|---|---:|---:|---:|---:|---:|:---:|
| `gemma3:4b` | 9.77 | 25,321,680 | $1.97 | $0.42 | 119,047,619 | no |
| `qwen2.5-coder:3b` | 8.37 | 21,686,400 | $2.31 | $0.42 | 119,047,619 | no |

The break-even (~119M tokens/month) is **beyond what this hardware can produce** even running
24/7 (~22–25M). At the measured throughput a local token costs about 4.7× the hosted price
under these assumptions. Local serving on this class of machine is justified by data residency
or offline operation, not by cost — and a cost case would need a benchmark on the actual target
server, where throughput, and so capacity, would be different.


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

```bash
git clone <this-repo>
cd llm-serving-cost
python -m venv .venv && source .venv/bin/activate   # or .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env
ollama pull gemma3:4b
ollama pull qwen2.5-coder:3b
python run_bench.py
```

This regenerates `docs/results.md` and writes a new
`results/bench_<sha8>.json` containing every per-request measurement,
aggregates, the model, Ollama host, hardware string, timestamp, and the
git commit the run was produced from. Run the test suite (no Ollama or
network required) with:

```bash
python -m pip install -r requirements-ci.txt
python -m pytest -q
```

## Tech

| Layer | Choice | Why |
|-------|--------|-----|
| HTTP | `httpx` streaming | Only way to measure TTFT accurately |
| LLM | Ollama `/api/generate` | OpenAI-compatible, supports streaming |
| Reporting | Markdown tables | Renderable on GitHub without deps |
| Cost model | Break-even formula | Simple, self-contained, easy to adjust |

## Layout

```
data/prompts.jsonl          6 Arabic prompts (short / medium / long)
src/
  schema.py                 BenchmarkRun, BenchmarkSummary, CostProfile
  config.py                 settings from env
  bench/
    benchmark.py            streaming benchmark runner
    cost.py                 cost model + break-even
    provenance.py           git commit / dirty-tree refusal guard
    results_writer.py       raw JSON provenance file writer
  report/
    generate.py             Markdown report writer
tests/                      deterministic, model-free unit tests
run_bench.py                entry point
docs/
  results.md                generated benchmark table
  cto-memo.md               cost/perf analysis memo
  DESIGN.md                 design decisions
```
