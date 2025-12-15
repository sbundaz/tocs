import shutil
import subprocess
import tempfile
import pytest
from tocs.main import INDENT_LEVEL, create_toc_row


def test_lorem_ipsum():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md") as tmp:
        shutil.copy("tests/fixtures/lorem_ipsum_input.md", tmp.name)

        result = subprocess.run(
            ["python3", "tocs/main.py", tmp.name], capture_output=True, text=True
        )

        assert result.returncode == 0

        with open(tmp.name) as f:
            actual = f.read()

        with open("tests/fixtures/lorem_ipsum_output.md") as f:
            expected = f.read()

        assert actual == expected


def test_lorem_ipsum_depth_2():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md") as tmp:
        shutil.copy("tests/fixtures/lorem_ipsum_depth_2_input.md", tmp.name)

        result = subprocess.run(
            ["python3", "tocs/main.py", tmp.name, "--depth", "2"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        with open(tmp.name) as f:
            actual = f.read()

        with open("tests/fixtures/lorem_ipsum_depth_2_output.md") as f:
            expected = f.read()

        assert actual == expected


def test_lorem_ipsum_with_invalid_depth():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md") as tmp:
        shutil.copy("tests/fixtures/lorem_ipsum_depth_2_input.md", tmp.name)

        result = subprocess.run(
            ["python3", "tocs/main.py", tmp.name, "--depth", "0"],
            capture_output=True,
            text=True,
        )

        print(result)

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
def test_invalid_toc_configuration(fixture_file_name):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md") as tmp:
        shutil.copy(f"tests/fixtures/{fixture_file_name}", tmp.name)

        result = subprocess.run(
            ["python3", "tocs/main.py", tmp.name], capture_output=True, text=True
        )

        assert result.returncode == 1
        assert (
            result.stderr
            == "Error: Missing or invalid TOC markers. Add '<!-- init-tocs -->' and '<!-- end-tocs -->' to your file.\n"
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


def test_dry_run():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md") as tmp:
        shutil.copy("tests/fixtures/lorem_ipsum_input.md", tmp.name)

        result = subprocess.run(
            ["python3", "tocs/main.py", tmp.name, "--dry-run"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Verify file was not modified
        with open(tmp.name) as f:
            actual = f.read()

        with open("tests/fixtures/lorem_ipsum_input.md") as f:
            expected = f.read()

        assert actual == expected
        assert "- [Header 1](#header-1)" in result.stdout
