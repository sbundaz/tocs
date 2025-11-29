import shutil
import subprocess
import tempfile
import pytest
from toc.main import create_toc_row

INDENT_LEVEL = "    "

def test_lorem_ipsum():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md") as tmp:
        shutil.copy("tests/fixtures/lorem_ipsum_input.md", tmp.name)

        result = subprocess.run(
            ["python3", "toc/main.py", tmp.name], capture_output=True, text=True
        )

        assert result.returncode == 0

        with open(tmp.name) as f:
            actual = f.read()

        with open("tests/fixtures/lorem_ipsum_output.md") as f:
            expected = f.read()

        assert actual == expected


@pytest.mark.parametrize(
    "fixture_file_name",
    [
        "wrong_toc_config_init.md",
        "wrong_toc_config_end.md",
        "wrong_toc_config_order.md",
    ],
)
def test_invalid_toc_configuration(fixture_file_name):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md") as tmp:
        shutil.copy(f"tests/fixtures/{fixture_file_name}", tmp.name)

        result = subprocess.run(
            ["python3", "toc/main.py", tmp.name], capture_output=True, text=True
        )

        assert result.returncode == 1
        assert (
            result.stderr
            == "Error: Missing or invalid TOC markers. Add '<!-- init-toc -->' and '<!-- end-toc -->' to your file.\n"
        )

def test_create_toc_row_h1():
    header = "# Hello World"

    result = create_toc_row(header)

    assert result == "- [Hello World](#hello-world)"


def test_create_toc_row_h2():
    header = "## Hello World"

    result = create_toc_row(header)

    assert result == f"{INDENT_LEVEL}- [Hello World](#hello-world)"


def test_create_toc_row_h3():
    header = "### Hello World"

    result = create_toc_row(header)

    assert result == f"{INDENT_LEVEL}{INDENT_LEVEL}- [Hello World](#hello-world)"

def test_create_toc_with_hyphen():
    header = "# Hello-World"

    result = create_toc_row(header)

    assert result == "- [Hello-World](#hello-world)"

def test_create_toc_with_multiple_hyphens():
    header = "# Hello--World"

    result = create_toc_row(header)

    assert result == "- [Hello--World](#hello--world)"

def test_create_toc_with_underscore():
    header = "# Hello_World"

    result = create_toc_row(header)

    assert result == "- [Hello_World](#hello_world)"

def test_create_toc_with_multiple_underscore():
    header = "# Hello__World"

    result = create_toc_row(header)

    assert result == "- [Hello__World](#hello__world)"

def test_create_toc_remove_special_chars():
    header = "# Hello!?.:;'\"()[]{}@#$%^&*+=<>/\\|`~World"

    result = create_toc_row(header)

    assert result == "- [Hello!?.:;'\"()[]{}@#$%^&*+=<>/\\|`~World](#helloworld)"
    