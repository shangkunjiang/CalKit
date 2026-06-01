"""
Bader Charge Analyzer.

Auto-generates ACF.dat via chgsum.pl + bader, parses results,
and maps atomic species from OUTCAR POTCAR info.
"""

import os
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAnalyzer


class BaderAnalyzer(BaseAnalyzer):
    """Analyze Bader charges — auto-generate ACF.dat if needed."""

    def __init__(self) -> None:
        super().__init__()
        self.acf: Optional[Path] = None
        self.outcar: Optional[Path] = None
        self.directory: Path = Path(".")
        self._atoms: List[Dict[str, Any]] = []
        self._summary: Dict[str, Any] = {}

    # -- Public API -------------------------------------------------

    def run(self, acf_path: str = "", outcar_path: str = "",
            directory: str = ".") -> None:
        self.directory = Path(directory).resolve()

        # Resolve paths
        acf_file = self.directory / (acf_path or "ACF.dat")
        self.outcar = self._resolve(outcar_path or "OUTCAR", directory)

        # If ACF.dat missing, auto-generate
        if not acf_file.exists():
            ok = self._generate_acf()
            if not ok:
                return

        self.acf = acf_file
        if not self._check_file(self.acf, "ACF.dat"):
            return
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
        sep = "-" * 68
        print("\n" + sep)
        print("  Bader Charge Analysis")
        print(sep)
        print("  %-4s %-8s %10s %8s %10s" %
              ("ID", "Element", "Charge", "ZVAL", "Bader"))
        print("  " + "-" * 60)
        for a in self._atoms:
            print("  %-4d %-8s %10.4f %8.1f %10.4f" %
                  (a["id"], a["element"], a["charge"],
                   a["zval"], a["bader"]))
        print(sep + "\n")

    def to_excel(self, output: str) -> None:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Bader"
        ws.append(["Atom_ID", "Element", "Charge", "ZVAL", "Bader"])
        for a in self._atoms:
            ws.append([a["id"], a["element"], a["charge"], a["zval"], a["bader"]])
        wb.save(output)

    # -- ACF generation --------------------------------------------

    def _generate_acf(self) -> bool:
        """Run chgsum.pl + bader to generate ACF.dat."""
        aeccar0 = self.directory / "AECCAR0"
        aeccar2 = self.directory / "AECCAR2"
        chgcar = self.directory / "CHGCAR"
        chgsum_path = Path(__file__).parent / "chgsum.pl"
        bader_path = Path(__file__).parent / "bader_bin"

        if not aeccar0.exists():
            self.errors.append("AECCAR0 not found: %s" % aeccar0)
            return False
        if not aeccar2.exists():
            self.errors.append("AECCAR2 not found: %s" % aeccar2)
            return False
        if not chgcar.exists():
            self.errors.append("CHGCAR not found: %s" % chgcar)
            return False
        if not chgsum_path.exists():
            self.errors.append("chgsum.pl not found in CalKit")
            return False
        if not bader_path.exists():
            self.errors.append("bader binary not found in CalKit")
            return False

        try:
            # Step 1: chgsum.pl AECCAR0 AECCAR2
            print("  Running chgsum.pl AECCAR0 AECCAR2 ...")
            subprocess.run(
                ["perl", str(chgsum_path), "AECCAR0", "AECCAR2"],
                cwd=str(self.directory),
                capture_output=True, text=True, timeout=120, check=True
            )

            # Step 2: bader CHGCAR -ref CHGCAR_sum
            print("  Running bader CHGCAR -ref CHGCAR_sum ...")
            subprocess.run(
                [str(bader_path), "CHGCAR", "-ref", "CHGCAR_sum"],
                cwd=str(self.directory),
                capture_output=True, text=True, timeout=300, check=True
            )

            # Verify ACF.dat was generated
            if not (self.directory / "ACF.dat").exists():
                self.errors.append("bader ran but ACF.dat not generated")
                return False

            print("  ACF.dat generated successfully.")
            return True

        except subprocess.TimeoutExpired:
            self.errors.append("bader calculation timed out")
            return False
        except subprocess.CalledProcessError as e:
            self.errors.append("bader failed: %s" % (e.stderr.strip() if e.stderr else str(e)))
            return False

    # -- Parsing ---------------------------------------------------

    def _parse_acf(self) -> None:
        lines = self.acf.read_text().splitlines()
        header_found = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Find header line: "#    X        Y        Z        CHARGE    MIN DIST   ATOMIC VOL"
            if not header_found:
                if stripped.startswith("#") and "CHARGE" in stripped:
                    header_found = True
                continue

            parts = stripped.split()
            if len(parts) >= 7:
                self._atoms.append({
                    "id": int(parts[0]),
                    "x": float(parts[1]),
                    "y": float(parts[2]),
                    "z": float(parts[3]),
                    "charge": float(parts[4]),
                    "min_dist": float(parts[5]),
                    "volume": float(parts[6]),
                    "element": "",
                    "zval": 0.0,
                    "bader": 0.0,
                })

    def _map_elements(self) -> None:
        """Read POTCAR types and ZVAL from OUTCAR."""
        lines = self.outcar.read_text().splitlines()

        # Read POTCAR types
        potcar_types: List[str] = []
        for line in lines:
            if "POTCAR:" in line:
                label = line.split("POTCAR:")[1].strip().split()
                # POTCAR: PAW_PBE C 08Apr2002 -> element is C (2nd word)
                name = label[1].strip("_").split("_")[0] if len(label) >= 3 else label[0]
                if name not in potcar_types:
                    potcar_types.append(name)

        # Read ion counts
        ion_counts: List[int] = []
        for line in lines:
            if "ions per type" in line:
                nums = [int(w) for w in line.split("=")[1].strip().split()
                        if w.strip().isdigit()]
                ion_counts.extend(nums)
                break

        # Read ZVAL for each element (summary line: ZVAL = 4.00 5.00 8.00)
        zvals: List[float] = []
        for line in lines:
            if "ZVAL" in line and "=" in line and "POMASS" not in line:
                parts = line.split("=")[1].strip().split()
                candidates = []
                for p in parts:
                    try:
                        candidates.append(float(p))
                    except ValueError:
                        break
                if len(candidates) == len(potcar_types):
                    zvals = candidates
                    break

        # Build element + zval map
        if potcar_types and ion_counts and len(potcar_types) == len(ion_counts):
            idx = 1
            for i, (el, cnt) in enumerate(zip(potcar_types, ion_counts)):
                zv = zvals[i] if i < len(zvals) else 0.0
                for j in range(cnt):
                    for atom in self._atoms:
                        if atom["id"] == idx:
                            atom["element"] = el
                            atom["zval"] = zv
                            atom["bader"] = zv - atom["charge"]
                            break
                    idx += 1

    def _build_summary(self) -> None:
        groups: Dict[str, List[float]] = defaultdict(list)
        for a in self._atoms:
            groups[a["element"]].append(a["charge"])
        for elem, charges in groups.items():
            self._summary[elem] = {
                "count": len(charges),
                "min": min(charges),
                "max": max(charges),
                "avg": sum(charges) / len(charges),
            }

    # -- Properties ------------------------------------------------

    @property
    def atoms(self) -> List[Dict[str, Any]]:
        return self._atoms

    @property
    def summary(self) -> Dict[str, Any]:
        return self._summary
