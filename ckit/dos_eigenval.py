"""
DOS from EIGENVAL — VASPKIT 115 style Gaussian smearing.

Reads VASP EIGENVAL (energy eigenvalues + k-point weights) and OUTCAR
(Fermi level) to compute density of states via Gaussian smearing.

Replaces the DOSCAR-direct approach with the same algorithm VASPKIT 115 uses.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .base import BaseAnalyzer


class DOSEigenvalAnalyzer(BaseAnalyzer):
    """Compute DOS from EIGENVAL using Gaussian smearing (VASPKIT 115)."""

    def __init__(self) -> None:
        super().__init__()
        self.eigenval: Optional[Path] = None
        self.outcar: Optional[Path] = None
        self._energies: List[float] = []        # energy grid
        self._dos_total: List[float] = []        # total DOS
        self._dos_up: List[float] = []           # spin-up DOS (if ISPIN=2)
        self._dos_down: List[float] = []         # spin-down DOS (if ISPIN=2)
        self._idos: List[float] = []             # integrated DOS
        self._efermi: float = 0.0                # Fermi level from OUTCAR
        self._ispin: int = 1                     # 1=non-polarised, 2=spin-polarised
        self._nbands: int = 0
        self._nkpts: int = 0
        self._nelect: int = 0
        self._sigma: float = 0.05                # smearing width (eV)
        self._nedos: int = 2000                  # number of energy grid points
        self._eigen_up: List[float] = []          # parsed spin-up eigenvalues
        self._eigen_down: List[float] = []        # parsed spin-down eigenvalues
        self._kweights: List[float] = []          # k-point weights

    # -- Public API -----------------------------------------------------

    def run(self, eigenval_path: str = "", outcar_path: str = "",
            directory: str = ".", sigma: float = 0.05, nedos: int = 2000) -> None:
        """Execute DOS calculation."""
        self._sigma = sigma
        self._nedos = nedos

        self.eigenval = self._resolve(eigenval_path or "EIGENVAL", directory)
        self.outcar = self._resolve(outcar_path or "OUTCAR", directory)

        if not self._check_file(self.eigenval, "EIGENVAL"):
            return

        self._parse_eigenval()
        self._read_fermi()
        self._compute_dos()
        self._ran = True

    def print_summary(self) -> None:
        if not self._ran:
            print("Run analysis first.")
            return

        sep = "-" * 50
        print("\n" + sep)
        print("  DOS Analysis Summary (Gaussian smearing)")
        print(sep)
        print("  Sigma: %.3f eV" % self._sigma)
        print("  Grid points: %d" % self._nedos)
        print("  Fermi level: %.4f eV" % self._efermi)
        print("  Spin: %s" % ("polarised" if self._ispin == 2 else "non-polarised"))

        if self._energies:
            print("  Energy aligned: %.4f ~ %.4f eV (vs E-fermi)" %
                  (self._energies[0], self._energies[-1]))
            peak = float(np.max(self._dos_total))
            print("  DOS max: %.2f states/eV" % peak)

        if self._idos:
            print("  IDOS at E-fermi: %.2f electrons" %
                  self._idos[len(self._idos) // 2])

        print(sep + "\n")

    def to_excel(self, output: str) -> None:
        """Export DOS data to Excel (compatible with VASPKIT TDOS.dat)."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "DOS"

        if self._ispin == 2:
            ws.append(["Energy(eV)", "DOS(up)", "DOS(down)", "DOS(total)", "IDOS"])
            for i, e in enumerate(self._energies):
                ws.append([e, self._dos_up[i], self._dos_down[i],
                           self._dos_total[i], self._idos[i]])
        else:
            ws.append(["Energy(eV)", "DOS(total)", "IDOS"])
            for i, e in enumerate(self._energies):
                ws.append([e, self._dos_total[i], self._idos[i]])

        wb.save(output)

    def to_file(self, output: str) -> None:
        """Write TDOS.dat-style output file."""
        with open(output, "w") as f:
            if self._ispin == 2:
                f.write("# Energy(eV)  DOS(up)  DOS(down)  DOS(total)  IDOS\n")
                for i, e in enumerate(self._energies):
                    f.write("%12.6f  %12.6f  %12.6f  %12.6f  %12.6f\n" %
                            (e, self._dos_up[i], self._dos_down[i],
                             self._dos_total[i], self._idos[i]))
            else:
                f.write("# Energy(eV)  DOS(total)  IDOS\n")
                for i, e in enumerate(self._energies):
                    f.write("%12.6f  %12.6f  %12.6f\n" %
                            (e, self._dos_total[i], self._idos[i]))

    # -- Parsing --------------------------------------------------------

    def _parse_eigenval(self) -> None:
        """Parse VASP EIGENVAL file.

        Format:
          Line 0: NIONS NIONS NBLOCK ISPIN
          Lines 1-4: header (skip)
          Line 5: "CAR "
          Line 6: system name
          Line 7: NELECT NKPTS NBANDS
          Then for each k-point:
            kx ky kz weight
            For each band (ISPIN=1): idx E occ
            For each band (ISPIN=2): idx E_up E_down occ_up occ_down
        """
        lines = self.eigenval.read_text().splitlines()
        if len(lines) < 8:
            self.errors.append("EIGENVAL too short")
            return

        # Line 0: get ISPIN
        try:
            tokens = lines[0].split()
            self._ispin = int(tokens[3])
        except (IndexError, ValueError):
            self._ispin = 1

        # Search for NELECT NKPTS NBANDS line (varies by VASP version)
        found = False
        line_idx = 8  # default start position
        start_search = 2  # skip first 2 header lines
        for i in range(start_search, min(start_search + 10, len(lines))):
            tokens = lines[i].split()
            if len(tokens) == 3:
                try:
                    n1 = int(tokens[0])
                    n2 = int(tokens[1])
                    n3 = int(tokens[2])
                    if n1 > 0 and n2 > 0 and 0 < n3 < 10000:
                        self._nelect = n1
                        self._nkpts = n2
                        self._nbands = n3
                        line_idx = i + 2  # skip NELECT line + blank line
                        found = True
                        break
                except (ValueError, IndexError):
                    continue

        if not found:
            self.errors.append("Cannot find NELECT/NKPTS/NBANDS in EIGENVAL")
            return
        for _ in range(self._nkpts):
            if line_idx >= len(lines):
                break

            # K-point line: kx ky kz weight
            try:
                ktokens = lines[line_idx].split()
                if not ktokens:
                    line_idx += 1
                    continue
                if len(ktokens) >= 4:
                    weight = float(ktokens[3])
                else:
                    weight = 1.0
            except (ValueError, IndexError):
                weight = 1.0

            self._kweights.append(weight)
            line_idx += 1

            # Band eigenvalues
            for _ in range(self._nbands):
                if line_idx >= len(lines):
                    break
                parts = lines[line_idx].split()
                line_idx += 1

                if not parts:
                    continue
                try:
                    if self._ispin == 2 and len(parts) >= 3:
                        self._eigen_up.append(float(parts[1]))
                        self._eigen_down.append(float(parts[2]))
                    elif len(parts) >= 2:
                        val = float(parts[1])
                        self._eigen_up.append(val)
                    else:
                        continue
                except ValueError:
                    continue

        if self._ispin == 1:
            self._eigen_down = self._eigen_up.copy()

    def _read_fermi(self) -> None:
        """Extract Fermi level from OUTCAR."""
        if not self.outcar.exists():
            return

        try:
            text = self.outcar.read_text()
            # VASP writes "E-fermi" in OUTCAR
            for line in reversed(text.splitlines()):
                if "E-fermi" in line or "E-fermi" in line.replace(" ", ""):
                    tokens = line.split()
                    for i, t in enumerate(tokens):
                        if "fermi" in t.lower() or "Fermi" in t:
                            if i + 1 < len(tokens):
                                # Look for ":" separator
                                val = tokens[i + 1].replace(":", "").strip()
                                try:
                                    self._efermi = float(val)
                                    return
                                except ValueError:
                                    pass
                            # Try the last numeric-looking token in the line
                            for tok in reversed(tokens):
                                try:
                                    self._efermi = float(tok)
                                    return
                                except ValueError:
                                    continue
        except Exception:
            pass

    # -- DOS computation -----------------------------------------------

    def _compute_dos(self) -> None:
        """Compute DOS via Gaussian smearing.

        For each eigenvalue E_i at k-point with weight w_k:
            DOS(E) += w_k * gaussian(E - E_i, sigma)
        where gaussian(x) = 1/(sigma * sqrt(2*pi)) * exp(-x^2 / (2*sigma^2))
        """
        if not self._eigen_up:
            self.errors.append("No eigenvalues parsed from EIGENVAL")
            return

        # Build eigenvalue arrays (flattened)
        eup = np.array(self._eigen_up, dtype=np.float64)
        if self._ispin == 2:
            edown = np.array(self._eigen_down, dtype=np.float64)
        else:
            edown = eup.copy()

        # K-point weights (repeated per band)
        ntotal = self._nkpts * self._nbands
        if len(self._kweights) == 0:
            self._kweights = [1.0]

        # Expand k-point weights to match eigenvalues
        weights = np.zeros(ntotal, dtype=np.float64)
        for ik in range(self._nkpts):
            w = self._kweights[ik]
            start = ik * self._nbands
            end = start + self._nbands
            weights[start:end] = w

        # Normalisation factor
        weight_sum = float(np.sum(weights))
        if weight_sum > 0:
            weights /= weight_sum

        # Energy range: E_min - 5*sigma to E_max + 5*sigma
        emin = float(np.min(eup)) - 5.0 * self._sigma
        emax = float(np.max(eup)) + 5.0 * self._sigma
        if self._ispin == 2:
            emin = min(emin, float(np.min(edown)) - 5.0 * self._sigma)
            emax = max(emax, float(np.max(edown)) + 5.0 * self._sigma)

        # Create energy grid
        dE = (emax - emin) / (self._nedos - 1)
        energy_grid = np.linspace(emin, emax, self._nedos, dtype=np.float64)

        # Gaussian prefactor
        sigma = self._sigma
        prefactor = 1.0 / (sigma * np.sqrt(2.0 * np.pi))

        # Compute DOS: iterate over eigenvalues, accumulate contributions
        # Use localised approach: for each eigenvalue, only update grid
        # points within +/- 5*sigma to save computation
        nsigma = 5.0
        half_width = int(np.ceil(nsigma * sigma / dE))

        dos_up = np.zeros(self._nedos, dtype=np.float64)
        dos_down = np.zeros(self._nedos, dtype=np.float64)

        for i in range(ntotal):
            w = weights[i]

            # Spin-up
            e = eup[i]
            idx_center = int(round((e - emin) / dE))
            lo = max(0, idx_center - half_width)
            hi = min(self._nedos, idx_center + half_width + 1)

            for j in range(lo, hi):
                x = (energy_grid[j] - e) / sigma
                dos_up[j] += w * prefactor * np.exp(-0.5 * x * x)

            # Spin-down
            if self._ispin == 2:
                e = edown[i]
                idx_center = int(round((e - emin) / dE))
                lo = max(0, idx_center - half_width)
                hi = min(self._nedos, idx_center + half_width + 1)

                for j in range(lo, hi):
                    x = (energy_grid[j] - e) / sigma
                    dos_down[j] += w * prefactor * np.exp(-0.5 * x * x)

        # Align energy axis to Fermi level
        energy_grid -= self._efermi

        # Total DOS
        dos_total = dos_up + dos_down if self._ispin == 2 else dos_up

        # Integrated DOS (trapezoidal integration)
        idos = np.zeros(self._nedos, dtype=np.float64)
        idos[0] = dos_total[0] * dE * 0.5
        for i in range(1, self._nedos):
            idos[i] = idos[i - 1] + (dos_total[i] + dos_total[i - 1]) * dE * 0.5

        # Store results
        self._energies = energy_grid.tolist()
        self._dos_total = dos_total.tolist()
        self._idos = idos.tolist()

        if self._ispin == 2:
            self._dos_up = dos_up.tolist()
            self._dos_down = dos_down.tolist()
        else:
            self._dos_up = self._dos_total.copy()
            self._dos_down = self._dos_total.copy()

    # -- Properties ----------------------------------------------------

    @property
    def energies(self) -> List[float]:
        return self._energies.copy()

    @property
    def dos_total(self) -> List[float]:
        return self._dos_total.copy()

    @property
    def dos_up(self) -> List[float]:
        return self._dos_up.copy()

    @property
    def dos_down(self) -> List[float]:
        return self._dos_down.copy()

    @property
    def efermi(self) -> float:
        return self._efermi
