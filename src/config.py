"""Configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    # Models to benchmark — comma-separated
    models_raw: str = os.getenv("BENCH_MODELS", "gemma3:4b,qwen2.5-coder:3b")
    # Runs per (model, prompt) pair — higher = more stable averages
    runs_per_cell: int = int(os.getenv("RUNS_PER_CELL", "2"))
    # Free-text description of the machine the benchmark runs on — recorded in
    # results/bench_<sha8>.json for provenance, not measured automatically.
    hardware: str = os.getenv(
        "BENCH_HARDWARE",
        "Windows 11, 15.9 GB RAM, NVIDIA GTX 1050 Ti 4 GB (Ollama GPU offload)",
    )

    @property
    def models(self) -> list[str]:
        return [m.strip() for m in self.models_raw.split(",") if m.strip()]


settings = Settings()
