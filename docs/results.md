# LLM Serving Cost — Benchmark Results

Generated from `results/bench_<sha8>.json` by `src/report.py`.

Source commit: `f6042d92c7cf62d9e65e2eefaf8b84749dff1132` · worktree clean: True · Total runs: 24 · Models: gemma3:4b, qwen2.5-coder:3b

## Latency & Throughput

Medians over successful runs; p95 over successful runs' total time. tok/s = output tokens / total request time, including time to first token.

| Model | Prompt class | Runs ok | Median TTFT (ms) | Median tok/s | P95 total (ms) |
|---|---|---:|---:|---:|---:|
| `gemma3:4b` | short | 4/4 | 1,191 | 9.52 | 24,879 |
| `gemma3:4b` | medium | 4/4 | 845 | 10.14 | 30,112 |
| `gemma3:4b` | long | 4/4 | 982 | 9.73 | 30,883 |
| `qwen2.5-coder:3b` | short | 4/4 | 372 | 8.91 | 21,693 |
| `qwen2.5-coder:3b` | medium | 4/4 | 395 | 8.64 | 34,901 |
| `qwen2.5-coder:3b` | long | 4/4 | 578 | 8.32 | 36,180 |

## Cost model (local server vs hosted API)

> Local: an assumed ~$50/month dedicated server (an input, not a measurement).
> API: illustrative hosted pricing, $0.15 input / $0.60 output per 1M tokens, blended 40/60.
> Capacity: mean tok/s over all successful runs of the model, running 24/7 for 30 days.

| Model | Mean tok/s | Capacity (tok/month) | Local $/1M tok | API $/1M tok | Break-even (tok/month) | Reachable |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| `gemma3:4b` | 9.77 | 25,321,680 | $1.97 | $0.42 | 119,047,619 | no |
| `qwen2.5-coder:3b` | 8.37 | 21,686,400 | $2.31 | $0.42 | 119,047,619 | no |

## Per-run Raw Data

| Model | Prompt | Class | TTFT (ms) | Total (ms) | tok/s | Output tok | Error |
|-------|--------|-------|:---:|:---:|:---:|:---:|:---:|
| `gemma3:4b` | short-1 | short | 19562.3 | 41513.7 | 7.23 | 300 |  |
| `gemma3:4b` | short-1 | short | 721.7 | 24879.4 | 12.06 | 300 |  |
| `gemma3:4b` | short-2 | short | 1135.7 | 6720.9 | 10.27 | 69 |  |
| `gemma3:4b` | short-2 | short | 1246.3 | 8553.3 | 8.77 | 75 |  |
| `gemma3:4b` | medium-1 | medium | 2115.2 | 29070.2 | 10.32 | 300 |  |
| `gemma3:4b` | medium-1 | medium | 829.9 | 28541.6 | 10.51 | 300 |  |
| `gemma3:4b` | medium-2 | medium | 859.6 | 30112.0 | 9.96 | 300 |  |
| `gemma3:4b` | medium-2 | medium | 717.7 | 32764.0 | 9.16 | 300 |  |
| `gemma3:4b` | long-1 | long | 1661.7 | 31377.9 | 9.56 | 300 |  |
| `gemma3:4b` | long-1 | long | 731.3 | 30882.9 | 9.71 | 300 |  |
| `gemma3:4b` | long-2 | long | 1205.0 | 30774.4 | 9.75 | 300 |  |
| `gemma3:4b` | long-2 | long | 758.1 | 30203.0 | 9.93 | 300 |  |
| `qwen2.5-coder:3b` | short-1 | short | 10543.1 | 21693.2 | 5.3 | 115 |  |
| `qwen2.5-coder:3b` | short-1 | short | 288.1 | 29455.4 | 9.64 | 284 |  |
| `qwen2.5-coder:3b` | short-2 | short | 448.0 | 11379.5 | 9.05 | 103 |  |
| `qwen2.5-coder:3b` | short-2 | short | 295.5 | 8327.9 | 8.77 | 73 |  |
| `qwen2.5-coder:3b` | medium-1 | medium | 439.9 | 34900.8 | 8.6 | 300 |  |
| `qwen2.5-coder:3b` | medium-1 | medium | 356.9 | 34932.3 | 8.59 | 300 |  |
| `qwen2.5-coder:3b` | medium-2 | medium | 433.4 | 34527.9 | 8.69 | 300 |  |
| `qwen2.5-coder:3b` | medium-2 | medium | 286.7 | 34289.0 | 8.75 | 300 |  |
| `qwen2.5-coder:3b` | long-1 | long | 806.1 | 35684.4 | 8.41 | 300 |  |
| `qwen2.5-coder:3b` | long-1 | long | 286.4 | 35948.2 | 8.35 | 300 |  |
| `qwen2.5-coder:3b` | long-2 | long | 891.7 | 36179.9 | 8.29 | 300 |  |
| `qwen2.5-coder:3b` | long-2 | long | 349.1 | 37685.2 | 7.96 | 300 |  |
