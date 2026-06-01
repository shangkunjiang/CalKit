"""
Magnetic Moment Analyzer for VASP OUTCAR files.

Parses the final ionic step's magnetic moments from OUTCAR and
optionally exports results to Excel.
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseAnalyzer


class MagneticMomentAnalyzer(BaseAnalyzer):
    """Extract and summarize magnetic moments from an OUTCAR file."""

    def __init__(self) -> None:
        super().__init__()
        self.outcar: Optional[Path] = None
        self._moments: List[Dict[str, Any]] = []
        self._summary: Dict[str, Dict[str, Any]] = {}

    # ── Public API ─────────────────────────────────────────────

    def run(self, outcar_path: str = "", directory: str = ".") -> None:
        p = self._resolve(outcar_path or "OUTCAR", directory)
        if not self._check_file(p, "OUTCAR"):
            return

        self.outcar = p
        text = p.read_text()
        self._parse(text)
        self._build_summary()
        self._ran = True

    def print_summary(self) -> None:
        if not self._ran:
            print("Run analysis first.")
            return
        print(f"\n{'─' * 50}")
        print("  Magnetic Moment Summary")
        print(f"{'─' * 50}")
        print(f"  {'Element':<6} {'#Atoms':>6} {'Avg (μB)':>10} {'Min (μB)':>10} {'Max (μB)':>10}")
        print(f"  {'─' * 50}")
        for elem, info in self._summary.items():
            print(f"  {elem:<6} {info['count']:>6} {info['avg']:>10.4f} "
                  f"{info['min']:>10.4f} {info['max']:>10.4f}")
        print(f"{'─' * 50}\n")

    def to_excel(self, output: str) -> None:
        """Export magnetic moments and element summary to Excel."""
        import openpyxl

        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "Atomic Moments"
        ws1.append(["#", "Element", "Magnetic Moment (μB)"])
        for m in self._moments:
            ws1.append([m["num"], m["element"], m["moment"]])

        ws2 = wb.create_sheet("Element Summary")
        ws2.append(["Element", "Count", "Avg (μB)", "Min (μB)", "Max (μB)"])
        for elem, info in self._summary.items():
            ws2.append([elem, info["count"], info["avg"], info["min"], info["max"]])

        wb.save(output)

    # ── Parsing ────────────────────────────────────────────────

    def _parse(self, text: str) -> None:
        # Extract element mapping from POTCAR lines
        element_map = self._extract_element_mapping(text)

        # Find the last magnetization block — after the last "magnetization (x)"
        blocks: List[List[float]] = []
        pattern = re.compile(
            r"#\s*of\s*ion\s+.*?"
            r"magnetization\s*\(x\)",
            re.DOTALL,
        )

        found = pattern.findall(text)
        if not found:
            return

        # Re-split to find the last block's numeric values
        # Instead: find all lines between the last "magnetization (x)" and the next empty line / separator
        # Better approach: find all blocks by pattern

        # Use a different approach: split by "magnetization (x)" headers
        parts = re.split(r"#\s*of\s*ion\s+.*?magnetization\s*\(x\).*?\n", text)
        if len(parts) < 2:
            return

        # Take the last part which contains the final ionic step's moments
        last_part = parts[-1]
        moments: List[float] = []
        for line in last_part.strip().split("\n"):
            # Stop at separator lines
            if "─" in line or "total" in line.lower() or not line.strip():
                if moments:
                    break
                continue
            nums = re.findall(r"[-]?\d+\.\d+", line)
            if nums:
                moments.append(float(nums[-1]))

        if not moments:
            return

        # Build per-atom records
        for i, mom in enumerate(moments, start=1):
            elem = element_map.get(i, "?")
            self._moments.append({"num": i, "element": elem, "moment": mom})

    def _extract_element_mapping(self, text: str) -> Dict[int, str]:
        """Map atom index → element symbol from POTCAR / ions per type."""
        mapping: Dict[int, str] = {}
        elements: List[str] = []
        counts: List[int] = []

        for line in text.splitlines():
            if "POTCAR:" in line:
                label = line.split("POTCAR:")[1].strip().split()[0]
                name = label.split("_")[0].strip("0123456789_")
                if name not in elements:
                    elements.append(name)

            if "ions per type" in line and "=" in line:
                parts = line.split("=")[1].strip().split()
                counts = [int(w) for w in parts if w.isdigit()]
                break

        if len(elements) != len(counts):
            return mapping

        idx = 1
        for el, n in zip(elements, counts):
            for _ in range(n):
                mapping[idx] = el
                idx += 1
        return mapping

    def _build_summary(self) -> None:
        groups: Dict[str, List[float]] = defaultdict(list)
        for m in self._moments:
            groups[m["element"]].append(m["moment"])
        for elem, vals in groups.items():
            self._summary[elem] = {
                "count": len(vals), "min": min(vals),
                "max": max(vals), "avg": sum(vals) / len(vals),
            }

    @property
    def moments(self) -> List[Dict[str, Any]]:
        return self._moments.copy()

    @property
    def summary(self) -> Dict[str, Dict[str, Any]]:
        return {k: v.copy() for k, v in self._summary.items()}