"""
Command-line interface for CalKit.

Uses a command registry pattern so new analyzers can be added
by simply appending to `COMMANDS` — no argparse boilerplate needed.
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .bader_analysis import BaderAnalyzer
from .energy import EnergyExtractor
from .force_convergence import ForceConvergenceAnalyzer
from .free_energy import FreeEnergyAnalyzer
from .magnetic_moment import MagneticMomentAnalyzer
from .pdos_analysis import PDOSAnalyzer


# ── Command registry ──────────────────────────────────────────

COMMANDS = {
    "force": {
        "class": ForceConvergenceAnalyzer,
        "help": "Force convergence analysis",
        "run_kwargs": lambda a: {"outcar_path": a.outcar, "directory": a.directory},
        "add_args": lambda p: (
            p.add_argument("--outcar", default="", help="OUTCAR path"),
            p.add_argument("--directory", default=".", help="VASP directory"),
        ),
    },
    "bader": {
        "class": BaderAnalyzer,
        "help": "Bader charge analysis",
        "run_kwargs": lambda a: {"acf_path": a.acf, "outcar_path": a.outcar, "directory": a.directory},
        "add_args": lambda p: (
            p.add_argument("--acf", default="", help="ACF.dat path"),
            p.add_argument("--outcar", default="", help="OUTCAR path"),
            p.add_argument("--directory", default=".", help="VASP directory"),
            p.add_argument("--excel", default="", help="Export to Excel"),
        ),
    },
    "free": {
        "class": FreeEnergyAnalyzer,
        "help": "Free energy analysis",
        "run_kwargs": lambda a: {"outcar_path": a.outcar, "directory": a.directory},
        "add_args": lambda p: (
            p.add_argument("--outcar", default="", help="OUTCAR path"),
            p.add_argument("--directory", default=".", help="VASP directory"),
            p.add_argument("--output", default="", help="Write to file"),
        ),
    },
    "pdos": {
        "class": PDOSAnalyzer,
        "help": "PDOS analysis",
        "run_kwargs": lambda a: {"doscar_path": a.doscar, "procar_path": a.procar, "directory": a.directory},
        "add_args": lambda p: (
            p.add_argument("--doscar", default="", help="DOSCAR path"),
            p.add_argument("--procar", default="", help="PROCAR path"),
            p.add_argument("--directory", default=".", help="VASP directory"),
            p.add_argument("--excel", default="", help="Export to Excel"),
        ),
    },
    "mag": {
        "class": MagneticMomentAnalyzer,
        "help": "Magnetic moment analysis",
        "run_kwargs": lambda a: {"outcar_path": a.outcar, "directory": a.directory},
        "add_args": lambda p: (
            p.add_argument("--outcar", default="", help="OUTCAR path"),
            p.add_argument("--directory", default=".", help="VASP directory"),
            p.add_argument("--excel", default="", help="Export to Excel"),
        ),
    },
    "energy": {
        "class": EnergyExtractor,
        "help": "Energy extraction",
        "run_kwargs": lambda a: {"outcar_path": a.outcar, "directory": a.directory},
        "add_args": lambda p: (
            p.add_argument("--outcar", default="", help="OUTCAR path"),
            p.add_argument("--directory", default=".", help="VASP directory"),
            p.add_argument("--output", default="", help="Write to file"),
        ),
    },
}


# ── CLI builder ───────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calkit",
        description="CalKit — Multi-scale Computation Analysis Toolkit (v%s)" % __version__,
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    for name, spec in COMMANDS.items():
        sp = sub.add_parser(name, help=spec["help"])
        spec["add_args"](sp)
        sp.set_defaults(cmd_name=name)

    # Global options
    parser.add_argument("--version", action="version", version=f"calkit {__version__}")
    return parser


# ── Entry point ──────────────────────────────────────────────

def main(argv: list | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        # No sub-command → launch interactive menu
        from .menu import main as menu_main
        menu_main()
        return

    spec = COMMANDS[args.command]
    analyzer = spec["class"]()
    kwargs = spec["run_kwargs"](args)
    analyzer.run(**kwargs)

    if analyzer.errors:
        print("\nErrors:")
        for e in analyzer.errors:
            print(f"  - {e}")
        sys.exit(1)

    analyzer.print_summary()

    # Optional export
    if hasattr(args, "excel") and args.excel:
        analyzer.to_excel(args.excel)
        print(f"Exported to {args.excel}")
    if hasattr(args, "output") and args.output:
        analyzer.to_file(args.output)
        print(f"Written to {args.output}")


if __name__ == "__main__":
    main()
