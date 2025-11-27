from toc import create_toc_row


def test_create_toc_row_h1():
    header = "# Hello World"

    result = create_toc_row(header)

    assert result == "- [Hello World](#hello-world)"

def test_create_toc_row_h2():
    header = "## Hello World"

    result = create_toc_row(header)

    assert result == "\t- [Hello World](#hello-world)"


def test_create_toc_row_h3():
    header = "### Hello World"

    result = create_toc_row(header)

    assert result == "\t\t- [Hello World](#hello-world)"