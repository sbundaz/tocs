import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tocs.main import INDENT_LEVEL, create_toc_entry, format_toc

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


def toc_row(line, anchor_occurrences):
    """Format a single heading as a TOC row, or None if it gets no entry."""
    entry = create_toc_entry(line, anchor_occurrences)
    return None if entry is None else format_toc([entry])[0]


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


def test_toc_row_h1():
    header = "# Hello World"

    result = toc_row(header, {})

    assert result == "- [Hello World](#hello-world)"


def test_format_toc_nests_by_level():
    occurrences = {}
    entries = [create_toc_entry(h, occurrences) for h in ["# A", "## B", "### C"]]

    assert format_toc(entries) == [
        "- [A](#a)",
        f"{INDENT_LEVEL}- [B](#b)",
        f"{INDENT_LEVEL}{INDENT_LEVEL}- [C](#c)",
    ]


def test_create_toc_with_hyphen():
    header = "# Hello-World"

    result = toc_row(header, {})

    assert result == "- [Hello-World](#hello-world)"


def test_create_toc_with_multiple_hyphens():
    header = "# Hello--World"

    result = toc_row(header, {})

    assert result == "- [Hello--World](#hello--world)"


def test_create_toc_with_underscore():
    header = "# Hello_World"

    result = toc_row(header, {})

    assert result == "- [Hello_World](#hello_world)"


def test_create_toc_with_multiple_underscore():
    header = "# Hello__World"

    result = toc_row(header, {})

    assert result == "- [Hello__World](#hello__world)"


def test_create_toc_remove_special_chars():
    header = "# Hello!?.:;'\"()[]{}@#$%^&*+=<>/\\|`~World"

    result = toc_row(header, {})

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
    assert create_toc_entry(line, {}) is None


def test_heading_with_up_to_three_leading_spaces():
    assert toc_row("   ## Indented", {}) == "- [Indented](#indented)"


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
    assert toc_row(line, {}) == expected


def test_heading_made_only_of_closing_hashes_is_empty():
    assert create_toc_entry("# ###", {}) is None


@pytest.mark.parametrize(
    "code_block",
    [
        "```python\n# comment\n``` \n",
        "~~~\n# comment\n~~~\n",
        "````md\n```\n# comment\n```\n````\n",
        "- item\n    ```bash\n    # comment\n    ```\n",
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


def test_yaml_front_matter_comments_are_not_headings(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text(
        "---\n# yaml comment\ntitle: x\n---\n"
        "<!-- init-tocs -->\n<!-- end-tocs -->\n# Real\n"
    )

    result = run_tocs(md)

    assert result.returncode == 0, result.stderr
    assert md.read_text() == (
        "---\n# yaml comment\ntitle: x\n---\n"
        "<!-- init-tocs -->\n- [Real](#real)\n<!-- end-tocs -->\n# Real\n"
    )


def test_headings_beyond_depth_still_count_for_duplicate_anchors(tmp_path):
    md = tmp_path / "doc.md"
    body = "# A\n## Usage\n### Usage\n## Usage\n"
    md.write_text(f"<!-- init-tocs -->\n<!-- end-tocs -->\n{body}")

    result = run_tocs(md, "--depth", "2")

    assert result.returncode == 0, result.stderr
    assert md.read_text() == (
        "<!-- init-tocs -->\n<!-- depth=2 -->\n- [A](#a)\n"
        "    - [Usage](#usage)\n    - [Usage](#usage-2)\n"
        f"<!-- end-tocs -->\n{body}"
    )


def test_duplicate_anchor_does_not_clash_with_numbered_heading():
    occurrences = {}

    rows = [toc_row(h, occurrences) for h in ["# Foo", "# Foo", "# Foo 1"]]

    assert rows == ["- [Foo](#foo)", "- [Foo](#foo-1)", "- [Foo 1](#foo-1-1)"]


@pytest.mark.parametrize(
    "headings, expected",
    [
        (["## A", "### B", "## C"], ["- [A](#a)", "    - [B](#b)", "- [C](#c)"]),
        (["# A", "### B", "# C"], ["- [A](#a)", "    - [B](#b)", "- [C](#c)"]),
        (["## A", "# B", "## C"], ["- [A](#a)", "- [B](#b)", "    - [C](#c)"]),
    ],
)
def test_format_toc_never_over_indents(headings, expected):
    occurrences = {}
    entries = [create_toc_entry(h, occurrences) for h in headings]

    assert format_toc(entries) == expected


@pytest.mark.parametrize(
    "line, expected",
    [
        (
            "# See [docs](http://x.y) and `code`",
            "- [See docs and `code`](#see-docs-and-code)",
        ),
        ("# Title <small>beta</small>", "- [Title <small>beta</small>](#title-beta)"),
    ],
)
def test_markdown_and_html_inside_headings(line, expected):
    assert toc_row(line, {}) == expected


def test_headings_above_the_toc_are_not_listed(tmp_path):
    md = tmp_path / "doc.md"
    body = "# Title\n## Usage\n"
    md.write_text(f"# Title\nintro\n<!-- init-tocs -->\n<!-- end-tocs -->\n{body}")

    result = run_tocs(md)

    assert result.returncode == 0, result.stderr
    assert md.read_text() == (
        "# Title\nintro\n<!-- init-tocs -->\n"
        "- [Title](#title-1)\n    - [Usage](#usage)\n"
        f"<!-- end-tocs -->\n{body}"
    )


@pytest.mark.parametrize(
    "lock", ["<!-- depth=1 --> ", "  <!--depth=1-->", "<!-- depth = 1 -->"]
)
def test_depth_lock_tolerates_whitespace(tmp_path, lock):
    md = tmp_path / "doc.md"
    md.write_text(f"<!-- init-tocs -->\n{lock}\n<!-- end-tocs -->\n# A\n## B\n")

    result = run_tocs(md)

    assert result.returncode == 0, result.stderr
    assert md.read_text() == (
        "<!-- init-tocs -->\n<!-- depth=1 -->\n- [A](#a)\n<!-- end-tocs -->\n"
        "# A\n## B\n"
    )


@pytest.mark.parametrize("lock", ["<!-- depth=0 -->", "<!-- depth=two -->"])
def test_invalid_depth_lock_is_reported_and_dropped(tmp_path, lock):
    md = tmp_path / "doc.md"
    md.write_text(f"<!-- init-tocs -->\n{lock}\n<!-- end-tocs -->\n# A\n## B\n")

    result = run_tocs(md)

    assert result.returncode == 0
    assert result.stderr.startswith("Warning: ignoring")
    assert lock in result.stderr
    assert md.read_text() == (
        "<!-- init-tocs -->\n- [A](#a)\n    - [B](#b)\n<!-- end-tocs -->\n"
        "# A\n## B\n"
    )


def test_depth_and_clear_depth_are_mutually_exclusive(tmp_path):
    md = fixture_copy(tmp_path, "lorem_ipsum_depth_2_input.md")

    result = run_tocs(md, "--depth", "1", "--clear-depth")

    assert result.returncode == 2
    assert "not allowed with argument" in result.stderr
    assert md.read_text() == read_fixture("lorem_ipsum_depth_2_input.md")


def test_non_utf8_file_is_reported_cleanly(tmp_path):
    md = tmp_path / "doc.md"
    md.write_bytes("<!-- init-tocs -->\n<!-- end-tocs -->\n# Caffè\n".encode("latin-1"))

    result = run_tocs(md)

    assert result.returncode == 1
    assert "is not valid UTF-8" in result.stderr
    assert "Traceback" not in result.stderr


def test_utf8_is_used_regardless_of_locale(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("<!-- init-tocs -->\n<!-- end-tocs -->\n# Caffè\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-X", "utf8=0", str(MAIN), str(md)],
        capture_output=True,
        text=True,
        env={
            "LC_ALL": "C",
            "LANG": "C",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONCOERCECLOCALE": "0",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "- [Caffè](#caffè)" in md.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "original, expected",
    [
        (
            "<!-- init-tocs -->\r\n<!-- end-tocs -->\r\n# A\r\n",
            "<!-- init-tocs -->\r\n- [A](#a)\r\n<!-- end-tocs -->\r\n# A\r\n",
        ),
        (
            "<!-- init-tocs -->\n<!-- end-tocs -->\n# A",
            "<!-- init-tocs -->\n- [A](#a)\n<!-- end-tocs -->\n# A",
        ),
        (
            "<!-- init-tocs -->\n<!-- end-tocs -->\n# A\npage\fbreak\n",
            "<!-- init-tocs -->\n- [A](#a)\n<!-- end-tocs -->\n# A\npage\fbreak\n",
        ),
    ],
    ids=["crlf", "no-final-newline", "form-feed"],
)
def test_file_formatting_is_preserved(tmp_path, original, expected):
    md = tmp_path / "doc.md"
    md.write_bytes(original.encode())

    result = run_tocs(md)

    assert result.returncode == 0, result.stderr
    assert md.read_bytes() == expected.encode()


def test_write_keeps_permissions_and_leaves_no_temp_files(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("<!-- init-tocs -->\n<!-- end-tocs -->\n# A\n")
    md.chmod(0o640)

    result = run_tocs(md)

    assert result.returncode == 0, result.stderr
    assert md.stat().st_mode & 0o777 == 0o640
    assert [p.name for p in tmp_path.iterdir()] == ["doc.md"]


def test_version_comes_from_package_metadata():
    from importlib.metadata import version

    result = run_tocs("--version")

    assert result.returncode == 0
    assert result.stdout == f"tocs {version('tocs')}\n"


def test_missing_file_is_reported(tmp_path):
    result = run_tocs(tmp_path / "missing.md")

    assert result.returncode == 1
    assert result.stderr == f"Error: File '{tmp_path / 'missing.md'}' not found\n"


def test_directory_is_rejected(tmp_path):
    result = run_tocs(tmp_path)

    assert result.returncode == 1
    assert result.stderr == f"Error: '{tmp_path}' is not a file\n"


@pytest.mark.parametrize(
    "args, body, depth",
    [
        ([], "# A\n## B\n### C\n", 3),
        (["--depth", "2"], "# A\n## B\n### C\n", 2),
        ([], "## A\n### B\n", 3),
    ],
)
def test_success_message_reports_depth_reached(tmp_path, args, body, depth):
    md = tmp_path / "doc.md"
    md.write_text(f"<!-- init-tocs -->\n<!-- end-tocs -->\n{body}")

    result = run_tocs(md, *args)

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"TOC updated in {md}: depth reached {depth}\n"


def test_success_message_without_headings(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("<!-- init-tocs -->\n<!-- end-tocs -->\ntext\n")

    result = run_tocs(md)

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"TOC updated in {md}: no headings found\n"


def test_dry_run_prints_only_the_toc(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("<!-- init-tocs -->\n<!-- end-tocs -->\n# A\n")

    result = run_tocs(md, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert result.stdout == "- [A](#a)\n"
