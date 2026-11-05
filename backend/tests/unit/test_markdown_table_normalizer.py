import pytest
from agent.orchestrator import normalize_markdown_tables


def test_normalize_clean_table():
    raw = "| Col A | Col B |\n|---|---|\n| 1 | 2 |"
    result = normalize_markdown_tables(raw)
    assert "| Col A | Col B |" in result
    assert "|---|---|" in result
    assert "| 1 | 2 |" in result


def test_normalize_malformed_delimiter_trailing_quote():
    raw = (
        "Some text before\n"
        "| Category | Key Points |\n"
        "|----------|------------|'\n"
        "| Physical | Aerosol particulates |\n"
        "Some text after"
    )
    result = normalize_markdown_tables(raw)
    # Trailing quote must be removed from delimiter
    assert "|----------|------------|'" not in result
    assert "|----------|------------|" in result
    # Must be separated by blank lines
    assert "\n\n| Category | Key Points |" in result
    assert "| Physical | Aerosol particulates |\n\nSome text after" in result


def test_normalize_unclosed_row_pipe():
    raw = (
        "| Col1 | Col2 |\n"
        "|---|---|\n"
        "| Row 1 | Val 1\n"
        "| Row 2 | Val 2 |"
    )
    result = normalize_markdown_tables(raw)
    lines = [line.strip() for line in result.strip().split("\n")]
    assert lines[2] == "| Row 1 | Val 1 |"
    assert lines[3] == "| Row 2 | Val 2 |"


def test_normalize_missing_columns_padded():
    raw = (
        "| H1 | H2 | H3 |\n"
        "|---|---|---|\n"
        "| OnlyOne |"
    )
    result = normalize_markdown_tables(raw)
    lines = [line.strip() for line in result.strip().split("\n")]
    assert lines[2] == "| OnlyOne |  |  |"
