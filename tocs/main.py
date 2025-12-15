import argparse
from pathlib import Path
import re
import sys

INDENT_LEVEL = "    "


def create_toc_row(line: str, max_depth: int = None) -> str:
    hashes = 0
    j = 0

    while line[j] == "#":
        hashes += 1
        j += 1

    if max_depth and hashes > max_depth:
        return None

    line_content = line[hashes + 1 :]
    anchor = create_anchor(line_content)
    toc_row = f"{INDENT_LEVEL *(hashes-1)}- [{line_content}](#{anchor})"
    return toc_row


def create_anchor(line_content: str) -> str:
    anchor = re.sub(r"[^a-zA-Z0-9\-_ ]", "", line_content)
    return anchor.replace(" ", "-").lower()


def toggle_ignore_rows_flag(ignore_rows: bool, line: str):
    """
    Controls whether to ignore rows inside code snippets that start with ```.
    Also handles multiline snippets.
    """
    if line == "```":
        return not ignore_rows
    elif line.startswith("```") and not line.endswith("```"):
        return True
    elif line.startswith("```") and line.endswith("```"):
        return False
    else:
        return ignore_rows


def process_file(path, depth=None):
    lines = []
    tocs = []
    init_toc_position = -1
    end_toc_position = -1
    ignore_rows = False

    try:
        with open(path, "rt") as f:
            lines = f.read().splitlines()
    except (IOError, PermissionError) as e:
        print(f"Error while reading {path}: {e}", file=sys.stderr)
        sys.exit(1)

    for i, line in enumerate(lines):
        ignore_rows = toggle_ignore_rows_flag(ignore_rows, line)

        if ignore_rows:
            continue

        if "<!-- init-tocs -->" in line:
            init_toc_position = i
        elif "<!-- end-tocs -->" in line:
            end_toc_position = i
        elif line.startswith("#"):
            toc_row = create_toc_row(line, depth)
            if toc_row:
                tocs.append(toc_row)

    if (
        init_toc_position == -1
        or end_toc_position == -1
        or init_toc_position >= end_toc_position
    ):
        print(
            f"Error: Missing or invalid TOC markers. Add '<!-- init-tocs -->' and '<!-- end-tocs -->' to your file.",
            file=sys.stderr,
        )
        sys.exit(1)

    lines_before_tocs = lines[: init_toc_position + 1]
    lines_after_tocs = lines[end_toc_position:]
    new_lines = lines_before_tocs + tocs + lines_after_tocs

    try:
        with open(path, "w") as f:
            for l in new_lines:
                f.write(l + "\n")
    except (IOError, PermissionError) as e:
        print(f"Error while writing {path}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="tocs",
        description="Generate table of contents for markdown files",
        epilog="""
  Examples:
    tocs /path/to/file.md                    Generate TOC in file.md

  Requirements:
    The file must contain <!-- init-tocs --> and <!-- end-tocs --> markers.
  """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("file", help="Markdown file to process")
    parser.add_argument(
        "--depth", type=int, help="Maximum header depth to include in TOC"
    )
    parser.add_argument("--version", action="version", version="tocs 1.0.4")
    args = parser.parse_args()
    path = Path(args.file).resolve()

    if not path.exists():
        print(f"Error: File '{args.file}' not found", file=sys.stderr)
        sys.exit(1)

    if args.depth is not None and args.depth < 1:
        print(f"Error: depth must be greater than 0", file=sys.stderr)
        sys.exit(1)

    process_file(path, args.depth)


if __name__ == "__main__":
    main()
