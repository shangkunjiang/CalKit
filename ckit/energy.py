"""
Energy Extractor for VASP OUTCAR files.

Extracts key energy values from the final ionic step.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseAnalyzer


class EnergyExtractor(BaseAnalyzer):
    """Extract energy values from the final ionic step of an OUTCAR file."""

    _KEYS = ("energy_without_entropy", "energy_sigma0", "toten")

    def __init__(self) -> None:
        super().__init__()
        self.outcar: Optional[Path] = None
        self._values: Dict[str, float] = {}

    # ── Public API ─────────────────────────────────────────────

    def run(self, outcar_path: str = "", directory: str = ".") -> None:
        p = self._resolve(outcar_path or "OUTCAR", directory)
        if not self._check_file(p, "OUTCAR"):
            return

        self.outcar = p
        lines = p.read_text().splitlines()
        self._values = {k: 0.0 for k in self._KEYS}

        for line in lines:
            if "energy  without entropy" in line:
                v = self._float_after(line, "=")
                if v is not None:
                    self._values["energy_without_entropy"] = v

            elif "energy(sigma->0)" in line:
                v = self._float_after(line, "=")
                if v is not None:
                    self._values["energy_sigma0"] = v

            elif "TOTEN" in line:
                v = self._float_at(line, -1)
                if v is not None:
                    self._values["toten"] = v

        self._ran = True

    def print_summary(self) -> None:
        if not self._ran:
            print("Run analysis first.")
            return
        print(f"\n{'─' * 45}")
        print("  VASP Energy Summary")
        print(f"{'─' * 45}")
        labels = {
            "energy_without_entropy": "energy  without entropy",
            "energy_sigma0": "energy(sigma->0)",
            "toten": "FREE ENERGIE TOTEN",
        }
        for key, label in labels.items():
            print(f"  {label:<32} {self._values[key]:>12.8f} eV")
        print(f"{'─' * 45}\n")

    def to_file(self, output: str) -> None:
        """Write energy values to a text file."""
        with open(output, "w") as f:
            for k, v in self._values.items():
                f.write(f"{k}: {v:.8f} eV\n")

    @property
    def values(self) -> Dict[str, float]:
        return self._values.copy()