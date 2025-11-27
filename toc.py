from pathlib import Path
import sys


def create_toc_row(line: str) -> str:
    hashes = 0
    j = 0

    while line[j] == "#":
        hashes+=1
        j+=1

    line_content = line[hashes + 1:]
    anchor = line_content.replace(" ", "-").lower()
    toc_row = f"{'\t'*(hashes-1)}- [{line_content}](#{anchor})"
    return toc_row

def main():
    path = Path(Path(__file__).parent, "source.md")
    lines = []
    tocs = []
    init_toc_position = -1
    end_toc_position = -1

    with open(path, "rt") as f:
        lines = f.read().splitlines()

    for i, line in enumerate(lines):
        if "<!-- init-toc -->" in line:
            init_toc_position = i
        elif "<!-- end-toc -->" in line:
            end_toc_position = i
        elif line.startswith("#"):
            tocs.append(create_toc_row(line))

    if init_toc_position == -1 or end_toc_position == -1 or init_toc_position >= end_toc_position:
        print(f"The toc configuration is not valid. (init_toc_position: {init_toc_position}, end_toc_position: {end_toc_position}) ")
        sys.exit(1)

    lines_before_tocs = lines[:init_toc_position+1]
    lines_after_tocs = lines[end_toc_position:]
    new_lines = lines_before_tocs + tocs + lines_after_tocs
    print("#===== line before tocs")
    for l in new_lines:
        print(l)

    with open(path, "w") as f:
        for l in new_lines:
            f.write(l+"\n")


if __name__ == "__main__":
    main()