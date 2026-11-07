import argparse
from importlib.metadata import PackageNotFoundError, version
import os
import shutil
import tempfile
from pathlib import Path
import re
import sys
from typing import NamedTuple

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


class TocEntry(NamedTuple):
    level: int
    text: str
    anchor: str


def create_toc_entry(
    line: str, anchor_occurrences: dict[str, int], max_depth: int | None = None
) -> TocEntry | None:
    heading = parse_heading(line)
    if heading is None:
        return None

    level, text = heading
    # A link inside the TOC link would be invalid Markdown: keep its text only.
    text = strip_links(text)
    if not text:
        return None

    # Every heading gets an anchor on the rendered page, including the ones
    # left out of the TOC, so count it before applying the depth limit.
    anchor = unique_anchor(create_anchor(text), anchor_occurrences)

    if max_depth and level > max_depth:
        return None

    return TocEntry(level, text, anchor)


def format_toc(entries: list[TocEntry]) -> list[str]:
    """
    Render entries as a nested list.

    Nesting is relative to the shallowest heading and grows by at most one
    level per row: a list item indented by 4+ spaces more than allowed (a
    document without H1, or an H1 followed by an H3) renders as a code block.
    """
    if not entries:
        return []

    base_level = min(entry.level for entry in entries)
    rows = []
    previous_depth = -1
    for entry in entries:
        depth = min(entry.level - base_level, previous_depth + 1)
        rows.append(f"{INDENT_LEVEL * depth}- [{entry.text}](#{entry.anchor})")
        previous_depth = depth
    return rows


def unique_anchor(anchor: str, anchor_occurrences: dict[str, int]) -> str:
    """
    Make the anchor unique the way GitHub does (github-slugger): append -1, -2,
    ... until the result has not been used, including by a heading whose own
    text already ends with a number.
    """
    original = anchor
    while anchor in anchor_occurrences:
        anchor_occurrences[original] += 1
        anchor = f"{original}-{anchor_occurrences[original]}"
    anchor_occurrences[anchor] = 0
    return anchor


LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")


def strip_links(text: str) -> str:
    """Replace [text](url) links and ![alt](src) images with their text."""
    return LINK_RE.sub(r"\1", text)


def create_anchor(line_content):
    # GitHub builds the anchor from the rendered text, so drop link targets
    # and HTML tags before removing punctuation.
    line_content = HTML_TAG_RE.sub("", strip_links(line_content))
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


DEPTH_LOCK_RE = re.compile(r"\s*<!--\s*depth\s*=\s*(\d+)\s*-->\s*")


def read_depth_lock(line: str) -> int | None:
    """Return the depth stored in a '<!-- depth=N -->' line, if valid."""
    match = DEPTH_LOCK_RE.fullmatch(line)
    if match is None:
        if re.match(r"\s*<!--\s*depth", line):
            print(
                f"Warning: ignoring malformed depth lock '{line.strip()}'",
                file=sys.stderr,
            )
        return None

    depth = int(match.group(1))
    if depth < 1:
        print(
            f"Warning: ignoring depth lock '{line.strip()}', "
            "depth must be greater than 0",
            file=sys.stderr,
        )
        return None
    return depth


def generate_toc(original_lines: list[str], max_depth: int | None, clear_depth: bool):
    tocs = []
    entries: list[TocEntry] = []
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
                locked_depth = read_depth_lock(original_lines[init_toc_position + 1])
                if locked_depth:
                    max_depth = locked_depth
                    tocs.append(f"<!-- depth={max_depth} -->")

        elif is_marker(line, END_MARKER):
            if end_toc_position != -1:
                exit_with_error(f"Found more than one '{END_MARKER}' marker.")
            end_toc_position = i
        elif init_toc_position != -1 and end_toc_position == -1:
            # Old TOC content: it is about to be replaced.
            continue
        else:
            entry = create_toc_entry(line, anchor_occurrences, max_depth)
            # Headings above the TOC (e.g. the document title) keep their
            # anchor, which affects duplicates, but are not listed.
            if entry and end_toc_position != -1:
                entries.append(entry)

    if (
        init_toc_position == -1
        or end_toc_position == -1
        or init_toc_position >= end_toc_position
    ):
        exit_with_error(
            "Missing or invalid TOC markers. "
            f"Add '{INIT_MARKER}' and '{END_MARKER}' to your file."
        )

    tocs.extend(format_toc(entries))
    lines_before_tocs = original_lines[: init_toc_position + 1]
    lines_after_tocs = original_lines[end_toc_position:]
    return [lines_before_tocs, tocs, lines_after_tocs]


class Document(NamedTuple):
    lines: list[str]
    newline: str
    trailing_newline: bool


def read_document(path: Path) -> Document:
    """Read a file keeping track of its line ending and final newline."""
    try:
        with open(path, "rt", encoding="utf-8", newline="") as f:
            content = f.read()
    except UnicodeDecodeError as e:
        exit_with_error(f"{path} is not valid UTF-8 ({e.reason} at byte {e.start})")
    except OSError as e:
        exit_with_error(f"Could not read {path}: {e}")

    newline = "\r\n" if "\r\n" in content else "\n"
    # Split on newlines only: str.splitlines() also splits on form feeds,
    # U+2028 and other characters that must be written back unchanged.
    lines = content.replace("\r\n", "\n").split("\n")
    trailing_newline = lines[-1] == ""
    if trailing_newline:
        lines.pop()
    return Document(lines, newline, trailing_newline)


def write_document(path: Path, document: Document):
    """Replace the file atomically, so an interrupted write cannot truncate it."""
    content = document.newline.join(document.lines)
    if document.trailing_newline:
        content += document.newline

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        shutil.copymode(path, tmp_path)
        os.replace(tmp_path, path)
    except OSError as e:
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        exit_with_error(f"Could not write {path}: {e}")


def process(
    path: Path,
    depth: int | None = None,
    dry_run: bool = False,
    clear_depth: bool = False,
):
    original = read_document(path)
    lines_before_tocs, tocs, lines_after_tocs = generate_toc(
        original.lines, depth, clear_depth
    )

    if dry_run:
        for t in tocs:
            print(t)
    else:
        lines = lines_before_tocs + tocs + lines_after_tocs
        write_document(path, original._replace(lines=lines))


def get_version() -> str:
    """Single source of truth: the version declared in pyproject.toml."""
    try:
        return version("tocs")
    except PackageNotFoundError:
        return "unknown"


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
    depth_options = parser.add_mutually_exclusive_group()
    depth_options.add_argument(
        "--depth", type=int, help="Maximum header depth to include in TOC"
    )
    depth_options.add_argument(
        "--clear-depth",
        action="store_true",
        help="Clear the max depth once it has been set and locked in the TOC marker",
    )
    parser.add_argument("--version", action="version", version=f"tocs {get_version()}")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print TOC to stdout without modifying the file",
    )
    args = parser.parse_args()
    path = Path(args.file).resolve()

    if not path.exists():
        exit_with_error(f"File '{args.file}' not found")

    if not path.is_file():
        exit_with_error(f"'{args.file}' is not a file")

    if args.depth is not None and args.depth < 1:
        exit_with_error("depth must be greater than 0")

    process(path, args.depth, args.dry_run, args.clear_depth)


if __name__ == "__main__":
    main()
