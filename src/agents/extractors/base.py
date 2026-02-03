"""Common utilities for extractor agents."""
import time
import logging
from pathlib import Path
from typing import Callable, TypeVar, Any
from functools import wraps
from anthropic import Anthropic

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(max_retries: int = 3) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for exponential backoff retry logic.

    Args:
        max_retries: Maximum number of retry attempts

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts")
                        raise RuntimeError(f"{func.__name__} failed: {e}")
            raise RuntimeError(f"{func.__name__} exhausted retries")  # Should never reach here
        return wrapper
    return decorator


def upload_page_images(client: Anthropic, page_paths: list[Path]) -> list[str]:
    """
    Upload page images to Anthropic Files API.

    Args:
        client: Anthropic client instance
        page_paths: List of image file paths

    Returns:
        List of file IDs from API

    Raises:
        IOError: If file upload fails
    """
    file_ids = []
    for page_path in page_paths:
        with open(page_path, "rb") as f:
            file = client.files.create(file=f, purpose="vision")
            file_ids.append(file.id)
            logger.debug(f"Uploaded {page_path.name} -> {file.id}")
    return file_ids


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
