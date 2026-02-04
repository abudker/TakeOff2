"""Apply instruction proposals with version management."""

from pathlib import Path
from typing import Optional, Tuple
import re
import shutil
from datetime import datetime

from .critic import InstructionProposal


def parse_instruction_version(file_path: Path) -> str:
    """
    Extract version from instruction file header.

    Expected format in first 10 lines:
    # Verifier Instructions v1.2.3
    or
    # Instructions v1.0.0

    Returns "1.0.0" (without v prefix) or "1.0.0" if not found.
    """
    content = file_path.read_text()
    # Check first 10 lines only
    header = '\n'.join(content.split('\n')[:10])

    match = re.search(r'[Vv](\d+\.\d+\.\d+)', header)
    if match:
        return match.group(1)
    return "1.0.0"


def bump_version(current: str, bump_type: str) -> str:
    """
    Bump semantic version.

    Args:
        current: Current version (e.g., "1.2.3")
        bump_type: "major" | "minor" | "patch"

    Returns:
        New version string (e.g., "1.3.0")
    """
    parts = current.split('.')
    major = int(parts[0]) if len(parts) > 0 else 1
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump_type: {bump_type}")


def get_bump_type(change_type: str) -> str:
    """Map change_type to version bump type."""
    return {
        "add_section": "minor",
        "modify_section": "minor",
        "clarify_rule": "patch",
        "fix_typo": "patch",
        "restructure": "major",
    }.get(change_type, "patch")


def apply_version_to_content(content: str, new_version: str) -> str:
    """
    Update version number in instruction file content.

    Replaces first occurrence of vX.Y.Z with new version.
    If no version found, adds version to first heading.
    """
    # Try to replace existing version
    if re.search(r'[Vv]\d+\.\d+\.\d+', content):
        return re.sub(
            r'([Vv])\d+\.\d+\.\d+',
            rf'\g<1>{new_version}',
            content,
            count=1
        )

    # No version found - add to first heading
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('# '):
            lines[i] = f"{line} v{new_version}"
            break
    return '\n'.join(lines)


def save_instruction_snapshot(
    target_path: Path,
    iteration_dir: Path,
    version: str
) -> Path:
    """
    Save a copy of the instruction file to iteration directory.

    Args:
        target_path: Path to instruction file
        iteration_dir: Path to iteration folder (e.g., evals/x/results/iteration-002/)
        version: Current version before changes

    Returns:
        Path to saved snapshot
    """
    changes_dir = iteration_dir / "instruction-changes"
    changes_dir.mkdir(parents=True, exist_ok=True)

    # Build snapshot filename: agent-name-filename-vX.Y.Z.md
    agent_name = target_path.parent.name
    file_stem = target_path.stem
    snapshot_name = f"{agent_name}-{file_stem}-v{version}.md"

    snapshot_path = changes_dir / snapshot_name
    shutil.copy(target_path, snapshot_path)

    return snapshot_path


def apply_proposal(
    proposal: InstructionProposal,
    project_root: Path,
    iteration_dirs: list[Path] = None
) -> Tuple[str, str]:
    """
    Apply proposal to instruction file with version bump.

    Process:
    1. Read current content and version
    2. Save snapshot to iteration directories (if provided)
    3. Apply proposed change (append for add_section)
    4. Bump version in header
    5. Write updated file

    Args:
        proposal: The proposal to apply
        project_root: Project root directory
        iteration_dirs: List of iteration directories to save snapshots to

    Returns:
        Tuple of (old_version, new_version)
    """
    target_path = project_root / proposal.target_file

    if not target_path.exists():
        raise FileNotFoundError(f"Target file not found: {target_path}")

    # Read current content
    current_content = target_path.read_text()
    current_version = parse_instruction_version(target_path)

    # Save snapshots before modifying
    if iteration_dirs:
        for iter_dir in iteration_dirs:
            save_instruction_snapshot(target_path, iter_dir, current_version)

    # Apply change based on type
    if proposal.change_type == "add_section":
        # Append new section
        new_content = current_content.rstrip() + "\n\n" + proposal.proposed_change + "\n"
    elif proposal.change_type == "modify_section":
        # For modify, we append with a note - more sophisticated replacement
        # would require section markers or user guidance
        new_content = current_content.rstrip() + "\n\n" + proposal.proposed_change + "\n"
    else:
        # Default: append
        new_content = current_content.rstrip() + "\n\n" + proposal.proposed_change + "\n"

    # Bump version
    bump_type = get_bump_type(proposal.change_type)
    new_version = bump_version(current_version, bump_type)
    new_content = apply_version_to_content(new_content, new_version)

    # Write updated file
    target_path.write_text(new_content)

    return current_version, new_version


def rollback_instruction(
    target_path: Path,
    iteration_dir: Path,
    project_root: Path
) -> bool:
    """
    Rollback an instruction file to its state in a previous iteration.

    Args:
        target_path: Path to instruction file to rollback
        iteration_dir: Path to iteration folder containing snapshot
        project_root: Project root directory

    Returns:
        True if rollback succeeded, False if no snapshot found
    """
    changes_dir = iteration_dir / "instruction-changes"
    if not changes_dir.exists():
        return False

    # Find snapshot for this file
    agent_name = target_path.parent.name
    file_stem = target_path.stem
    pattern = f"{agent_name}-{file_stem}-v*.md"

    snapshots = list(changes_dir.glob(pattern))
    if not snapshots:
        return False

    # Use the snapshot (should be only one per iteration)
    snapshot = snapshots[0]
    shutil.copy(snapshot, target_path)
    return True
