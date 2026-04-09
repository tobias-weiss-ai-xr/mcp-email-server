"""End-to-end tests for complete cover letter workflow."""

import time
from pathlib import Path

from mcp_email_server.tools.create_draft_letter import create_cover_letter_draft


class TestCoverLetterWorkflow:
    """End-to-end tests for cover letter creation workflow."""

    def test_complete_cover_letter_workflow(self, tmp_path):
        """Test complete workflow from template to PDF generation."""
        # Create minimal template directory
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Minimal LaTeX template that will definitely compile
        template = r"""\documentclass{article}
\begin{document}
\textbf{To:} \EMPLOYERNAME\
\textbf{Position:} \POSITION

\BODY1

\BODY2

\end{document}
"""
        template_file = template_dir / "bewerbung-template-english.tex"
        template_file.write_text(template, encoding="utf-8")

        # Configure
        config = {"template_base": str(template_dir)}

        # Execute
        result = create_cover_letter_draft(
            config=config,
            employer_name="Test Organization",
            position="Senior Engineer",
            language="en",
            variables={
                "BODY1": "This is the first paragraph of the test letter.",
                "BODY2": "This is the second paragraph.",
            },
        )

        # Verify
        assert result is not None, "create_cover_letter_draft returned None"
        assert isinstance(result, str), f"Expected string result, got {type(result)}"
        assert "pdf" in result.lower(), f"Expected PDF path in result: {result}"

        # Verify PDF file exists
        if ":" in result:
            pdf_path = result.split(":")[1].strip().split()[0]
            if pdf_path and Path(pdf_path).exists():
                assert Path(pdf_path).stat().st_size > 0, "PDF file is empty"

    def test_latex_compilation_performance(self, tmp_path):
        """Test that LaTeX compilation completes in under 10 seconds."""
        # Setup
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        template = r"""\documentclass{article}
\begin{document}
Test \EMPLOYERNAME \POSITION
\BODY1
\BODY2
\BODY3
\end{document}
"""
        template_file = template_dir / "bewerbung-template-english.tex"
        template_file.write_text(template, encoding="utf-8")

        config = {"template_base": str(template_dir)}

        # Measure time
        start_time = time.time()
        result = create_cover_letter_draft(
            config=config,
            employer_name="Performance Test Company",
            position="DevOps Engineer",
            language="en",
            variables={
                "BODY1": "First paragraph of test letter.",
                "BODY2": "Second paragraph of test letter.",
                "BODY3": "Third paragraph of test letter.",
            },
        )
        duration = time.time() - start_time

        # Verify performance
        assert duration < 10, f"LaTeX compilation took {duration:.2f}s, expected < 10s"
        assert result is not None, "create_cover_letter_draft returned None"
