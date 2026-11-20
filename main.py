"""Place the finished front page where the grader reads it.

The grader runs this file from the repository root, with Python 3.13, without
network access, and reads the image from /output/entry.png. Outside the
grader, MAKEFUN_OUTPUT_DIR names the directory instead:

    MAKEFUN_OUTPUT_DIR=out python3 main.py

The page itself is committed as entry.png; this program only moves a copy of
it into place, so every run produces the same bytes.
"""

import os
import shutil
import sys
from pathlib import Path

DESTINATION_NAME = "entry.png"
DEFAULT_OUTPUT = "/output"


def source_path() -> Path:
    """The committed page, beside this file."""
    return Path(__file__).resolve().parent / "entry.png"


def output_dir() -> Path:
    """Where the grader expects the page; MAKEFUN_OUTPUT_DIR overrides it."""
    return Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or DEFAULT_OUTPUT)


def copy_page(src: Path, dest_dir: Path) -> Path:
    """Copy the page into dest_dir, creating it if needed, and return the copy."""
    if not src.is_file():
        raise SystemExit(f"cannot find the committed page at {src}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / DESTINATION_NAME
    shutil.copyfile(src, target)
    return target


def main(argv: list[str] | None = None) -> int:
    src = source_path()
    dest = copy_page(src, output_dir())
    size = dest.stat().st_size
    print(f"copied {src.name} ({size} bytes) to {dest}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
