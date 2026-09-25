# LLM Serving Cost — Benchmark Results

Total runs: 24 · Models: gemma3:4b, qwen2.5-coder:3b

## Latency & Throughput

| Model | Prompt class | Avg TTFT (ms) | Avg tok/s | P95 total (ms) | Avg output tokens |
|-------|-------------|:---:|:---:|:---:|:---:|
| `gemma3:4b` | short | 5666.5 | 9.58 | 24879.4 | 186 |
| `gemma3:4b` | medium | 1130.6 | 9.99 | 30112.0 | 300 |
| `gemma3:4b` | long | 1089.0 | 9.74 | 30882.9 | 300 |
| `qwen2.5-coder:3b` | short | 2893.7 | 8.19 | 21693.2 | 144 |
| `qwen2.5-coder:3b` | medium | 379.2 | 8.66 | 34900.8 | 300 |
| `qwen2.5-coder:3b` | long | 583.3 | 8.25 | 36179.9 | 300 |

## Cost model (local server vs hosted API)

> Local: an assumed ~$50/month dedicated server (an input, not a measurement).
> API: illustrative hosted pricing, $0.15 input / $0.60 output per 1M tokens, blended 40/60.
> Capacity: measured tok/s running 24/7 for 30 days on the benchmark machine.

| Model | Avg tok/s | Capacity (tok/month) | Local $/1M tok | API $/1M tok | Break-even (tok/month) | Reachable |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| `gemma3:4b` | 9.77 | 25,321,680 | $1.97 | $0.42 | 119,047,619 | no |
| `qwen2.5-coder:3b` | 8.37 | 21,686,400 | $2.31 | $0.42 | 119,047,619 | no |

## Per-run Raw Data

| Model | Prompt | Class | TTFT (ms) | tok/s | Output tok | Error |
|-------|--------|-------|:---:|:---:|:---:|:---:|
| `gemma3:4b` | short-1 | short | 19562.3 | 7.23 | 300 |  |
| `gemma3:4b` | short-1 | short | 721.7 | 12.06 | 300 |  |
| `gemma3:4b` | short-2 | short | 1135.7 | 10.27 | 69 |  |
| `gemma3:4b` | short-2 | short | 1246.3 | 8.77 | 75 |  |
| `gemma3:4b` | medium-1 | medium | 2115.2 | 10.32 | 300 |  |
| `gemma3:4b` | medium-1 | medium | 829.9 | 10.51 | 300 |  |
| `gemma3:4b` | medium-2 | medium | 859.6 | 9.96 | 300 |  |
| `gemma3:4b` | medium-2 | medium | 717.7 | 9.16 | 300 |  |
| `gemma3:4b` | long-1 | long | 1661.7 | 9.56 | 300 |  |
| `gemma3:4b` | long-1 | long | 731.3 | 9.71 | 300 |  |
| `gemma3:4b` | long-2 | long | 1205.0 | 9.75 | 300 |  |
| `gemma3:4b` | long-2 | long | 758.1 | 9.93 | 300 |  |
| `qwen2.5-coder:3b` | short-1 | short | 10543.1 | 5.3 | 115 |  |
| `qwen2.5-coder:3b` | short-1 | short | 288.1 | 9.64 | 284 |  |
| `qwen2.5-coder:3b` | short-2 | short | 448.0 | 9.05 | 103 |  |
| `qwen2.5-coder:3b` | short-2 | short | 295.5 | 8.77 | 73 |  |
| `qwen2.5-coder:3b` | medium-1 | medium | 439.9 | 8.6 | 300 |  |
| `qwen2.5-coder:3b` | medium-1 | medium | 356.9 | 8.59 | 300 |  |
| `qwen2.5-coder:3b` | medium-2 | medium | 433.4 | 8.69 | 300 |  |
| `qwen2.5-coder:3b` | medium-2 | medium | 286.7 | 8.75 | 300 |  |
| `qwen2.5-coder:3b` | long-1 | long | 806.1 | 8.41 | 300 |  |
| `qwen2.5-coder:3b` | long-1 | long | 286.4 | 8.35 | 300 |  |
| `qwen2.5-coder:3b` | long-2 | long | 891.7 | 8.29 | 300 |  |
| `qwen2.5-coder:3b` | long-2 | long | 349.1 | 7.96 | 300 |  |
