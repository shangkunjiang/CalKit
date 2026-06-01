"""
Configuration manager for CalKit.

Reads/writes ~/.calkit/config.json and provides
typed accessors for all configurable paths and defaults.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG = {
    "paths": {
        "pseudopotential_dir": "",
        "bader_executable": "bader",
        "vaspkit_executable": "vaspkit",
        "default_output_dir": "",
    },
    "defaults": {
        "temperature": 298.15,
        "dpi": 150,
        "output_format": "excel",
        "pdos_pattern": "PDOS*.dat",
    },
    "ui": {
        "color_output": True,
        "show_banner": True,
    },
}


def _config_dir() -> Path:
    """Return the config directory (~/.calkit), ensure it exists."""
    d = Path.home() / ".calkit"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _config_path() -> Path:
    return _config_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    """Load config from ~/.calkit/config.json (auto-creates if missing)."""
    path = _config_path()
    if not path.exists():
        _write_json(path, DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Merge missing keys from default (deep merge for top-level sections)
    for section in DEFAULT_CONFIG:
        if section not in data:
            data[section] = dict(DEFAULT_CONFIG[section])
        elif isinstance(DEFAULT_CONFIG[section], dict):
            for key, val in DEFAULT_CONFIG[section].items():
                if key not in data[section]:
                    data[section][key] = val
    return data


def save_config(data: Dict[str, Any]) -> None:
    """Save config dict to ~/.calkit/config.json."""
    _write_json(_config_path(), data)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---- Typed accessors ----

def get_pseudo_dir() -> str:
    """Pseudopotential directory (e.g. /path/to/POTCAR_library)."""
    return load_config()["paths"].get("pseudopotential_dir", "")


def get_bader_exe() -> str:
    """Bader executable name or path."""
    return load_config()["paths"].get("bader_executable", "bader")


def get_vaspkit_exe() -> str:
    """Vaspkit executable name or path."""
    return load_config()["paths"].get("vaspkit_executable", "vaspkit")


def get_output_dir() -> str:
    """Default output directory (empty = current dir)."""
    return load_config()["paths"].get("default_output_dir", "")


def get_temperature() -> float:
    return load_config()["defaults"].get("temperature", 298.15)


def get_dpi() -> int:
    return load_config()["defaults"].get("dpi", 150)


def get_output_format() -> str:
    return load_config()["defaults"].get("output_format", "excel")


def get_pdos_pattern() -> str:
    return load_config()["defaults"].get("pdos_pattern", "PDOS*.dat")


def is_color_enabled() -> bool:
    return load_config()["ui"].get("color_output", True)


def interactive_config() -> None:
    """Interactive config editor (called by `calkit config`)."""
    cfg = load_config()

    print("\n" + "─" * 50)
    print("  CalKit Configuration Editor")
    print("─" * 50)

    fields = [
        ("paths", "pseudopotential_dir", "Pseudopotential directory", str),
        ("paths", "bader_executable",    "Bader executable path",     str),
        ("paths", "vaspkit_executable",  "Vaspkit executable path",   str),
        ("paths", "default_output_dir",  "Default output directory",  str),
        ("defaults", "temperature",      "Default temperature (K)",   float),
        ("defaults", "dpi",              "Plot DPI",                  int),
        ("defaults", "output_format",    "Output format (excel/csv)", str),
        ("defaults", "pdos_pattern",     "PDOS glob pattern",         str),
        ("ui", "color_output",          "Color output (true/false)",  None),
    ]

    for section, key, desc, cast in fields:
        current = cfg.get(section, {}).get(key, "")
        prompt = f"  {desc} [{current}]: "
        try:
            val = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if val:
            if cast == bool or (cast is None and key == "color_output"):
                cfg[section][key] = val.lower() in ("true", "1", "yes", "y")
            elif cast:
                try:
                    cfg[section][key] = cast(val)
                except ValueError:
                    print(f"  Invalid value, keeping '{current}'")
            else:
                cfg[section][key] = val

    save_config(cfg)
    print(f"\nConfiguration saved to {_config_path()}\n")
