"""Tests for the SnippetLibrary module."""

import pytest
from pathlib import Path
import tempfile

from mcp_email_server.tools.snippet_library import SnippetLibrary


def test_snippet_library_loading():
    """Test loading snippets from markdown file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test snippet file
        snippet_file = tmpdir_path / "letter-snippets-de.md"
        snippet_file.write_text(
            """
# Test Snippets

## Test Category
\\BODY1 := Test body text

## Another Category
\\BODY2 := Another test paragraph
""",
            encoding="utf-8",
        )

        lib = SnippetLibrary(str(tmpdir_path))
        lib.load_snippets("de")

        assert lib.get_snippet("de", "BODY1") == "Test Category: Test body text"
        assert lib.get_snippet("de", "BODY2") == "Another Category: Another test paragraph"
        assert lib.get_snippet("de", "BODY3") == ""  # Not defined


def test_snippet_library_missing_file():
    """Test handling of missing snippet file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        lib = SnippetLibrary(str(Path(tmpdir)))
        lib.load_snippets("de")

        assert lib.get_snippet("de", "BODY1") == ""


def test_list_categories():
    """Test listing categories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        snippet_file = tmpdir_path / "letter-snippets-de.md"
        snippet_file.write_text(
            """
# Test

## Category A
\\BODY1 := Text A

## Category B
\\BODY2 := Text B
""",
            encoding="utf-8",
        )

        lib = SnippetLibrary(str(tmpdir_path))
        categories = lib.list_categories("de")

        assert "Category A" in categories
        assert "Category B" in categories


def test_get_all_snippets():
    """Test retrieving all snippets for a language."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        snippet_file = tmpdir_path / "letter-snippets-en.md"
        snippet_file.write_text(
            """
# English Snippets

## DevOps
\\BODY1 := DevOps text

## AI
\\BODY2 := AI text
""",
            encoding="utf-8",
        )

        lib = SnippetLibrary(str(tmpdir_path))
        lib.load_snippets("en")

        assert lib.get_snippet("en", "BODY1") == "DevOps: DevOps text"
        assert lib.get_snippet("en", "BODY2") == "AI: AI text"
