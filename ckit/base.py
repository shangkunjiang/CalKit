"""
Base classes for CalKit analyzers.

All analysis modules inherit from BaseAnalyzer to share common logic
for path resolution, error tracking, and result formatting.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseAnalyzer(ABC):
    """Abstract base for all CalKit analysis modules.

    Subclasses must implement:
      - run(**kwargs)  → execute the analysis pipeline
      - print_summary() → print results to stdout
    """

    def __init__(self) -> None:
        self.errors: List[str] = []
        self._ran: bool = False

    # ── Abstract interface ───────────────────────────────────────

    @abstractmethod
    def run(self, **kwargs: Any) -> None:
        """Execute the analysis pipeline."""
        ...

    @abstractmethod
    def print_summary(self) -> None:
        """Print results to stdout."""
        ...

    # ── Path helpers ─────────────────────────────────────────────

    @staticmethod
    def _resolve(path: str, directory: str = ".") -> Path:
        """Return absolute Path; join with *directory* if relative."""
        p = Path(os.path.expanduser(path))
        if not p.is_absolute():
            p = Path(directory) / p
        return p

    def _check_file(self, path: Path, label: str = "") -> bool:
        """Return True if *path* exists; otherwise record an error."""
        if not path.exists():
            self.errors.append(f"{label} not found: {path}")
            return False
        return True

    # ── Parsing helpers ─────────────────────────────────────────

    @staticmethod
    def _float_after(line: str, sep: str) -> Optional[float]:
        """Extract float from *line* after the first occurrence of *sep*."""
        if sep not in line:
            return None
        rest = line.split(sep, 1)[1]
        for token in rest.split():
            try:
                return float(token)
            except ValueError:
                continue
        return None

    @staticmethod
    def _float_at(line: str, index: int = -1) -> Optional[float]:
        """Extract float at token *index* (0-based) from *line*."""
        try:
            return float(line.split()[index])
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _find_line(lines: List[str], keyword: str, last: bool = True) -> Optional[str]:
        """Return the first (or last) line containing *keyword*."""
        seq = reversed(lines) if last else iter(lines)
        for line in seq:
            if keyword in line:
                return line
        return None
