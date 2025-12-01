import argparse
from pathlib import Path
import re
import sys

INDENT_LEVEL = "    "


def create_toc_row(line: str) -> str:
    hashes = 0
    j = 0

    while line[j] == "#":
        hashes += 1
        j += 1

    line_content = line[hashes + 1 :]
    anchor = create_anchor(line_content)
    toc_row = f"{INDENT_LEVEL *(hashes-1)}- [{line_content}](#{anchor})"
    return toc_row


def create_anchor(line_content: str) -> str:
    anchor = re.sub(r"[^a-zA-Z0-9\-_ ]", "", line_content)
    return anchor.replace(" ", "-").lower()


def process_file(path):
    lines = []
    tocs = []
    init_toc_position = -1
    end_toc_position = -1

    try:
        with open(path, "rt") as f:
            lines = f.read().splitlines()
    except (IOError, PermissionError) as e:
        print(f"Error while reading {path}: {e}", file=sys.stderr)
        sys.exit(1)

    for i, line in enumerate(lines):
        if "<!-- init-toc -->" in line:
            init_toc_position = i
        elif "<!-- end-toc -->" in line:
            end_toc_position = i
        elif line.startswith("#"):
            tocs.append(create_toc_row(line))

    if (
        init_toc_position == -1
        or end_toc_position == -1
        or init_toc_position >= end_toc_position
    ):
        print(
            f"Error: Missing or invalid TOC markers. Add '<!-- init-toc -->' and '<!-- end-toc -->' to your file.",
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
        prog="toc",
        description="Generate table of contents for markdown files",
        epilog="""
  Examples:
    toc /path/to/file.md                    Generate TOC in file.md

  Requirements:
    The file must contain <!-- init-toc --> and <!-- end-toc --> markers.
  """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("file", help="Markdown file to process")
    parser.add_argument("--version", action="version", version="toc 1.0.0")
    args = parser.parse_args()
    path = Path(args.file).resolve()

    if not path.exists():
        print(f"Error: File '{args.file}' not found", file=sys.stderr)
        sys.exit(1)

    process_file(path)


if __name__ == "__main__":
    main()
