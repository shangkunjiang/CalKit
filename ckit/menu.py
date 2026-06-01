"""
Interactive TUI menu for CalKit.

The menu is dynamically generated from the same command registry
used by the CLI, so adding a new analyzer only requires updating
COMMANDS in cli.py — this module updates automatically.
"""

import os
import sys
from pathlib import Path

_ANSI_RESET = "\033[0m"
_ANSI_BOLD = "\033[1m"
_ANSI_CYAN = "\033[96m"
_ANSI_GREEN = "\033[92m"
_ANSI_YELLOW = "\033[93m"
_ANSI_RED = "\033[91m"


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _header() -> None:
    print(f"{_ANSI_CYAN}{_ANSI_BOLD}")
    print("╔══════════════════════════════════════╗")
    print("║         CalKit  v0.4.0            ║")
    print("╚══════════════════════════════════════╝")
    print(_ANSI_RESET)


def _menu_items() -> list:
    """Build menu entries from the CLI command registry."""
    from .cli import COMMANDS

    items = []
    for idx, (name, spec) in enumerate(COMMANDS.items(), start=1):
        from .cli import __version__
        items.append((idx, name, spec["help"]))
    return items


def _print_menu(items: list) -> None:
    for idx, name, help_text in items:
        print(f"  {_ANSI_GREEN}[{idx}]{_ANSI_RESET} {name:<10} {_ANSI_YELLOW}{help_text}{_ANSI_RESET}")
    print(f"  {_ANSI_GREEN}[0]{_ANSI_RESET} {'exit':<10} Exit")
    print()


def _run_analyzer(name: str) -> None:
    """Instantiate and run a single analyzer using current directory."""
    from .cli import COMMANDS
    spec = COMMANDS[name]
    analyzer = spec["class"]()

    print("\n" + _ANSI_CYAN + "---- " + spec["help"] + " ----" + _ANSI_RESET)
    print("  Working directory: " + _ANSI_GREEN + os.getcwd() + _ANSI_RESET)

    directory = "."
    kwargs = {"directory": directory}

    if name in ("force", "free", "energy", "mag"):
        kwargs["outcar_path"] = "OUTCAR"
    if name == "bader":
        kwargs["acf_path"] = "ACF.dat"
        kwargs["outcar_path"] = "OUTCAR"
    if name == "pdos":
        kwargs["doscar_path"] = "DOSCAR"
        # Read POSCAR to show atom list
        poscar_path = os.path.join(directory, "POSCAR")
        if os.path.exists(poscar_path):
            try:
                with open(poscar_path, "r") as pf:
                    plines = pf.readlines()
                enames = plines[5].split()
                ecounts = list(map(int, plines[6].split()))
                idx = 1
                print("  Atom list:")
                for ei, cnt in zip(enames, ecounts):
                    for j in range(cnt):
                        print("    %3d: %-3s" % (idx, ei), end="")
                        if idx % 5 == 0:
                            print()
                        idx += 1
                if (idx - 1) % 5 != 0:
                    print()
            except Exception:
                pass
        print("  Free Format, e.g., Fe C H 1-4 7 8 24")
        atoms = input("  Atoms (element or index): ").strip()
        print("  s py pz px dxy dyz dz2 dxz dx2, or all")
        orbs = input("  Orbitals (default: all): ").strip() or "all"
        kwargs["atoms"] = [atoms] if atoms else []
        kwargs["orbitals"] = orbs

    analyzer.run(**kwargs)

    if analyzer.errors:
        print("\n" + _ANSI_RED + "Errors:" + _ANSI_RESET)
        for e in analyzer.errors:
            print("  " + _ANSI_RED + "- " + e + _ANSI_RESET)
        return

    analyzer.print_summary()

    if hasattr(analyzer, "to_excel"):
        out = "PDOS_USER.xlsx"
        analyzer.to_excel(out)
        print(_ANSI_GREEN + "Exported to " + out + _ANSI_RESET)

    # txt export removed

def main() -> None:
    items = _menu_items()
    while True:
        _clear()
        _header()
        _print_menu(items)

        try:
            choice = input(f"{_ANSI_BOLD}Select > {_ANSI_RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if choice == "0":
            print("Goodbye.")
            break

        try:
            idx = int(choice)
            if 1 <= idx <= len(items):
                _run_analyzer(items[idx - 1][1])
                input(f"\n{_ANSI_YELLOW}Press Enter to continue...{_ANSI_RESET}")
            else:
                print(f"{_ANSI_RED}Invalid choice.{_ANSI_RESET}")
                input(f"\n{_ANSI_YELLOW}Press Enter to continue...{_ANSI_RESET}")
        except ValueError:
            print(f"{_ANSI_RED}Enter a number.{_ANSI_RESET}")
            input(f"\n{_ANSI_YELLOW}Press Enter to continue...{_ANSI_RESET}")


if __name__ == "__main__":
    main()