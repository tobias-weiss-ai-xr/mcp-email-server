"""Tests for CLI create_draft command."""

import os
import tempfile

from typer.testing import CliRunner

from mcp_email_server.cli.create_draft import app

runner = CliRunner()

# Shared fake template base path for tests that don't exercise LaTeX compilation
_FAKE_TEMPLATE_BASE = tempfile.mkdtemp()


def test_create_draft_missing_required_args():
    """Test that CLI fails when required arguments are missing."""
    result = runner.invoke(app, [], env={**os.environ, "MCP_EMAIL_SERVER_TEMPLATE_BASE": _FAKE_TEMPLATE_BASE})

    assert result.exit_code != 0
    # Typer outputs to stderr when args are missing
    assert result.stderr is not None


def test_create_draft_invalid_language():
    """Test that CLI fails with invalid language."""
    result = runner.invoke(
        app,
        ["--employer", "Test Company", "--position", "DevOps", "--language", "fr"],
        env={**os.environ, "MCP_EMAIL_SERVER_TEMPLATE_BASE": "_FAKE_TEMPLATE_BASE"},
    )

    assert result.exit_code != 0
    # Check stderr for error message
    assert result.stderr is not None


def test_create_draft_basic_execution(monkeypatch):
    """Test basic CLI execution with mocked create_cover_letter_draft."""
    mock_result = "PDF created: /path/to/output/bewerbung-template-deutsch.pdf\nEmployer: Test Company\nPosition: DevOps Engineer\nLanguage: DE\nDate: Today"

    def mock_create_draft(*args, **kwargs):
        return mock_result

    monkeypatch.setattr(
        "mcp_email_server.cli.create_draft.create_cover_letter_draft",
        mock_create_draft,
    )

    result = runner.invoke(
        app,
        [
            "--employer",
            "Test Company",
            "--position",
            "DevOps Engineer",
            "--language",
            "de",
        ],
        env={**os.environ, "MCP_EMAIL_SERVER_TEMPLATE_BASE": "_FAKE_TEMPLATE_BASE"},
    )

    assert result.exit_code == 0
    assert "PDF created" in result.stdout
    assert "Test Company" in result.stdout
    assert "DevOps Engineer" in result.stdout


def test_create_draft_with_all_options(monkeypatch):
    """Test CLI with all options provided."""
    mock_result = "PDF created successfully"
    call_args_container = {}

    def mock_create_draft(*args, **kwargs):
        call_args_container.update(kwargs)
        return mock_result

    monkeypatch.setattr(
        "mcp_email_server.cli.create_draft.create_cover_letter_draft",
        mock_create_draft,
    )

    result = runner.invoke(
        app,
        [
            "--employer",
            "Acme GmbH",
            "--position",
            "Senior DevOps Engineer",
            "--language",
            "en",
            "--body1",
            "I am writing to apply...",
            "--body2",
            "My qualifications include...",
            "--body3",
            "I look forward to discussing...",
            "--greeting",
            "Dear Hiring Manager,",
        ],
        env={**os.environ, "MCP_EMAIL_SERVER_TEMPLATE_BASE": "_FAKE_TEMPLATE_BASE"},
    )

    assert result.exit_code == 0
    assert call_args_container

    # Verify the function was called with correct arguments
    assert call_args_container["employer_name"] == "Acme GmbH"
    assert call_args_container["position"] == "Senior DevOps Engineer"
    assert call_args_container["language"] == "en"
    assert call_args_container["variables"]["BODY1"] == "I am writing to apply..."
    assert call_args_container["variables"]["BODY2"] == "My qualifications include..."
    assert call_args_container["variables"]["BODY3"] == "I look forward to discussing..."
    assert call_args_container["variables"]["GREETING"] == "Dear Hiring Manager,"


def test_create_draft_failure_case(monkeypatch):
    """Test CLI when create_cover_letter_draft returns None (failure)."""

    def mock_create_draft(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "mcp_email_server.cli.create_draft.create_cover_letter_draft",
        mock_create_draft,
    )

    result = runner.invoke(
        app,
        ["--employer", "Test Company", "--position", "DevOps"],
        env={**os.environ, "MCP_EMAIL_SERVER_TEMPLATE_BASE": "_FAKE_TEMPLATE_BASE"},
    )

    assert result.exit_code != 0
    assert "Failed to create cover letter draft" in result.stderr


def test_create_draft_english_language(monkeypatch):
    """Test CLI with English language option."""
    mock_result = "PDF created: /path/to/output/bewerbung-template-english.pdf"

    def mock_create_draft(*args, **kwargs):
        return mock_result

    monkeypatch.setattr(
        "mcp_email_server.cli.create_draft.create_cover_letter_draft",
        mock_create_draft,
    )

    result = runner.invoke(
        app,
        [
            "--employer",
            "Tech Corp",
            "--position",
            "ML Engineer",
            "--language",
            "en",
        ],
        env={**os.environ, "MCP_EMAIL_SERVER_TEMPLATE_BASE": "_FAKE_TEMPLATE_BASE"},
    )

    assert result.exit_code == 0
    assert (
        "bewerbung-template-english.pdf" in result.stdout
        or "English" in result.stdout
        or "ML Engineer" in result.stdout
    )
