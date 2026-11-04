"""Load config/default.yaml, optionally overlaid with user overrides (e.g. from the web settings page)."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "default.yaml"


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict:
    out = copy.deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_config(path: str | Path | None = None, overrides: Mapping[str, Any] | None = None) -> dict:
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return deep_merge(cfg, overrides or {})


def resolve_path(cfg: Mapping[str, Any], key: str) -> Path:
    """Resolve a cfg['paths'][key] entry relative to the repo root."""
    p = Path(cfg["paths"][key])
    return p if p.is_absolute() else REPO_ROOT / p
