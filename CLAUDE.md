# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
**tocs** is a Python CLI tool that automatically generates table of contents (TOC) for markdown files by scanning headers and inserting links between `<!-- init-tocs -->` and `<!-- end-tocs -->` comment markers.

## Development Commands

### Environment Setup
- Create virtual environment: `python -m venv .venv`
- Activate environment: `source .venv/bin/activate`
- Install in development mode: `pip install -e .[dev]`

### Testing
- Run all tests: `pytest`
- Run specific test: `pytest tests/test_toc.py::test_lorem_ipsum`
- Tests use temporary files and subprocess calls to test the CLI

### Code Formatting
- Format code: `black .` (configured for 88-character line length)

### Package Management
- Build package: `python -m build`
- Install locally: `pip install -e .`

## Architecture

### Core Components
- `tocs/main.py`: Single-file CLI implementation containing all core logic
- `process()`: Main entry point that coordinates TOC generation
- `generate_toc()`: Core algorithm that parses markdown and builds TOC structure
- `create_toc_entry()`: Turns a heading line into a `TocEntry` (level, text, unique anchor)
- `format_toc()`: Renders entries as a nested list, indented relative to the shallowest heading
- `create_anchor()`: Converts header text to URL-safe anchor links

### Key Functions
- `update_open_fence()`: Tracks fenced code blocks (``` or ~~~, any length, possibly indented) so headers inside them are skipped
- `read_document()`/`write_document()`: UTF-8 file I/O that preserves line endings and the final newline; writes are atomic (temp file + `os.replace`)
- Anchor collision handling: Duplicate anchors get numbered suffixes (-1, -2, etc.)

### Test Structure
- Integration tests use `subprocess` to test actual CLI execution
- Fixture-based testing with input/output markdown files in `tests/fixtures/`
- Unit tests for individual functions like `create_toc_entry()` and `format_toc()`
- Parameterized tests for error conditions and edge cases

## Code Style
- Use `snake_case` for variables and functions, `PascalCase` for classes
- 4-space indentation (defined as `INDENT_LEVEL` constant)
- Error handling with descriptive messages to stderr and appropriate exit codes
