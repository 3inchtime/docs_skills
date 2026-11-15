#!/usr/bin/env python3
"""Inline the bundled flow reader CSS/JS in a marked HTML template.

This is an asset inliner, not a complete website crawler or browser validator.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile
import os


STYLE_MARKER = '<link rel="stylesheet" href="flow-reader.css" data-flow-inline="style">'
SCRIPT_MARKER = '<script src="flow-reader.js" defer data-flow-inline="script"></script>'
ASSETS = Path(__file__).resolve().parent.parent / "assets"


def render(template: str, style: str, script: str) -> str:
    for label, marker in (("style", STYLE_MARKER), ("script", SCRIPT_MARKER)):
        count = template.count(marker)
        if count != 1:
            raise ValueError(f"Expected exactly one {label} marker; found {count}.")
    if "</style" in style.lower() or "</script" in script.lower():
        raise ValueError("Bundled assets contain an HTML closing tag and cannot be inlined safely.")
    return template.replace(STYLE_MARKER, f"<style>\n{style}\n</style>").replace(
        SCRIPT_MARKER, f'<script type="module">\n{script}\n</script>'
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Destination HTML file.")
    parser.add_argument(
        "--template", type=Path, default=ASSETS / "flow-reader.example.html",
        help="HTML template containing the two exact asset markers; defaults to the synthetic example.",
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing output file.")
    args = parser.parse_args(argv)
    temporary = None
    try:
        template_path = args.template.resolve(strict=True)
        destination = args.output.absolute()
        protected = {template_path, (ASSETS / "flow-reader.css").resolve(), (ASSETS / "flow-reader.js").resolve()}
        if destination.resolve() in protected:
            raise ValueError("Output must not replace the source template or bundled assets.")
        if destination.is_symlink():
            raise ValueError("Output must not be a symbolic link.")
        if destination.exists() and not args.force:
            raise FileExistsError(f"Output already exists: {destination}; use --force to replace it.")
        result = render(
            template_path.read_text(encoding="utf-8"),
            (ASSETS / "flow-reader.css").read_text(encoding="utf-8"),
            (ASSETS / "flow-reader.js").read_text(encoding="utf-8"),
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=".flow-reader-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(result)
        if args.force:
            os.replace(temporary, destination)
        else:
            # Link atomically refuses a racing destination; both paths share a filesystem.
            os.link(temporary, destination)
            temporary.unlink()
        temporary = None
        print(f"Created {destination}")
        print("Inlined the bundled CSS and JS. Verify any other resources and browser behavior separately.")
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
