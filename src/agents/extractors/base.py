"""Common utilities for extractor agents.

NOTE: With Claude Code agent architecture, most functionality here is obsolete.
Keeping minimal utilities that might be needed elsewhere.
"""
from pathlib import Path


def load_instructions(instructions_dir: Path, *filenames: str) -> str:
    """
    Load and concatenate instruction files.

    Args:
        instructions_dir: Base directory for instructions
        filenames: Instruction file names to load

    Returns:
        Concatenated instruction text

    Raises:
        FileNotFoundError: If instruction file missing
    """
    parts = []
    for filename in filenames:
        filepath = instructions_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Instruction file not found: {filepath}")
        parts.append(filepath.read_text())
    return "\n\n---\n\n".join(parts)
