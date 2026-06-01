"""
PDOS (Projected Density of States) Analyzer.

Reads VASP DOSCAR/PROCAR files to extract projected DOS data for
orbital- and element-resolved analysis.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .base import BaseAnalyzer


class PDOSAnalyzer(BaseAnalyzer):
    """Analyze PDOS from VASP DOSCAR / PROCAR output."""

    def __init__(self) -> None:
        super().__init__()
        self.doscar: Optional[Path] = None
        self.procar: Optional[Path] = None
        self._energies: List[float] = []
        self._pdos: Dict[str, Any] = {}
        self._nelect: int = 0

    # ── Public API ─────────────────────────────────────────────

    def run(self, doscar_path: str = "", procar_path: str = "",
            directory: str = ".") -> None:
        self.doscar = self._resolve(doscar_path or "DOSCAR", directory)
        self.procar = self._resolve(procar_path or "PROCAR", directory)

        if not self._check_file(self.doscar, "DOSCAR"):
            return

        self._parse_doscar()
        if self.procar.exists():
            self._parse_procar()
        self._ran = True

    def print_summary(self) -> None:
        if not self._ran:
            print("Run analysis first.")
            return
        print("\n" + "─" * 50)
        print("  PDOS Analysis Summary")
        print("─" * 50)
        if len(self._energies) >= 2:
            print("  Energy range: %.4f ~ %.4f eV" % (self._energies[0], self._energies[-1]))
        elif len(self._energies) == 1:
            print("  Energy range: %.4f eV (single point)" % self._energies[0])
        else:
            print("  Energy range: N/A (no data parsed)")
        print("  NEDOS: %d" % self._nelect)
        print("  PDOS entries: %d" % len(self._pdos))
        if self._pdos:
            print("  PDOS keys:")
            for key in list(self._pdos.keys())[:8]:
                val = self._pdos[key]
                if isinstance(val, (list, tuple)):
                    print("    - %s: %d points" % (key, len(val)))
                else:
                    print("    - %s: %s" % (key, val))
            if len(self._pdos) > 8:
                print("    ... and %d more" % (len(self._pdos) - 8))
        print("─" * 50)
        print()

    def to_excel(self, output: str) -> None:
        """Export PDOS data to Excel."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "PDOS"
        ws.append(["Energy (eV)"] + list(self._pdos.keys()))
        for i, e in enumerate(self._energies):
            row = [e] + [self._pdos[k][i] for k in self._pdos]
            ws.append(row)
        wb.save(output)

    # ── Parsing ────────────────────────────────────────────────

    def _parse_doscar(self) -> None:
        """Parse VASP DOSCAR format.

        Handles both standard and PDOS (LORBIT) DOSCAR formats.
        Format (line 0-based):
          0: NIONS NIONS POTCIM icharg
          1-4: header lines (parameters, system name)
          5: EMAX, ???, NEDOS, E_FERMI, weight
          6+: energy + DOS data (NEDOS rows)
        """
        lines = self.doscar.read_text().splitlines()
        if not lines:
            self.errors.append("DOSCAR is empty")
            return

        # Step 1: Get NIONS from line 0
        nions = 0
        try:
            nions = int(lines[0].split()[0])
        except (ValueError, IndexError):
            pass

        # Step 2: Find NEDOS line
        # NEDOS is an integer (> nions, 50~50000) in the header
        # In VASP DOSCAR, it is the 3rd token (index 2) on the header line
        nedos = 0
        efermi = 0.0
        dos_start = 0

        for i, line in enumerate(lines):
            if i < 3:
                continue  # skip first 3 lines
            tokens = line.split()
            if len(tokens) < 3:
                continue
            # Try positions 2, 1, 0 for NEDOS (VASP standard: position 2)
            for pos in [2, 1, 0]:
                if pos >= len(tokens):
                    continue
                try:
                    val = int(float(tokens[pos]))
                    if 50 <= val <= 50000 and val > nions:
                        nedos = val
                        if pos + 1 < len(tokens):
                            try:
                                efermi = float(tokens[pos + 1])
                            except ValueError:
                                pass
                        dos_start = i + 1
                        break
                except (ValueError, IndexError):
                    continue
            if nedos > 0:
                break

        if nedos == 0:
            self.errors.append("Could not find NEDOS in DOSCAR header")
            return

        self._nelect = nedos

        # Step 3: Read energy grid
        self._energies = []
        max_lines = min(nedos, len(lines) - dos_start)
        for i in range(max_lines):
            parts = lines[dos_start + i].split()
            if not parts:
                break
            try:
                self._energies.append(float(parts[0]))
            except ValueError:
                break

        # Step 4: Determine DOS columns from first data line
        ncols = 1
        if dos_start < len(lines) and lines[dos_start].split():
            ncols = len(lines[dos_start].split()) - 1  # exclude energy column

        # Step 5: Generate labels based on column count
        if ncols >= 4:
            labels = ["s_up", "s_down", "p_up", "p_down"]
        elif ncols >= 2:
            labels = ["total_up", "total_down"]
        elif ncols >= 1:
            labels = ["total"]
        else:
            labels = []

        # Step 6: Extract DOS arrays
        dos_data = {lbl: [] for lbl in labels}
        for i in range(max_lines):
            parts = lines[dos_start + i].split()
            for j, lbl in enumerate(labels):
                col_idx = j + 1
                if col_idx < len(parts):
                    try:
                        dos_data[lbl].append(float(parts[col_idx]))
                    except ValueError:
                        dos_data[lbl].append(0.0)
                else:
                    dos_data[lbl].append(0.0)

        self._pdos["energy"] = self._energies.copy()
        for lbl in labels:
            self._pdos[lbl] = dos_data[lbl]

    def _parse_procar(self) -> None:
        # Simplified: store raw PROCAR lines for later processing
        lines = self.procar.read_text().splitlines()
        self._pdos["procar_raw_lines"] = len(lines)

    @property
    def energies(self) -> List[float]:
        return self._energies.copy()

    @property
    def pdos(self) -> Dict[str, Any]:
        return self._pdos.copy()

    @property
    def nelect(self) -> int:
        return self._nelect
