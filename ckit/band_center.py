"""
Band Center Analyzer — VASPKIT 503 replica.

Calculates d-band center from PDOS data in DOSCAR.
Formula: epsilon_d = \int E * DOS(E) dE / \int DOS(E) dE
Integration range: from E_min to E_fermi (occupied states).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .base import BaseAnalyzer
# Reuse DOSCAR parser from PDOS module
from .pdos_analysis import PDOSAnalyzer


class BandCenterAnalyzer(BaseAnalyzer):
    """Calculate band center from DOSCAR (VASPKIT 503)."""

    def __init__(self) -> None:
        super().__init__()
        self._pdos = PDOSAnalyzer()
        self._results: List[Dict[str, Any]] = []

    # -- Public API -------------------------------------------------

    def run(self, doscar_path: str = "", directory: str = ".",
            atoms: str = "", orbitals: str = "d") -> None:
        """Run band center calculation."""
        self._pdos.doscar = self._resolve(doscar_path or "DOSCAR", directory)
        if not self._check_file(self._pdos.doscar, "DOSCAR"):
            return

        self._pdos._parse_doscar()

        if not atoms:
            self.errors.append("No atoms selected for band center")
            return

        self._compute_band_center(atoms, orbitals)
        self._ran = True

    def print_summary(self) -> None:
        if not self._ran:
            print("Run analysis first.")
            return
        sep = "-" * 50
        print("\n" + sep)
        print("  Band Center Analysis")
        print(sep)
        for r in self._results:
            print("  %-12s  %10.4f eV  (Fermi: %.4f)" %
                  (r["label"], r["center"], self._pdos._efermi))
        print(sep + "\n")

    def to_excel(self, output: str, selection: str = "Fe",
                 orbitals: str = "d") -> None:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BandCenter"
        ws.append(["Label", "Band_Center(eV)", "E_Fermi(eV)", "DOS_Integral"])
        for r in self._results:
            ws.append([r["label"], r["center"],
                       self._pdos._efermi, r["integral"]])
        wb.save(output)

    # -- Computation -----------------------------------------------

    def _compute_band_center(self, atoms: str, orbitals: str) -> None:
        """Calculate d-band center for selected atoms/orbitals.

        band_center = \int_{E_min}^{E_fermi} E * DOS(E) dE /
                      \int_{E_min}^{E_fermi} DOS(E) dE
        """
        pdos_data = self._pdos._extract_pdos(atoms, orbitals)
        if not pdos_data:
            self.errors.append("No PDOS data for %s %s orbitals" % (atoms, orbitals))
            return

        energies = np.array(self._pdos._energies)
        efermi = self._pdos._efermi

        for key, data in sorted(pdos_data.items()):
            # Sum spin-up + spin-down
            dos_up = np.array(data.get("up", []))
            dos_dn = np.array(data.get("dn", []))
            dos_total = dos_up + dos_dn

            if len(dos_total) == 0:
                continue

            # Integrate over occupied states (E <= 0 relative to Fermi)
            # energies are already aligned to E-fermi (E_fermi = 0)
            # So occupied states: E <= 0

            # Use all energies up to Fermi level
            mask = energies <= 0.0  # occupied states
            if not np.any(mask):
                # Fallback: use entire energy range
                mask = np.ones(len(energies), dtype=bool)

            e_occ = energies[mask]
            dos_occ = dos_total[mask]

            # Trapezoidal integration
            de = np.diff(e_occ)
            dos_mid = (dos_occ[:-1] + dos_occ[1:]) / 2.0

            numerator = np.sum(e_occ[:-1] * dos_mid * de)  # approximate
            denominator = np.sum(dos_mid * de)

            # More accurate: midpoint integration
            e_mid = (e_occ[:-1] + e_occ[1:]) / 2.0
            numerator = np.sum(e_mid * dos_mid * de)
            denominator = np.sum(dos_mid * de)

            if abs(denominator) < 1e-10:
                center = 0.0
            else:
                center = numerator / denominator

            self._results.append({
                "label": key,
                "center": center,
                "integral": denominator,
            })

    # -- Properties ------------------------------------------------

    @property
    def results(self) -> List[Dict[str, Any]]:
        return self._results
