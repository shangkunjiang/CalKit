"""
Free Energy Analyzer for VASP OUTCAR files.

Extracts free energy (energy without entropy) and related energy
values from VASP OUTCAR output.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseAnalyzer


class FreeEnergyAnalyzer(BaseAnalyzer):
    """Analyze free energy from an OUTCAR file."""

    def __init__(self) -> None:
        super().__init__()
        self.outcar: Optional[Path] = None
        self._values: Dict[str, float] = {}
        self._steps: int = 0

    # ── Public API ─────────────────────────────────────────────

    def run(self, outcar_path: str = "", directory: str = ".") -> None:
        p = self._resolve(outcar_path or "OUTCAR", directory)
        if not self._check_file(p, "OUTCAR"):
            return

        self.outcar = p
        self._parse(p.read_text().splitlines())
        self._ran = True

    def print_summary(self) -> None:
        if not self._ran:
            print("Run analysis first.")
            return
        print(f"\n{'─' * 50}")
        print("  Free Energy Analysis")
        print(f"{'─' * 50}")
        for key, val in self._values.items():
            print(f"  {key:<35} {val:>14.8f} eV")
        print(f"  {'Ionic steps':<35} {self._steps:>14}")
        print(f"{'─' * 50}\n")

    def to_file(self, output: str) -> None:
        """Write free energy values to a text file."""
        with open(output, "w") as f:
            for key, val in self._values.items():
                f.write(f"{key}: {val:.8f} eV\n")
            f.write(f"Ionic steps: {self._steps}\n")

    # ── Parsing ────────────────────────────────────────────────

    def _parse(self, lines: list) -> None:
        for line in lines:
            if "FREE ENERGIE OF THE ION-ELECTRON SYSTEM" in line:
                self._steps += 1
                parts = line.split()
                # energy  without entropy=  -42.12345678
                for i, w in enumerate(parts):
                    if "energy" in w and i + 1 < len(parts):
                        try:
                            self._values["energy_without_entropy"] = float(parts[i + 1])
                        except ValueError:
                            pass
                    if "entropy" in w and i + 1 < len(parts):
                        try:
                            self._values["energy_entropy"] = float(parts[i + 1])
                        except ValueError:
                            pass

            if "energy  without entropy" in line:
                v = self._float_after(line, "=")
                if v is not None:
                    self._values["energy_without_entropy"] = v

            if "energy(sigma->0)" in line:
                v = self._float_after(line, "=")
                if v is not None:
                    self._values["energy_sigma0"] = v

            if "TOTEN" in line and "energy" in line.lower():
                v = self._float_at(line, -1)
                if v is not None:
                    self._values["toten"] = v

    @property
    def values(self) -> Dict[str, float]:
        return self._values.copy()

    @property
    def steps(self) -> int:
        return self._steps