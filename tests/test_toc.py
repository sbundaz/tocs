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
