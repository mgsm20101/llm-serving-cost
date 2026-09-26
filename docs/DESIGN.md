# Design — LLM Serving Cost Profiler

The README says what is measured, how to run it and what came out. This file
records why the measurement and the cost model are built the way they are.

## How each metric is computed

`src/bench/benchmark.py:run_single` streams Ollama's `/api/generate` line by line.
Each line is a JSON object with a `response` field (a piece of output) and a final
`done: true` chunk that carries `eval_count`, Ollama's own count of output tokens.

- **TTFT** — request start to the first non-empty `response`.
- **Total** — request start to `done: true`.
- **tokens/sec** — `eval_count / (total_ms / 1000)`. The denominator is the whole
  request, so it **includes the time to first token** (prompt processing, and model
  loading on a cold first request). It is not decode-only throughput; it is the rate a
  caller sees end to end. That is why the first request of each model shows a lower
  tok/s (7.23 and 5.30 in `docs/results.md`) than the ones after it.

**Why streaming?** Without streaming only the total latency is visible. Streaming is
what makes the first-token moment observable without instrumenting the model.

## Why medians and p95, and no warm-up

No warm-up requests are sent; every request is recorded (see `warmup_protocol` in the
results JSON). The first request per model includes loading it, so a mean would be
dominated by that one cold start (19.6 s TTFT for `gemma3:4b short-1`). Per-cell
aggregates are therefore the median for TTFT and tok/s and the p95 for total latency.
They are computed once, in `src/bench/results_writer.py:build_aggregates`, and the
console table and `docs/results.md` both render those stored aggregates.

## Cost model design

The cost model (`src/bench/cost.py:build_cost_profile`) has three inputs:
1. the model's **mean** tok/s over all successful runs — measured
2. `LOCAL_SERVER_COST_PER_MONTH_USD` — an assumed fixed monthly cost
3. API input/output prices **per 1M tokens** — the unit vendors publish

From these it derives the break-even volume (tokens/month above which a fixed-cost
server beats per-token pricing) and the capacity (tokens/month the measured
throughput produces running 24/7). The break-even only matters if capacity reaches it;
the report says so per model. Because tok/s includes time to first token, capacity is
the rate for back-to-back single requests, not a decode-only upper bound.

An earlier version took the per-1M price as a per-1k price, which put the break-even
1000× too low (about 119 thousand tokens/month instead of about 119 million). The unit
is now in every parameter name and pinned by a test. The model is deliberately simple;
a real deployment would add GPU purchase or lease cost, staff time for operations, and
reliability differences.

## Hardware: a laptop, not a GPU server

No GPU server was available, so the measurement is a laptop running Ollama. An
earlier version of this file called the machine CPU-only; that was false — it has a
GTX 1050 Ti (4 GB) and Ollama offloads into it. The run did not record how much of the
model was resident in VRAM, so no CPU/GPU split can be claimed. The numbers are a floor
for the cost model (the API looks more competitive than it would against a real GPU
server), not a CPU-vs-GPU comparison.
