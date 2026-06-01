"""
Band Center Analyzer — VASPKIT 503 replica.

Calculates d-band center from PDOS data in DOSCAR.
Outputs spin-up, spin-down, and average band centers.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .base import BaseAnalyzer
from .pdos_analysis import PDOSAnalyzer


class BandCenterAnalyzer(BaseAnalyzer):
    """Calculate band center from DOSCAR (VASPKIT 503)."""

    def __init__(self) -> None:
        super().__init__()
        self._pdos = PDOSAnalyzer()
        self._results: List[Dict[str, Any]] = []

    def run(self, doscar_path: str = "", directory: str = ".",
            atoms: str = "", orbitals: str = "d") -> None:
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
        sep = "-" * 58
        print("\n" + sep)
        print("  Band Center Analysis")
        print(sep)
        print("  %-12s %10s %10s %10s" % ("Label", "Up(eV)", "Down(eV)", "Avg(eV)"))
        print("  " + "-" * 48)
        for r in self._results:
            print("  %-12s %10.4f %10.4f %10.4f" %
                  (r["label"], r["center_up"], r["center_dn"], r["center_avg"]))
        print("  Fermi level: %.4f eV" % self._pdos._efermi)
        print(sep + "\n")

    def to_excel(self, output: str, selection: str = "Fe",
                 orbitals: str = "d") -> None:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BandCenter"
        ws.append(["Label", "Center_up(eV)", "Center_dn(eV)", "Center_avg(eV)", "E_Fermi(eV)"])
        for r in self._results:
            ws.append([r["label"], r["center_up"], r["center_dn"],
                       r["center_avg"], self._pdos._efermi])
        wb.save(output)

    def _compute_band_center(self, atoms: str, orbitals: str) -> None:
        pdos_data = self._pdos._extract_pdos(atoms, orbitals)
        if not pdos_data:
            self.errors.append("No PDOS data for %s %s orbitals" % (atoms, orbitals))
            return

        energies = np.array(self._pdos._energies)

        def _calc_center(e_occ, edos):
            de = np.diff(e_occ)
            dm = (edos[:-1] + edos[1:]) / 2.0
            em = (e_occ[:-1] + e_occ[1:]) / 2.0
            num = np.sum(em * dm * de)
            den = np.sum(dm * de)
            if abs(den) < 1e-10:
                return 0.0
            return num / den

        for key, data in sorted(pdos_data.items()):
            dos_up = np.array(data.get("up", []))
            dos_dn = np.array(data.get("dn", []))
            if len(dos_up) == 0:
                continue

            mask = energies <= 0.0
            if not np.any(mask):
                mask = np.ones(len(energies), dtype=bool)

            e_occ = energies[mask]
            c_up = _calc_center(e_occ, dos_up[mask])
            c_dn = _calc_center(e_occ, dos_dn[mask])
            c_avg = (c_up + c_dn) / 2.0 if self._pdos._ispin == 2 else c_up

            self._results.append({
                "label": key,
                "center_up": c_up,
                "center_dn": c_dn,
                "center_avg": c_avg,
            })

    @property
    def results(self) -> List[Dict[str, Any]]:
        return self._results
