"""
Bader Charge Analyzer.

Reads ACF.dat to extract atomic Bader charges and integrates with
OUTCAR for atomic species mapping.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAnalyzer


class BaderAnalyzer(BaseAnalyzer):
    """Analyze Bader charges from ACF.dat."""

    def __init__(self) -> None:
        super().__init__()
        self.acf: Optional[Path] = None
        self.outcar: Optional[Path] = None
        self._atoms: List[Dict[str, Any]] = []
        self._summary: Dict[str, Dict[str, Any]] = {}

    # ── Public API ─────────────────────────────────────────────

    def run(self, acf_path: str = "", outcar_path: str = "", directory: str = ".") -> None:
        self.acf = self._resolve(acf_path or "ACF.dat", directory)
        if not self._check_file(self.acf, "ACF.dat"):
            return

        self.outcar = self._resolve(outcar_path or "OUTCAR", directory)
        if not self._check_file(self.outcar, "OUTCAR"):
            return

        self._parse_acf()
        self._map_elements()
        self._build_summary()
        self._ran = True

    def print_summary(self) -> None:
        if not self._ran:
            print("Run analysis first.")
            return
        print(f"\n{'─' * 50}")
        print("  Bader Charge Analysis Summary")
        print(f"{'─' * 50}")
        print(f"  {'Element':<6} {'#Atoms':>6} {'Min':>10} {'Max':>10} {'Avg':>10}")
        print(f"  {'─' * 50}")
        for elem, info in self._summary.items():
            print(f"  {elem:<6} {info['count']:>6} {info['min']:>10.4f} "
                  f"{info['max']:>10.4f} {info['avg']:>10.4f}")
        print(f"{'─' * 50}\n")

    def to_excel(self, output: str) -> None:
        """Export atomic charges and element summary to Excel."""
        import openpyxl

        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "Atomic Charges"
        ws1.append(["#", "X", "Y", "Z", "Charge", "MinDist", "AtomicVol", "Element"])
        for a in self._atoms:
            ws1.append([a["num"], a["x"], a["y"], a["z"],
                         a["charge"], a["min_dist"], a["volume"], a["element"]])

        ws2 = wb.create_sheet("Element Summary")
        ws2.append(["Element", "Count", "Min", "Max", "Avg"])
        for elem, info in self._summary.items():
            ws2.append([elem, info["count"], info["min"], info["max"], info["avg"]])

        wb.save(output)

    # ── Parsing ────────────────────────────────────────────────

    def _parse_acf(self) -> None:
        lines = self.acf.read_text().splitlines()
        header_skipped = False
        for line in lines:
            if not header_skipped:
                if line.strip().startswith("#"):
                    parts = line.split()
                    if len(parts) >= 7 and parts[1] == "X":
                        header_skipped = True
                    continue
                else:
                    continue
            parts = line.split()
            if len(parts) >= 7:
                self._atoms.append({
                    "num": int(parts[0]), "x": float(parts[1]), "y": float(parts[2]),
                    "z": float(parts[3]), "charge": float(parts[4]),
                    "min_dist": float(parts[5]), "volume": float(parts[6]), "element": "",
                })

    def _map_elements(self) -> None:
        lines = self.outcar.read_text().splitlines()
        potcar_types = []
        for line in lines:
            if "POTCAR:" in line:
                label = line.split("POTCAR:")[1].strip().split()[0]
                name = label.split("_")[0].strip("0123456789_")
                if name not in potcar_types:
                    potcar_types.append(name)
            if "ions per type" in line:
                nums = [int(w) for w in line.split("=")[1].strip().split() if w.isdigit()]
                break

        if potcar_types and nums and len(potcar_types) == len(nums):
            self._element_map = {}
            idx = 1
            for el, n in zip(potcar_types, nums):
                for _ in range(n):
                    self._element_map[idx] = el
                    idx += 1
            for atom in self._atoms:
                atom["element"] = self._element_map.get(atom["num"], "?")

    def _build_summary(self) -> None:
        groups: Dict[str, List[float]] = defaultdict(list)
        for atom in self._atoms:
            groups[atom["element"]].append(atom["charge"])
        for elem, charges in groups.items():
            self._summary[elem] = {
                "count": len(charges),
                "min": min(charges), "max": max(charges),
                "avg": sum(charges) / len(charges),
            }

    @property
    def atoms(self) -> List[Dict[str, Any]]:
        return self._atoms

    @property
    def summary(self) -> Dict[str, Dict[str, Any]]:
        return self._summary