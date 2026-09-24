# LLM Serving Cost — Benchmark Results

Total runs: 6 · Models: qwen3:4b

## Latency & Throughput

| Model | Prompt class | Avg TTFT (ms) | Avg tok/s | P95 total (ms) | Avg output tokens |
|-------|-------------|:---:|:---:|:---:|:---:|
| `qwen3:4b` | short | 75305.6 | 3.96 | 75625.2 | 300 |
| `qwen3:4b` | medium | 73498.5 | 4.09 | 71146.3 | 300 |
| `qwen3:4b` | long | 76656.9 | 3.92 | 73372.7 | 300 |

## Cost Model (Local CPU server vs Cloud API)

> Local: ~$50/month all-in (hardware amortised + power) for a dedicated CPU server.
> API: blended GPT-4o-mini pricing (40% input @ $0.15 + 60% output @ $0.60 per 1k tokens).

| Model | Avg tok/s | Local $/1k tok | API $/1k tok | Break-even (tok/month) |
|-------|:---:|:---:|:---:|:---:|
| `qwen3:4b` | 3.99 | $0.00483 | $0.4200 | 119,048 |

## Per-run Raw Data

| Model | Prompt | Class | TTFT (ms) | tok/s | Output tok | Error |
|-------|--------|-------|:---:|:---:|:---:|:---:|
| `qwen3:4b` | short-1 | short | 75625.2 | 3.97 | 300 |  |
| `qwen3:4b` | short-2 | short | 74986.0 | 3.96 | 300 |  |
| `qwen3:4b` | medium-1 | medium | 75850.7 | 3.96 | 300 |  |
| `qwen3:4b` | medium-2 | medium | 71146.3 | 4.22 | 300 |  |
| `qwen3:4b` | long-1 | long | 73372.7 | 4.09 | 300 |  |
| `qwen3:4b` | long-2 | long | 79941.1 | 3.75 | 300 |  |
