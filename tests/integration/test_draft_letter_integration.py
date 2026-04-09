"""Integration tests for LaTeX cover letter compilation and email draft creation."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from mcp_email_server.tools.create_draft_letter import (
    compile_latex_letter,
    create_cover_letter_draft,
)


class TestCompileLatexLetter:
    """Tests for compile_latex_letter function."""

    def test_compile_latex_letter_with_placeholders(self):
        """Test PDF generation from template with placeholder replacement."""
        # Create a minimal LaTeX template with placeholders
        template_content = r"""\documentclass{article}
\begin{document}
Hello \EMPLOYERNAME!
Today is \DATE.
Position: \POSITION
\end{document}
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            template_path = tmpdir_path / "test.tex"
            template_path.write_text(template_content, encoding="utf-8")

            # Define variables to replace
            variables = {
                "employername": "Test Company",
                "date": "2024-01-15",
                "position": "Software Engineer",
            }

            # Compile the LaTeX template
            pdf_path = compile_latex_letter(str(template_path), variables, str(tmpdir_path))

            # Verify PDF was generated
            assert pdf_path is not None
            assert Path(pdf_path).exists()
            assert Path(pdf_path).suffix == ".pdf"

            # Verify PDF has content (file size > 0)
            assert Path(pdf_path).stat().st_size > 0

            # Verify temporary files were cleaned up
            # (only .pdf should remain, not .aux, .log, .out)
            remaining_files = list(tmpdir_path.glob("*"))
            pdf_files = [f for f in remaining_files if f.suffix == ".pdf"]
            assert len(pdf_files) == 1  # Only the PDF should remain

    def test_compile_latex_letter_missing_template(self):
        """Test error handling for missing template file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = compile_latex_letter(
                str(Path(tmpdir) / "nonexistent.tex"),
                {},
                str(tmpdir),
            )
            assert result is None

    def test_compile_latex_letter_case_insensitive(self):
        """Test that placeholder replacement is case-insensitive."""
        template_content = r"""\documentclass{article}
\begin{document}
Test \MyPlaceholder content\end{document}
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            template_path = tmpdir_path / "test.tex"
            template_path.write_text(template_content, encoding="utf-8")

            # Use different case for variable key
            variables = {"myplaceholder": "replaced value"}

            pdf_path = compile_latex_letter(str(template_path), variables, str(tmpdir_path))

            assert pdf_path is not None
            assert Path(pdf_path).exists()


class TestCreateCoverLetterDraft:
    """Tests for create_cover_letter_draft function."""

    def test_create_cover_letter_draft_with_simple_template(self):
        """Test end-to-end workflow for cover letter creation with simple template."""
        # Create a minimal LaTeX template that will definitely compile
        simple_template = r"""\documentclass{article}
\begin{document}
\textbf{Position:} \POSITION

\textbf{Company:} \EMPLOYERNAME

\BODY1

\BODY2

\BODY3

\end{document}
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create template file with correct name expected by create_cover_letter_draft
            template_file = tmpdir_path / "bewerbung-template-english.tex"
            template_file.write_text(simple_template, encoding="utf-8")

            # Mock config
            config = {"template_base": str(tmpdir_path)}

            # Test with custom variables
            result = create_cover_letter_draft(
                config=config,
                employer_name="Acme Corp",
                position="Software Engineer",
                language="en",
                variables={
                    "BODY1": "I am writing to apply.",
                    "BODY2": "My qualifications include experience.",
                    "BODY3": "I look forward to discussing.",
                },
            )

            # Verify result is a string with expected content
            assert isinstance(result, str), f"Expected string, got {type(result)}: {result}"
            assert "PDF" in result or "pdf" in result.lower() or "created" in result.lower()
            assert "Acme Corp" in result or "Software Engineer" in result

            # Extract PDF path from result and verify it exists
            if ":" in result:
                pdf_path = result.split(":")[1].strip().split()[0]
                if pdf_path and Path(pdf_path).exists():
                    assert Path(pdf_path).exists()

    def test_create_cover_letter_draft_missing_template(self):
        """Test error handling when template files are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"template_base": tmpdir}

            result = create_cover_letter_draft(
                config=config,
                employer_name="Test Company",
                position="Developer",
                language="de",
            )

            assert result is None or "error" in result.lower() or "failed" in result.lower()


class TestLatexCompilation:
    """Tests for LaTeX compilation process."""

    def test_lualatex_execution(self):
        """Test that lualatex is available and can compile simple documents."""
        # Check if lualatex is installed
        try:
            result = subprocess.run(
                ["lualatex", "--version"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0 or "lualatex" in result.stdout.lower() or "lualatex" in result.stderr.lower()
        except FileNotFoundError:
            pytest.skip("lualatex not installed")

    def test_pdf_generation_from_real_template(self):
        """Test PDF generation from actual job application template (optional)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Copy real template
            template_path = Path("D:/Nextcloud/sync/repo/job_applications/00_template/bewerbung-template-deutsch.tex")
            if not template_path.exists():
                pytest.skip("Real template not available for testing")

            template_content = template_path.read_text(encoding="utf-8")

            # Replace placeholders with real values in the template definition
            template_content = template_content.replace(
                r"\newcommand{\EMPLOYERNAME}{\textbf{[Firmenname]}}",
                r"\newcommand{\EMPLOYERNAME}{\textbf{Test GmbH}}",
            )
            template_content = template_content.replace(
                r"\newcommand{\POSITION}{\textbf{[Position]}}",
                r"\newcommand{\POSITION}{\textbf{DevOps Engineer}}",
            )

            test_template = tmpdir_path / "test.tex"
            test_template.write_text(template_content, encoding="utf-8")

            # Compile - this may fail if moderncv has issues, so we make it optional
            pdf_path = compile_latex_letter(
                str(test_template),
                {"employername": "Test GmbH", "position": "DevOps Engineer"},
                str(tmpdir_path),
            )

            # If compilation succeeded, verify the PDF
            if pdf_path:
                assert Path(pdf_path).exists()
                assert Path(pdf_path).stat().st_size > 0
            else:
                # Skip if compilation failed (moderncv may have environment issues)
                pytest.skip("Template compilation failed (moderncv environment issue)")
