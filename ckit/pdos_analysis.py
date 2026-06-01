"""
Projected DOS of selected atoms/orbitals — faithful VASPKIT 115 replica.

Reads VASP DOSCAR (with LORBIT projector data), asks user to select
atoms (by element symbol or index) and orbitals, then outputs PDOS
data in VASPKIT PDOS_USER.dat format.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .base import BaseAnalyzer


class PDOSAnalyzer(BaseAnalyzer):
    """Projected DOS of selected atoms/orbitals — VASPKIT 115 style."""

    def __init__(self) -> None:
        super().__init__()
        self.doscar: Optional[Path] = None
        self._efermi: float = 0.0
        self._ispin: int = 1
        self._nedos: int = 0
        self._nions: int = 0
        self._energies: List[float] = []           # energy grid (aligned to E-fermi)
        self._total_dos: Dict[str, List[float]] = {}  # total DOS by spin
        # PDOS data: key = "element_orbital", value = dict of spin→array
        self._pdos_data: Dict[str, Any] = {}
        self._atom_types: List[str] = []             # element names
        self._atom_counts: List[int] = []            # count per element
        self._atom_elements: List[str] = []          # element per atom index

    # -- Public API -----------------------------------------------

    def run(self, doscar_path: str = "", directory: str = ".",
            atoms: List[str] = None, orbitals: str = "all") -> None:
        self.doscar = self._resolve(doscar_path or "DOSCAR", directory)

        if not self._check_file(self.doscar, "DOSCAR"):
            return

        self._parse_doscar()
        self._ran = True

    def print_summary(self) -> None:
        if not self._ran:
            print("Run analysis first.")
            return
        sep = "-" * 50
        print("\n" + sep)
        print("  PDOS Summary (VASPKIT 115 style)")
        print(sep)
        print("  Ions: %d" % self._nions)
        print("  Fermi level: %.4f eV" % self._efermi)
        print("  NEDOS: %d" % self._nedos)
        print("  Spin: %s" % ("polarised" if self._ispin == 2 else "non-polarised"))
        print(sep + "\n")

    def to_file(self, output: str, selection: str = "Fe",
                orbitals: str = "all") -> None:
        """Write PDOS_USER.dat in VASPKIT format.

        *selection*: element symbol (e.g. "Fe") or atom range (e.g. "1-4")
        *orbitals*: orbital names or "all"
        """
        data = self._extract_pdos(selection, orbitals)
        if not data:
            return

        lines = []
        # Header line
        header_parts = ["#Energy"]
        for key in sorted(data.keys()):
            header_parts.append("UP_%s" % key)
            if self._ispin == 2:
                header_parts.append("DW_%s" % key)
        lines.append("    " + "   ".join("%-12s" % p for p in header_parts).rstrip())

        # Data lines
        ndata = len(self._energies)
        for i in range(ndata):
            row = ["%12.5f" % self._energies[i]]
            for key in sorted(data.keys()):
                up = data[key]["up"][i] if i < len(data[key]["up"]) else 0.0
                row.append("%12.5f" % up)
                if self._ispin == 2:
                    dn = data[key]["dn"][i] if i < len(data[key]["dn"]) else 0.0
                    row.append("%12.5f" % dn)
            lines.append("".join(row))

        with open(output, "w") as f:
            f.write("\n".join(lines) + "\n")

    def to_excel(self, output: str, selection: str = "Fe",
                 orbitals: str = "all") -> None:
        import openpyxl
        data = self._extract_pdos(selection, orbitals)
        if not data:
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "PDOS"
        headers = ["Energy(eV)"]
        for key in sorted(data.keys()):
            headers.append("%s_up" % key)
            if self._ispin == 2:
                headers.append("%s_down" % key)
        ws.append(headers)
        ndata = len(self._energies)
        for i in range(ndata):
            row = [self._energies[i]]
            for key in sorted(data.keys()):
                up = data[key]["up"][i] if i < len(data[key]["up"]) else 0.0
                row.append(up)
                if self._ispin == 2:
                    dn = data[key]["dn"][i] if i < len(data[key]["dn"]) else 0.0
                    row.append(dn)
            ws.append(row)
        wb.save(output)

    # -- DOSCAR parsing ------------------------------------------

    def _parse_doscar(self) -> None:
        """Parse VASP DOSCAR with PDOS (LORBIT >= 10)."""
        lines = self.doscar.read_text().splitlines()
        if len(lines) < 6:
            self.errors.append("DOSCAR too short")
            return

        # Header line 0: NIONS NIONS POTIM ...
        try:
            self._nions = int(lines[0].split()[0])
        except (IndexError, ValueError):
            self.errors.append("Cannot read NIONS from DOSCAR")
            return

        # Find the NEDOS / E-fermi line
        nedos = 0
        header_end = 0
        for i, line in enumerate(lines):
            toks = line.split()
            if len(toks) >= 3:
                for pos in [2, 1, 0]:
                    if pos >= len(toks):
                        continue
                    try:
                        n1 = int(float(toks[pos]))
                        n2_idx = min(pos + 1, len(toks) - 1)
                        n2 = float(toks[n2_idx])
                        if 100 <= n1 <= 50000 and -100 < n2 < 100 and n1 > self._nions:
                            nedos = n1
                            self._efermi = n2
                            header_end = i
                            break
                    except (ValueError, IndexError):
                        continue
                if nedos > 0:
                    break

        if nedos == 0:
            self.errors.append("Cannot find NEDOS in DOSCAR")
            return

        self._nedos = nedos
        data_start = header_end + 1

        # Read energy grid and total DOS
        # Check spin: if data row has 3+ columns, spin-polarised
        first_data = lines[data_start].split()
        ncol = len(first_data) if data_start < len(lines) else 2
        self._ispin = 2 if ncol >= 3 else 1

        self._energies = []
        total_up = []
        total_dn = []

        for i in range(nedos):
            idx = data_start + i
            if idx >= len(lines):
                break
            parts = lines[idx].split()
            if not parts:
                break
            try:
                self._energies.append(float(parts[0]) - self._efermi)
                if self._ispin == 2 and len(parts) >= 3:
                    total_up.append(float(parts[1]))
                    total_dn.append(float(parts[2]))
                else:
                    total_up.append(float(parts[1]))
            except (ValueError, IndexError):
                break

        self._total_dos["up"] = total_up
        if self._ispin == 2:
            self._total_dos["dn"] = total_dn
        else:
            self._total_dos["dn"] = total_up

        # Read PDOS blocks: after total DOS, one block per ion
        # Each PDOS block: header line with element symbol, then NEDOS rows
        pdos_start = data_start + nedos
        self._atom_elements = []
        self._atom_types = []
        self._atom_counts = []

        # Read atom counts from header if available
        # Standard DOSCAR with PDOS stores atom info in the header

        # Read per-atom PDOS
        pdos_idx = 0
        current_atom = 0
        while pdos_start < len(lines) and current_atom < self._nions:
            # Skip any blank lines
            while pdos_start < len(lines) and not lines[pdos_start].strip():
                pdos_start += 1
            if pdos_start >= len(lines):
                break

            # Header line for this atom (may contain element info)
            hdr = lines[pdos_start].split()
            element = "atom%d" % (current_atom + 1)
            if hdr and not hdr[0].replace(".", "").replace("-", "").isdigit():
                element = hdr[0]
            pdos_start += 1

            # Determine how many spin channels × orbitals per row
            if pdos_start >= len(lines):
                break
            first_pdos = lines[pdos_start].split()
            nperrow = len(first_pdos) - 1 if first_pdos else 0  # exclude energy

            # Orbital labels for this atom
            if nperrow >= 18:  # s, py, pz, px, dxy, dyz, dz2, dxz, dx2 × 2 spins
                orb_labels = ["s", "py", "pz", "px", "dxy", "dyz", "dz2", "dxz", "dx2"]
            elif nperrow >= 9:
                orb_labels = ["s", "py", "pz", "px", "dxy", "dyz", "dz2", "dxz", "dx2"]
            elif nperrow >= 4 and self._ispin == 2:
                orb_labels = ["s", "py", "pz", "px"]
            elif nperrow >= 2:
                orb_labels = ["s", "p"]
            else:
                orb_labels = ["total"]

            norbs = len(orb_labels)
            if self._ispin == 2:
                norbs *= 2  # spin × each orbital

            # Read PDOS data rows for this atom
            for i in range(nedos):
                if pdos_start >= len(lines):
                    break
                parts = lines[pdos_start].split()
                pdos_start += 1
                if not parts:
                    continue

                # Store per-orbital PDOS
                key_prefix = "%s_%d" % (element, current_atom + 1)
                for io in range(min(len(orb_labels), (len(parts) - 1) // (self._ispin if self._ispin > 1 else 1))):
                    orb = orb_labels[io]
                    key = "%s_%s" % (key_prefix, orb)
                    if key not in self._pdos_data:
                        self._pdos_data[key] = {"up": [], "dn": []}
                    col_up = io * self._ispin + 1 if self._ispin == 2 else io + 1
                    if col_up < len(parts):
                        try:
                            self._pdos_data[key]["up"].append(float(parts[col_up]))
                        except ValueError:
                            self._pdos_data[key]["up"].append(0.0)
                    if self._ispin == 2:
                        col_dn = col_up + 1
                        if col_dn < len(parts):
                            try:
                                self._pdos_data[key]["dn"].append(float(parts[col_dn]))
                            except ValueError:
                                self._pdos_data[key]["dn"].append(0.0)

            current_atom += 1

    # -- PDOS extraction -----------------------------------------

    def _extract_pdos(self, selection: str, orbitals: str = "all") -> Dict[str, Any]:
        """Extract PDOS for given atoms and orbitals.

        Returns: { "element_orbital": {"up": [...], "dn": [...]} }
        """
        # Parse selection: element symbol or atom index
        selected_keys = []
        token = selection.strip()
        if not token:
            return {}

        # Check if it's an element symbol
        is_element = not token.replace("-", "").isdigit()

        for key in self._pdos_data:
            # key format: "Fe_1_s" or "atom1_1_s"
            parts = key.split("_")
            if len(parts) < 3:
                continue
            elem = parts[0]

            if is_element and elem.lower() == token.lower():
                if orbitals == "all" or any(o in key for o in orbitals.split()):
                    selected_keys.append(key)
            elif not is_element:
                # Numeric atom index
                try:
                    aidx = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else -1
                    if aidx == int(token) - 1 or str(aidx + 1) == token:
                        if orbitals == "all" or any(o in key for o in orbitals.split()):
                            selected_keys.append(key)
                except ValueError:
                    pass

        if not selected_keys:
            return {}

        # Build output dict: collapse same element+orbital across atoms
        result: Dict[str, Any] = {}
        for key in sorted(selected_keys):
            # Extract element_orbital from key
            # "Fe_1_dxy" → "Fe_dxy"
            parts = key.split("_")
            if len(parts) >= 3:
                short_key = "%s_%s" % (parts[0], "_".join(parts[2:]))
            else:
                short_key = key

            if short_key not in result:
                ndata = len(self._pdos_data[key].get("up", []))
                result[short_key] = {"up": np.zeros(ndata), "dn": np.zeros(ndata)}

            up_arr = np.array(self._pdos_data[key].get("up", []))
            dn_arr = np.array(self._pdos_data[key].get("dn", []))

            n = min(len(result[short_key]["up"]), len(up_arr))
            result[short_key]["up"][:n] += up_arr[:n]
            if len(dn_arr) >= n:
                result[short_key]["dn"][:n] += dn_arr[:n]

        return result

    # -- Properties ----------------------------------------------

    @property
    def energies(self) -> List[float]:
        return self._energies[:]
