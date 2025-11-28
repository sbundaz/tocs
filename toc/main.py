from pathlib import Path
import sys

INDENT_LEVEL = "    "


def create_toc_row(line: str) -> str:
    hashes = 0
    j = 0

    while line[j] == "#":
        hashes += 1
        j += 1

    line_content = line[hashes + 1 :]
    anchor = line_content.replace(" ", "-").lower()
    toc_row = f"{INDENT_LEVEL *(hashes-1)}- [{line_content}](#{anchor})"
    return toc_row


def main(path):
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
            f"Error: Missing or invalid TOC markers. Add '<!-- init-toc -->' and '<!-- end-toc -->' to your file.", file=sys.stderr
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Select a file!", file=sys.stderr)
        sys.exit(1)

    parameter_path = sys.argv[1]
    path = ""

    if parameter_path.startswith("/"):  # absolute path
        path = Path(parameter_path)
    else:  # relative path
        path = Path(Path(__file__).parent / parameter_path)

    if not path.exists():
        print(f"File {path} not found", file=sys.stderr)
        sys.exit(1)

    main(path)
