import argparse
from pathlib import Path
import re
import sys

INDENT_LEVEL = "    "
INIT_MARKER = "<!-- init-tocs -->"
END_MARKER = "<!-- end-tocs -->"


# CommonMark ATX heading: up to 3 spaces of indentation, 1-6 '#', then a space,
# a tab or the end of the line.
HEADING_RE = re.compile(r" {0,3}(#{1,6})(?:[ \t](.*))?")


def parse_heading(line: str) -> tuple[int, str] | None:
    """Return (level, text) if the line is an ATX heading, otherwise None."""
    match = HEADING_RE.fullmatch(line)
    if not match:
        return None
    text = (match.group(2) or "").strip()
    # Drop the optional closing sequence ("# Title ##"), but keep "# C#".
    text = re.sub(r"(?:^|[ \t]+)#+$", "", text).strip()
    return len(match.group(1)), text


def create_toc_row(
    line: str, anchor_occurrences: dict[str, int], max_depth: int | None = None
):
    heading = parse_heading(line)
    if heading is None:
        return None

    hashes, line_content = heading
    if not line_content:
        return None

    if max_depth and hashes > max_depth:
        return None

    anchor = create_anchor(line_content)

    if anchor not in anchor_occurrences:
        anchor_occurrences[anchor] = 1
    else:
        anchor_occurrences[anchor] += 1
        anchor = anchor + "-" + str(anchor_occurrences[anchor] - 1)

    toc_row = f"{INDENT_LEVEL *(hashes-1)}- [{line_content}](#{anchor})"
    return toc_row


def create_anchor(line_content):
    anchor = re.sub(r"[^\w\-_ ]", "", line_content)
    return anchor.replace(" ", "-").lower()


# Fences may be indented (e.g. inside list items) and use backticks or tildes.
FENCE_RE = re.compile(r"\s*(`{3,}|~{3,})(.*)")


def update_open_fence(open_fence: str | None, line: str) -> str | None:
    """
    Track fenced code blocks.

    Returns the fence that opened the code block the line belongs to, or None
    when the line is outside any code block. A block opened with N backticks
    (or tildes) is closed only by a line with at least N of the same character
    followed by nothing but whitespace.
    """
    match = FENCE_RE.fullmatch(line)

    if open_fence is None:
        if not match:
            return None
        fence, info = match.groups()
        if fence[0] == "`" and "`" in info:
            # Not a fence but inline code on one line, such as ```code```.
            return None
        return fence

    if match:
        fence, rest = match.groups()
        if (
            fence[0] == open_fence[0]
            and len(fence) >= len(open_fence)
            and not rest.strip()
        ):
            return None

    return open_fence


def find_front_matter_end(lines: list[str]) -> int:
    """Index of the line closing a leading YAML front matter block, or -1."""
    if not lines or lines[0].rstrip() != "---":
        return -1
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip() in ("---", "..."):
            return i
    return -1


def exit_with_error(message: str):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def is_marker(line: str, marker: str) -> bool:
    """Markers count only as whole lines, so mentions in prose are ignored."""
    return line.strip() == marker


def generate_toc(original_lines: list[str], max_depth: int | None, clear_depth: bool):
    tocs = []
    init_toc_position = -1
    end_toc_position = -1
    open_fence: str | None = None
    anchor_occurrences: dict[str, int] = {}
    front_matter_end = find_front_matter_end(original_lines)

    for i, line in enumerate(original_lines):
        if i <= front_matter_end:
            continue

        in_code_block = open_fence is not None
        open_fence = update_open_fence(open_fence, line)

        # Skip fence lines and everything between them.
        if in_code_block or open_fence is not None:
            continue

        if is_marker(line, INIT_MARKER):
            if init_toc_position != -1:
                exit_with_error(f"Found more than one '{INIT_MARKER}' marker.")
            init_toc_position = i

            if clear_depth:
                continue

            if max_depth:
                tocs.append(f"<!-- depth={max_depth} -->")
            elif init_toc_position + 1 < len(original_lines):
                depth_match = re.fullmatch(
                    r"<!-- depth=(\d+) -->", original_lines[init_toc_position + 1]
                )
                if depth_match:
                    max_depth = int(depth_match.group(1))
                    tocs.append(f"<!-- depth={max_depth} -->")

        elif is_marker(line, END_MARKER):
            if end_toc_position != -1:
                exit_with_error(f"Found more than one '{END_MARKER}' marker.")
            end_toc_position = i
        else:
            toc_row = create_toc_row(line, anchor_occurrences, max_depth)
            if toc_row:
                tocs.append(toc_row)

    if (
        init_toc_position == -1
        or end_toc_position == -1
        or init_toc_position >= end_toc_position
    ):
        exit_with_error(
            "Missing or invalid TOC markers. "
            f"Add '{INIT_MARKER}' and '{END_MARKER}' to your file."
        )

    lines_before_tocs = original_lines[: init_toc_position + 1]
    lines_after_tocs = original_lines[end_toc_position:]
    return [lines_before_tocs, tocs, lines_after_tocs]


def read_lines_from(path):
    try:
        with open(path, "rt") as f:
            lines = f.read().splitlines()
    except (IOError, PermissionError) as e:
        print(f"Error while reading {path}: {e}", file=sys.stderr)
        sys.exit(1)

    return lines


def write_to(path, lines):
    try:
        with open(path, "w") as f:
            for l in lines:
                f.write(l + "\n")
    except (IOError, PermissionError) as e:
        print(f"Error while writing {path}: {e}", file=sys.stderr)
        sys.exit(1)


def process(
    path: Path,
    depth: int | None = None,
    dry_run: bool = False,
    clear_depth: bool = False,
):
    original_lines = read_lines_from(path)
    lines_before_tocs, tocs, lines_after_tocs = generate_toc(
        original_lines, depth, clear_depth
    )

    if dry_run:
        for t in tocs:
            print(t)
    else:
        write_to(path, lines_before_tocs + tocs + lines_after_tocs)


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
    parser.add_argument(
        "--clear-depth",
        action="store_true",
        help="Clear the max depth once it has been set and locked in the TOC marker",
    )
    parser.add_argument("--version", action="version", version="tocs 1.0.8")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print TOC to stdout without modifying the file",
    )
    args = parser.parse_args()
    path = Path(args.file).resolve()

    if not path.exists():
        print(f"Error: File '{args.file}' not found", file=sys.stderr)
        sys.exit(1)

    if args.depth is not None and args.depth < 1:
        print("Error: depth must be greater than 0", file=sys.stderr)
        sys.exit(1)

    process(path, args.depth, args.dry_run, args.clear_depth)


if __name__ == "__main__":
    main()
