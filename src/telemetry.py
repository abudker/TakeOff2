"""Lightweight performance telemetry for extraction pipelines.

Usage:
    tel = Telemetry()

    with tel.span("discovery"):
        run_discovery(...)

    with tel.span("orientation"):
        with tel.span("pass1"):
            ...
        with tel.span("pass2"):
            ...

    print(tel.summary())
"""
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional


class Telemetry:
    """Tracks named timing spans with nesting support."""

    def __init__(self):
        self.spans: List[Dict] = []
        self._stack: List[str] = []  # current nesting path
        self._start_time = time.monotonic()

    @contextmanager
    def span(self, name: str):
        """Time a named block. Supports nesting via context stack."""
        parent = "/".join(self._stack) if self._stack else None
        full_name = f"{parent}/{name}" if parent else name
        entry = {
            "name": name,
            "full_name": full_name,
            "parent": parent,
            "start": time.monotonic(),
            "end": None,
            "duration": None,
        }
        self.spans.append(entry)
        self._stack.append(name)
        try:
            yield entry
        finally:
            entry["end"] = time.monotonic()
            entry["duration"] = entry["end"] - entry["start"]
            self._stack.pop()

    def total_seconds(self) -> float:
        """Wall-clock time since telemetry was created."""
        return time.monotonic() - self._start_time

    def summary(self) -> str:
        """Return formatted timing table."""
        total = self.total_seconds()
        if total == 0:
            return "No timing data."

        lines = []
        lines.append("")
        lines.append("TIMING BREAKDOWN")
        lines.append("\u2500" * 52)
        lines.append(f"{'Stage':<30} {'Duration':>9} {'% Total':>9}")
        lines.append("\u2500" * 52)

        for span in self.spans:
            dur = span["duration"]
            if dur is None:
                continue
            pct = (dur / total) * 100
            indent = "  " if span["parent"] else ""
            prefix = "\u251c\u2500 " if span["parent"] else ""
            name = f"{indent}{prefix}{span['name']}"
            lines.append(f"{name:<30} {dur:>8.1f}s {pct:>8.1f}%")

        lines.append("\u2500" * 52)
        lines.append(f"{'Total':<30} {total:>8.1f}s")
        lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Return JSON-serializable timing data."""
        def build_tree(spans: List[Dict], parent: Optional[str] = None) -> List[Dict]:
            children = [s for s in spans if s["parent"] == parent]
            result = []
            for s in children:
                entry = {
                    "name": s["name"],
                    "duration_seconds": round(s["duration"], 3) if s["duration"] else None,
                }
                nested = build_tree(spans, s["full_name"])
                if nested:
                    entry["children"] = nested
                result.append(entry)
            return result

        return {
            "total_seconds": round(self.total_seconds(), 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spans": build_tree(self.spans),
        }
