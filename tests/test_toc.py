import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tocs.main import INDENT_LEVEL, create_toc_row

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
MAIN = ROOT / "tocs" / "main.py"

MARKERS_ERROR = (
    "Error: Missing or invalid TOC markers. "
    "Add '<!-- init-tocs -->' and '<!-- end-tocs -->' to your file.\n"
)


def run_tocs(*args):
    return subprocess.run(
        [sys.executable, str(MAIN), *map(str, args)],
        capture_output=True,
        text=True,
    )


def fixture_copy(tmp_path, name):
    target = tmp_path / name
    shutil.copy(FIXTURES / name, target)
    return target


def read_fixture(name):
    return (FIXTURES / name).read_text()


def test_lorem_ipsum(tmp_path):
    md = fixture_copy(tmp_path, "lorem_ipsum_input.md")

    result = run_tocs(md)

    assert result.returncode == 0
    assert md.read_text() == read_fixture("lorem_ipsum_output.md")


def test_lorem_ipsum_depth_2(tmp_path):
    md = fixture_copy(tmp_path, "lorem_ipsum_depth_2_input.md")

    result = run_tocs(md, "--depth", "2")

    assert result.returncode == 0
    assert md.read_text() == read_fixture("lorem_ipsum_depth_2_output.md")


def test_multiple_headers(tmp_path):
    md = fixture_copy(tmp_path, "multiple_headers_input.md")

    result = run_tocs(md)

    assert result.returncode == 0
    assert md.read_text() == read_fixture("multiple_headers_output.md")


def test_lorem_ipsum_with_invalid_depth(tmp_path):
    md = fixture_copy(tmp_path, "lorem_ipsum_depth_2_input.md")

    result = run_tocs(md, "--depth", "0")

    assert result.returncode == 1
    assert result.stderr == "Error: depth must be greater than 0\n"


@pytest.mark.parametrize(
    "fixture_file_name",
    [
        "wrong_toc_config_init.md",
        "wrong_toc_config_end.md",
        "wrong_toc_config_order.md",
    ],
)
def test_invalid_toc_configuration(tmp_path, fixture_file_name):
    md = fixture_copy(tmp_path, fixture_file_name)

    result = run_tocs(md)

    assert result.returncode == 1
    assert result.stderr == MARKERS_ERROR


def test_create_toc_row_h1():
    header = "# Hello World"

    result = create_toc_row(header, {})

    assert result == "- [Hello World](#hello-world)"


def test_create_toc_row_h2():
    header = "## Hello World"

    result = create_toc_row(header, {})

    assert result == f"{INDENT_LEVEL}- [Hello World](#hello-world)"


def test_create_toc_row_h3():
    header = "### Hello World"

    result = create_toc_row(header, {})

    assert result == f"{INDENT_LEVEL}{INDENT_LEVEL}- [Hello World](#hello-world)"


def test_create_toc_with_hyphen():
    header = "# Hello-World"

    result = create_toc_row(header, {})

    assert result == "- [Hello-World](#hello-world)"


def test_create_toc_with_multiple_hyphens():
    header = "# Hello--World"

    result = create_toc_row(header, {})

    assert result == "- [Hello--World](#hello--world)"


def test_create_toc_with_underscore():
    header = "# Hello_World"

    result = create_toc_row(header, {})

    assert result == "- [Hello_World](#hello_world)"


def test_create_toc_with_multiple_underscore():
    header = "# Hello__World"

    result = create_toc_row(header, {})

    assert result == "- [Hello__World](#hello__world)"


def test_create_toc_remove_special_chars():
    header = "# Hello!?.:;'\"()[]{}@#$%^&*+=<>/\\|`~World"

    result = create_toc_row(header, {})

    assert result == "- [Hello!?.:;'\"()[]{}@#$%^&*+=<>/\\|`~World](#helloworld)"


def test_depth_lock_persists_across_runs(tmp_path):
    md = fixture_copy(tmp_path, "lorem_ipsum_depth_2_input.md")

    assert run_tocs(md, "--depth", "2").returncode == 0
    assert run_tocs(md).returncode == 0

    assert md.read_text() == read_fixture("lorem_ipsum_depth_2_output.md")


def test_clear_depth_removes_lock(tmp_path):
    md = fixture_copy(tmp_path, "lorem_ipsum_depth_2_input.md")

    assert run_tocs(md, "--depth", "2").returncode == 0
    assert run_tocs(md, "--clear-depth").returncode == 0

    assert md.read_text() == read_fixture("lorem_ipsum_depth_2_cleared_output.md")


def test_init_tocs_as_last_line_returns_standard_error(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("<!-- init-tocs -->")

    result = run_tocs(md)

    assert result.returncode == 1
    assert result.stderr == MARKERS_ERROR


def test_dry_run(tmp_path):
    md = fixture_copy(tmp_path, "lorem_ipsum_input.md")

    result = run_tocs(md, "--dry-run")

    assert result.returncode == 0
    assert md.read_text() == read_fixture("lorem_ipsum_input.md")
    assert "- [Header 1](#header-1)" in result.stdout


def test_marker_mentioned_in_text_is_not_a_marker(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text(
        "<!-- init-tocs -->\n<!-- end-tocs -->\n"
        "# A\nIMPORTANT TEXT\n## B\nsee <!-- end-tocs --> marker\n"
    )

    result = run_tocs(md)

    assert result.returncode == 0
    assert md.read_text() == (
        "<!-- init-tocs -->\n- [A](#a)\n    - [B](#b)\n<!-- end-tocs -->\n"
        "# A\nIMPORTANT TEXT\n## B\nsee <!-- end-tocs --> marker\n"
    )


@pytest.mark.parametrize("marker", ["<!-- init-tocs -->", "<!-- end-tocs -->"])
def test_duplicate_marker_is_rejected_without_touching_the_file(tmp_path, marker):
    md = tmp_path / "doc.md"
    original = f"<!-- init-tocs -->\n<!-- end-tocs -->\n# A\ntext\n{marker}\n"
    md.write_text(original)

    result = run_tocs(md)

    assert result.returncode == 1
    assert result.stderr == f"Error: Found more than one '{marker}' marker.\n"
    assert md.read_text() == original


@pytest.mark.parametrize(
    "line",
    ["#", "###", "#hashtag", "####### seven hashes", "    # indented code"],
)
def test_lines_that_are_not_toc_headings(line):
    assert create_toc_row(line, {}) is None


def test_heading_with_up_to_three_leading_spaces():
    assert (
        create_toc_row("   ## Indented", {}) == f"{INDENT_LEVEL}- [Indented](#indented)"
    )


def test_hash_only_line_does_not_crash(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("<!-- init-tocs -->\n<!-- end-tocs -->\n###\n#hashtag\n# A\n")

    result = run_tocs(md)

    assert result.returncode == 0, result.stderr
    assert md.read_text() == (
        "<!-- init-tocs -->\n- [A](#a)\n<!-- end-tocs -->\n###\n#hashtag\n# A\n"
    )


@pytest.mark.parametrize(
    "line, expected",
    [
        ("# Title  ", "- [Title](#title)"),
        ("#  Two spaces", "- [Two spaces](#two-spaces)"),
        ("#\tTab", "- [Tab](#tab)"),
        ("# Closed #", "- [Closed](#closed)"),
        ("# Closed ###   ", "- [Closed](#closed)"),
        ("# C#", "- [C#](#c)"),
    ],
)
def test_heading_whitespace_and_closing_hashes(line, expected):
    assert create_toc_row(line, {}) == expected


def test_heading_made_only_of_closing_hashes_is_empty():
    assert create_toc_row("# ###", {}) is None


@pytest.mark.parametrize(
    "code_block",
    [
        "```python\n# comment\n``` \n",  # closing fence with trailing space
        "~~~\n# comment\n~~~\n",
        "````md\n```\n# comment\n```\n````\n",  # shorter fence inside a longer one
        "- item\n    ```bash\n    # comment\n    ```\n",  # fence inside a list item
    ],
)
def test_headings_inside_code_blocks_are_ignored(tmp_path, code_block):
    md = tmp_path / "doc.md"
    body = f"# Before\n{code_block}# After\n"
    md.write_text(f"<!-- init-tocs -->\n<!-- end-tocs -->\n{body}")

    result = run_tocs(md)

    assert result.returncode == 0, result.stderr
    assert md.read_text() == (
        "<!-- init-tocs -->\n- [Before](#before)\n- [After](#after)\n"
        f"<!-- end-tocs -->\n{body}"
    )


def test_markers_after_code_block_with_trailing_space_are_found(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("```\ncode\n``` \n<!-- init-tocs -->\n<!-- end-tocs -->\n# A\n")

    result = run_tocs(md)

    assert result.returncode == 0, result.stderr
