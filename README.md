# tocs
**tocs** is a simple CLI application written in Python that generates **the table of contents (TOC)** section for markdown files.<br>
As a person who loves to write personal technical notes in markdown files, I needed something simple to use.

## How to install and use tocs
**Prerequisites:** Python 3.11.9+

### Installation
```bash
pip install tocs
```

### Basic usage:
- `tocs input_file.md` - Generate TOC for the file
- `tocs --help` - Show usage instructions
- `tocs --version` - Display version information

### tocs example
Given the following markdown file **input_file.md**:
```md
# header 1
Lorem ipsum dolor sit amet...

## header 2
Lorem ipsum dolor sit amet...

### header 3
Lorem ipsum dolor sit amet...
```

Add two tags where you want the TOCs table:
```md
<!-- init-tocs -->
<!-- end-tocs -->

# header 1
Lorem ipsum dolor sit amet...

## header 2
Lorem ipsum dolor sit amet...

### header 3
Lorem ipsum dolor sit amet...
```

Run `tocs input_file.md` and here's the output:

```md
<!-- init-tocs -->
- [header 1](#header-1)
    - [header 2](#header-2)
        - [header 3](#header-3)

<!-- end-tocs -->

# header 1
Lorem ipsum dolor sit amet...

## header 2
Lorem ipsum dolor sit amet...

### header 3
Lorem ipsum dolor sit amet...
```

## Development
- create venv: `python -m venv .venv`
- activate venv: `source .venv/bin/activate`
- install project and dependencies (editable mode): `pip install -e .[dev]`
- deactivate venv: `deactivate`