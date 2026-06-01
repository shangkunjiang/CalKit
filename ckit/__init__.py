"""
CalKit — Multi-scale Computation Analysis Toolkit for post-processing results from
VASP, Materials Studio, LAMMPS, ABACUS, DeePkit and other computational software.

Version: 0.4.0

Modules:
  base               — BaseAnalyzer abstract class
  force_convergence  — Force convergence analysis
  bader_analysis     — Bader charge analysis
  free_energy        — Free energy extraction
  pdos_analysis      — PDOS analysis
  magnetic_moment    — Magnetic moment analysis
  energy             — Energy extraction
  config             — Configuration management
"""

from .base import BaseAnalyzer
from .bader_analysis import BaderAnalyzer
from .config import load_config, save_config
from .energy import EnergyExtractor
from .force_convergence import ForceConvergenceAnalyzer
from .free_energy import FreeEnergyAnalyzer
from .magnetic_moment import MagneticMomentAnalyzer
from .pdos_analysis import PDOSAnalyzer

__version__ = "0.4.0"
__all__ = [
    "BaseAnalyzer",
    "ForceConvergenceAnalyzer",
    "BaderAnalyzer",
    "FreeEnergyAnalyzer",
    "PDOSAnalyzer",
    "MagneticMomentAnalyzer",
    "EnergyExtractor",
    "load_config",
    "save_config",
]