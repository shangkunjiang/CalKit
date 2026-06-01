"""
Force Convergence Analyzer for VASP OUTCAR files.

Parses the force convergence status from VASP output and reports
whether forces converged, the number of ionic steps, and final forces.
"""

from pathlib import Path
from typing import Optional

from .base import BaseAnalyzer


class ForceConvergenceAnalyzer(BaseAnalyzer):
    """Analyze force convergence from an OUTCAR file."""

    def __init__(self) -> None:
        super().__init__()
        self.outcar: Optional[Path] = None
        self._steps: int = 0
        self._converged: bool = False
        self._ediffg: float = 0.0
        self._max_force: float = 0.0

    # ── Public API ─────────────────────────────────────────────

    def run(self, outcar_path: str = "", directory: str = ".") -> None:
        p = self._resolve(outcar_path or "OUTCAR", directory)
        if not self._check_file(p, "OUTCAR"):
            return

        self.outcar = p
        lines = p.read_text().splitlines()
        self._parse(lines)
        self._ran = True

    def print_summary(self) -> None:
        if not self._ran:
            print("Run analysis first.")
            return
        status = "CONVERGED" if self._converged else "NOT CONVERGED"
        print(f"\n{'─' * 40}")
        print("  Force Convergence Analysis")
        print(f"{'─' * 40}")
        print(f"  Steps:  {self._steps}")
        print(f"  EDIFFG: {self._ediffg:.6f}")
        print(f"  Status: {status}")
        print(f"  Max Force (last step): {self._max_force:.8f}")
        print(f"{'─' * 40}\n")

    # ── Parsing ────────────────────────────────────────────────

    def _parse(self, lines: list) -> None:
        ediffg_found = False

        for line in lines:
            # EDIFFG
            if not ediffg_found and "EDIFFG" in line:
                v = self._float_after(line, "=")
                if v is not None:
                    self._ediffg = abs(v)
                    ediffg_found = True

            # ionic step counter
            if "FREE ENERGIE OF THE ION-ELECTRON SYSTEM" in line:
                self._steps += 1

            # convergence message
            if "reached required accuracy" in line:
                self._converged = True

            # maximum force
            if "TOTAL-FORCE" in line:
                self._max_force = self._float_at(line, -1) or 0.0

    @property
    def steps(self) -> int:
        return self._steps

    @property
    def converged(self) -> bool:
        return self._converged

    @property
    def ediffg(self) -> float:
        return self._ediffg

    @property
    def max_force(self) -> float:
        return self._max_force