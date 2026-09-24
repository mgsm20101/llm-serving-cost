"""Tests for env-driven config parsing in src/config.py."""

from __future__ import annotations

import importlib

import src.config as config_module


def _reload_settings_with_env(monkeypatch, **env):
    for key in ["OLLAMA_HOST", "BENCH_MODELS", "RUNS_PER_CELL", "BENCH_HARDWARE"]:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.reload(config_module)


def test_models_splits_and_strips_comma_separated_list(monkeypatch):
    mod = _reload_settings_with_env(monkeypatch, BENCH_MODELS=" qwen3:4b , qwen2.5:7b-instruct ")
    assert mod.settings.models == ["qwen3:4b", "qwen2.5:7b-instruct"]


def test_models_defaults_when_env_unset(monkeypatch):
    mod = _reload_settings_with_env(monkeypatch)
    assert mod.settings.models == ["gemma3:4b", "qwen2.5-coder:3b"]


def test_runs_per_cell_reads_int_from_env(monkeypatch):
    mod = _reload_settings_with_env(monkeypatch, RUNS_PER_CELL="5")
    assert mod.settings.runs_per_cell == 5


def test_empty_models_entries_are_dropped(monkeypatch):
    mod = _reload_settings_with_env(monkeypatch, BENCH_MODELS="qwen3:4b,,  ,")
    assert mod.settings.models == ["qwen3:4b"]


def test_ollama_host_and_hardware_from_env(monkeypatch):
    mod = _reload_settings_with_env(
        monkeypatch,
        OLLAMA_HOST="http://10.0.0.5:11434",
        BENCH_HARDWARE="test-rig",
    )
    assert mod.settings.ollama_host == "http://10.0.0.5:11434"
    assert mod.settings.hardware == "test-rig"
