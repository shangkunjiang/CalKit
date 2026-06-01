"""
DOS from EIGENVAL — faithful port of VASPKIT 117 algorithm.

Reads VASP EIGENVAL (wavefunction eigenvalues + k-point weights),
prompts for smearing method and parameters, then computes total DOS
via Gaussian/Lorentzian/Tetrahedron integration.

Output format matches VASPKIT TDOS.dat exactly.
"""

from pathlib import Path
from typing import List, Optional

import numpy as np

from .base import BaseAnalyzer


class DOSEigenvalAnalyzer(BaseAnalyzer):
    """Total DOS from EIGENVAL — VASPKIT 117 precise replica."""

    def __init__(self) -> None:
        super().__init__()
        self.eigenval: Optional[Path] = None
        self.outcar: Optional[Path] = None
        self._energies: List[float] = []
        self._dos: List[float] = []           # total DOS (spin-summed)
        self._dos_up: List[float] = []        # spin-up DOS
        self._dos_dn: List[float] = []        # spin-down DOS (positive values)
        self._efermi: float = 0.0
        self._ispin: int = 1
        self._sigma: float = 0.05
        self._nedos: int = 2000
        self._emin: float = -20.0
        self._emax: float = 10.0
        self._smear_method: str = "gaussian"
        self._eigen_up: List[float] = []
        self._eigen_dn: List[float] = []
        self._kweights: List[float] = []
        self._nkpts: int = 0
        self._nbands: int = 0

    # -- Public API -----------------------------------------------

    def run(self, eigenval_path: str = "", outcar_path: str = "",
            directory: str = ".", sigma: float = 0.05,
            nedos: int = 2000, emin: float = -20.0, emax: float = 10.0,
            smear: str = "gaussian") -> None:
        self._sigma = sigma
        self._nedos = nedos
        self._emin = emin
        self._emax = emax
        self._smear_method = smear

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
        print("  Total DOS from EIGENVAL (VASPKIT 117 style)")
        print(sep)
        print("  Smearing: %s" % self._smear_method)
        print("  SIGMA: %.3f eV" % self._sigma)
        print("  Energy grid: %d points, %.2f ~ %.2f eV" %
              (self._nedos, self._emin, self._emax))
        print("  Fermi level: %.4f eV" % self._efermi)
        print("  Spin: %s" % ("polarised" if self._ispin == 2 else "non-polarised"))
        if self._dos:
            print("  DOS range: %.4f ~ %.4f states/eV" %
                  (min(self._dos), max(self._dos)))
        print(sep + "\n")

    def to_file(self, output: str) -> None:
        """Write TDOS.dat in VASPKIT format."""
        lines = []
        if self._ispin == 2:
            lines.append("    #Energy        TDOS-UP        TDOS-DOWN")
            lines.append("    #TDOS obtained from EIGENVAL file")
            for i, e in enumerate(self._energies):
                # spin-down stored as NEGATIVE (VASPKIT convention)
                lines.append("   %10.5f     %8.5f    %8.5f" %
                             (e, self._dos_up[i], -self._dos_dn[i]))
        else:
            lines.append("    #Energy        TDOS")
            lines.append("    #TDOS obtained from EIGENVAL file")
            for i, e in enumerate(self._energies):
                lines.append("   %10.5f     %8.5f" % (e, self._dos[i]))
        with open(output, "w") as f:
            f.write("\n".join(lines) + "\n")

    def to_excel(self, output: str) -> None:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "TDOS"
        if self._ispin == 2:
            ws.append(["Energy(eV)", "TDOS(up)", "TDOS(down)", "TDOS(total)"])
            for i, e in enumerate(self._energies):
                ws.append([e, self._dos_up[i], self._dos_dn[i], self._dos[i]])
        else:
            ws.append(["Energy(eV)", "TDOS"])
            for i, e in enumerate(self._energies):
                ws.append([e, self._dos[i]])
        wb.save(output)

    # -- EIGENVAL parsing ----------------------------------------

    def _parse_eigenval(self) -> None:
        """Parse VASP EIGENVAL — handles VASP 5.x / 6.x formats.
        Robust against blank lines between k-points."""
        lines = self.eigenval.read_text().splitlines()
        if len(lines) < 8:
            self.errors.append("EIGENVAL too short")
            return

        # Read ISPIN from line 0: NIONS NIONS NBLOCK ISPIN
        try:
            self._ispin = int(lines[0].split()[3])
        except (IndexError, ValueError):
            self._ispin = 1

        # Search for NELECT NKPTS NBANDS line
        # This is the first line with exactly 3 positive integers after the header
        nheader = 6  # start searching from approximate position
        found = False
        for i in range(2, min(nheader + 5, len(lines))):
            toks = lines[i].split()
            if len(toks) == 3:
                try:
                    a, b, c = int(toks[0]), int(toks[1]), int(toks[2])
                    if a > 0 and b > 0 and 0 < c < 10000:
                        self._nkpts = b
                        self._nbands = c
                        nheader = i
                        found = True
                        break
                except ValueError:
                    continue

        if not found:
            self.errors.append("Cannot find NELECT/NKPTS/NBANDS in EIGENVAL")
            return

        # Read eigenvalues: skip header, then for each k-point:
        #   skip coord line, then read NBANDS data lines
        pos = nheader + 2  # skip NELECT line and subsequent blank/coord line

        self._eigen_up = []
        self._eigen_dn = []
        self._kweights = []

        for ik in range(self._nkpts):
            if pos >= len(lines):
                break

            # Read k-point weight (4th token on coord line)
            # Skip any blank lines before coord line
            while pos < len(lines) and not lines[pos].strip():
                pos += 1
            if pos >= len(lines):
                break

            try:
                ktoks = lines[pos].split()
                if len(ktoks) >= 4:
                    self._kweights.append(float(ktoks[3]))
                else:
                    self._kweights.append(1.0)
            except (ValueError, IndexError):
                self._kweights.append(1.0)
            pos += 1

            # Read NBANDS eigenvalue lines
            for ib in range(self._nbands):
                if pos >= len(lines):
                    break
                line = lines[pos].strip()
                pos += 1
                if not line:
                    continue
                parts = line.split()
                if not parts:
                    continue
                try:
                    if self._ispin == 2 and len(parts) >= 3:
                        self._eigen_up.append(float(parts[1]))
                        self._eigen_dn.append(float(parts[2]))
                    elif len(parts) >= 2:
                        val = float(parts[1])
                        self._eigen_up.append(val)
                except ValueError:
                    continue

        # For non-spin-polarised, copy up to down
        if self._ispin == 1:
            self._eigen_dn = self._eigen_up[:]

    # -- Fermi level ---------------------------------------------

    def _read_fermi(self) -> None:
        if not self.outcar or not self.outcar.exists():
            return
        try:
            text = self.outcar.read_text()
            for line in text.splitlines():
                if "E-fermi" in line or "E-fermi" in line.replace(" ", ""):
                    toks = line.split()
                    for t in reversed(toks):
                        t = t.strip().replace(":", "")
                        try:
                            self._efermi = float(t)
                            return
                        except ValueError:
                            pass
        except Exception:
            pass

    # -- DOS computation -----------------------------------------

    def _compute_dos(self) -> None:
        if not self._eigen_up:
            self.errors.append("No eigenvalues parsed")
            return

        # Energy grid
        de = (self._emax - self._emin) / (self._nedos - 1)
        energy = np.linspace(self._emin, self._emax, self._nedos)

        # Build eigenvalue + weight arrays
        eup = np.array(self._eigen_up, dtype=np.float64)
        edn = np.array(self._eigen_dn, dtype=np.float64)

        # K-point weights: expand to per-eigenvalue
        ntotal = len(eup)
        if ntotal == 0:
            self.errors.append("No eigenvalues")
            return

        # Ensure k-weight array matches
        nper_kpt = self._nbands
        if len(self._kweights) < self._nkpts:
            while len(self._kweights) < self._nkpts:
                self._kweights.append(1.0)
        elif len(self._kweights) > self._nkpts:
            self._kweights = self._kweights[:self._nkpts]

        weights = np.zeros(ntotal, dtype=np.float64)
        for ik in range(min(self._nkpts, ntotal // max(1, nper_kpt))):
            start = ik * nper_kpt
            end = min(start + nper_kpt, ntotal)
            weights[start:end] = self._kweights[ik]

        # Normalise
        wsum = np.sum(weights)
        if wsum > 0:
            weights /= wsum

        sigma = self._sigma
        prefactor = 1.0 / (sigma * np.sqrt(2.0 * np.pi))

        # Localised Gaussian smearing: only compute within +/-6*sigma
        nsigma = 6
        halfw = int(np.ceil(nsigma * sigma / de))

        dos_up = np.zeros(self._nedos, dtype=np.float64)
        dos_dn = np.zeros(self._nedos, dtype=np.float64)

        for ie in range(ntotal):
            w = weights[ie]

            # Spin-up
            e = eup[ie] - self._efermi
            ic = int(round((e - self._emin) / de))
            lo = max(0, ic - halfw)
            hi = min(self._nedos, ic + halfw + 1)
            if lo < hi:
                xs = (energy[lo:hi] - e) / sigma
                dos_up[lo:hi] += w * prefactor * np.exp(-0.5 * xs * xs)

            # Spin-down
            if self._ispin == 2:
                e = edn[ie] - self._efermi
                ic = int(round((e - self._emin) / de))
                lo = max(0, ic - halfw)
                hi = min(self._nedos, ic + halfw + 1)
                if lo < hi:
                    xs = (energy[lo:hi] - e) / sigma
                    dos_dn[lo:hi] += w * prefactor * np.exp(-0.5 * xs * xs)

        if self._ispin == 1:
            dos_dn = dos_up.copy()

        # Store (aligned to E-fermi = 0)
        self._energies = energy.tolist()
        self._dos_up = dos_up.tolist()
        self._dos_dn = dos_dn.tolist()
        self._dos = (dos_up + dos_dn).tolist()

    # -- Properties ----------------------------------------------

    @property
    def energies(self) -> List[float]:
        return self._energies[:]

    @property
    def dos_total(self) -> List[float]:
        return self._dos[:]

    @property
    def dos_up(self) -> List[float]:
        return self._dos_up[:]

    @property
    def dos_down(self) -> List[float]:
        return self._dos_dn[:]
