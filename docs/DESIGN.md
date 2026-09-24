# Design — LLM Serving Cost Profiler

## Why this project

Every LLM deployment question eventually becomes a cost question: on-prem vs API,
quantized vs full-precision, batch vs streaming. This project builds the measurement
layer to answer those questions from data, not assumptions.

## What we measure and why

**TTFT (Time To First Token)** — the latency the user *feels*. A slow TTFT means
the user waits for nothing while the model is still prefilling. Critical for
interactive applications; less relevant for batch jobs.

**tokens/sec** — the sustained generation rate after the first token. Determines
throughput: how many requests can be served concurrently, and how much the model
costs at volume.

**Why streaming?** Ollama's streaming API emits each token as it is generated.
Without streaming we only see total latency — TTFT is invisible. Streaming is the
only way to separate prefill (TTFT) from decode (tok/s) without instrumenting the
model internals.

**P95 total latency** — the tail. Averages are optimistic; P95 shows what the
occasional slow request looks like. A stable model has P95/avg close to 1; a model
with cold-start jitter has P95 much higher than avg.

## Cost model design

The cost model has three inputs:
1. `avg_tokens_per_sec` — from our benchmark
2. `LOCAL_SERVER_COST_PER_MONTH_USD` — hardware cost amortised
3. `api_cost_per_1k` — current API pricing

From these, we derive the break-even point: the monthly token volume above which
local serving is cheaper than API. The model is deliberately simple — its value is
the *methodology*, not the exact number. Real deployments need to add:
- GPU purchase/cloud lease costs (no GPU server was benchmarked here)
- Staff time for ops and maintenance
- Reliability/availability differences

## Why no GPU server in this project

No GPU *server* was available to benchmark, so the measurement is a laptop running
Ollama. It is worth being exact about what that means, because an earlier version of
this file said "the benchmark machine is CPU-only" and that was false: the box has a
GTX 1050 Ti (4 GB) and Ollama offloads into it. What is true is that the run did not
record how much of the model was resident in VRAM, so no split between CPU and GPU work
can be claimed from it.

That makes these numbers a floor rather than a clean CPU baseline — good enough to make
the cost model conservative (the API looks more competitive than it would against a
real GPU server), and not good enough to publish as a CPU-vs-GPU comparison. The
methodology is unchanged; swap the hardware, log the GPU share, and re-run
`python run_bench.py`.

## Streaming implementation details

We use `httpx` streaming to read Ollama's `/api/generate` line by line. Each line
is a JSON object with a `response` field (one token) and a final `done:true` chunk
that includes `eval_count` (total output tokens, authoritative from Ollama).

TTFT is the time from request start to the first non-empty `response` field.
Total latency is from request start to `done:true`. tokens/sec is
`eval_count / (total_ms / 1000)`.
