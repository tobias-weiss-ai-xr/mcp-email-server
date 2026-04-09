"""LaTeX template compilation for cover letter drafts.

This module provides functionality to compile LaTeX templates with variable
substitution into PDF documents for job application cover letters.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from mcp_email_server.log import logger


def _run_latex_compilation(temp_file: Path, output_path: Path, pdf_path: Path) -> str | None:
    """Run lualatex compilation and return PDF path on success, None on failure."""
    logger.info(f"Compiling LaTeX: {temp_file.name} -> {pdf_path.name}")

    try:
        result = subprocess.run(  # noqa: S603
            ["lualatex", "-interaction=nonstopmode", "-output-directory", str(output_path), str(temp_file)],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        if result.returncode != 0:
            logger.error(f"LaTeX compilation failed: {result.stderr}")
            logger.debug(f"LaTeX stdout: {result.stdout}")
            if temp_file.exists():
                temp_file.unlink()
            return None

        if not pdf_path.exists():
            logger.error(f"PDF not generated: {pdf_path}")
            return None

        logger.info(f"PDF generated successfully: {pdf_path}")
        _clean_latex_aux_files(output_path, temp_file.stem)
        return str(pdf_path)

    except subprocess.TimeoutExpired:
        logger.error(f"LaTeX compilation timed out for {temp_file.name}")
        return None
    except FileNotFoundError:
        logger.error("lualatex not found. Please install TeX Live or MiKTeX.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during compilation: {e}")
        return None


def compile_latex_letter(template_path: str, variables: dict[str, str], output_dir: str) -> str | None:
    """Compile a LaTeX template into a PDF with variable substitution.

    Reads a LaTeX template file, replaces placeholders of the form \\KEY with
    corresponding variable values (case-insensitive matching), compiles the
    document using lualatex, and returns the path to the generated PDF.

    Args:
        template_path: Path to the LaTeX template file (.tex).
        variables: Dictionary mapping placeholder keys (without backslash) to
                   replacement values. Keys are matched case-insensitively.
        output_dir: Directory where the PDF and temporary files will be written.

    Returns:
        Path to the generated PDF file if compilation succeeds, None otherwise.
        Returns None if template doesn't exist, lualatex fails, or PDF not generated.

    Example:
        >>> template_vars = {
        ...     "employername": "Acme Corp",
        ...     "position": "Software Engineer",
        ...     "date": "2024-01-15"
        ... }
        >>> pdf_path = compile_latex_letter("template.tex", template_vars, "/output")
        >>> print(pdf_path)
        "/output/template.pdf"
    """
    template_file = Path(template_path)
    output_path = Path(output_dir)

    # Check if template exists
    if not template_file.exists():
        logger.error(f"Template file not found: {template_path}")
        return None

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Read template content
    try:
        content = template_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read template: {e}")
        return None

    # Replace placeholders (case-insensitive)
    # Pattern matches \KEY where KEY is any placeholder name
    for key, value in variables.items():
        # Escape special LaTeX characters in value
        escaped_value = _escape_latex_special_chars(value)

        # Replace \KEY with value (case-insensitive)
        # Pattern: backslash followed by the key (case-insensitive)
        pattern = r"\\" + re.escape(key) + r"(?![a-zA-Z@])"
        content = re.sub(pattern, escaped_value, content, flags=re.IGNORECASE)

    # Write modified content to temp file in output directory
    temp_file = output_path / template_file.name
    try:
        temp_file.write_text(content, encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to write modified template: {e}")
        return None

    # Compile with lualatex
    pdf_path = output_path / template_file.with_suffix(".pdf").name
    return _run_latex_compilation(temp_file, output_path, pdf_path)


def _escape_latex_special_chars(text: str) -> str:
    """Escape special LaTeX characters to prevent compilation errors.

    Args:
        text: Plain text to escape.

    Returns:
        Text with LaTeX special characters escaped.
    """
    # Order matters: escape backslash first
    replacements = {
        "\\": "\\textbackslash{}",
        "{": "\\{",
        "}": "\\}",
        "$": "\\$",
        "&": "\\&",
        "#": "\\#",
        "%": "\\%",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
        "_": "\\_",
        "<": "\\textless{}",
        ">": "\\textgreater{}",
        "|": "\\textbar{}",
        "¨": "\\textquotedbl{}",
    }

    result = text
    for char, escaped in replacements.items():
        result = result.replace(char, escaped)

    return result


def _clean_latex_aux_files(output_dir: Path, base_name: str) -> None:
    """Clean up LaTeX auxiliary files after compilation.

    Removes common LaTeX auxiliary files (.aux, .log, .out, .toc, etc.)
    while preserving the PDF.

    Args:
        output_dir: Directory containing the auxiliary files.
        base_name: Base name of the document (without extension).
    """
    extensions_to_remove = [".aux", ".log", ".out", ".toc", ".lof", ".lot", ".bbl", ".blg", ".fls", ".fdb_latexmk"]

    for ext in extensions_to_remove:
        aux_file = output_dir / f"{base_name}{ext}"
        if aux_file.exists():
            try:
                aux_file.unlink()
                logger.debug(f"Cleaned up auxiliary file: {aux_file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete {aux_file.name}: {e}")


def create_cover_letter_draft(
    config: dict[str, Any],
    employer_name: str,
    position: str,
    language: str = "de",
    variables: dict[str, str] | None = None,
) -> str | None:
    """Create a cover letter draft from LaTeX template.

    Generates a cover letter PDF by selecting the appropriate template
    (German or English), filling in standard fields (employer name, position,
    date, greeting), and merging with custom body text variables.

    Args:
        config: Configuration dictionary containing 'template_base' path to
                directory with LaTeX template files.
        employer_name: Name of the employer/company.
        position: Job position/title being applied for.
        language: Language code ("de" for German, "en" for English).
                 Defaults to "de".
        variables: Optional dictionary of additional variables to replace in
                   the template (e.g., BODY1, BODY2, BODY3 for letter content).
                  Must use uppercase keys matching template placeholders.

    Returns:
        Summary string containing PDF path and draft information if successful,
        None if template selection or compilation fails.

    Example:
        >>> config = {"template_base": "/path/to/templates"}
        >>> result = create_cover_letter_draft(
        ...     config=config,
        ...     employer_name="Acme GmbH",
        ...     position="DevOps Engineer",
        ...     language="de",
        ...     variables={
        ...         "BODY1": "Ich bewerbe mich um die Position...",
        ...         "BODY2": "Meine Qualifikationen umfassen...",
        ...         "BODY3": "Ich stehe für ein persönliches Gespräch zur Verfügung."
        ...     }
        ... )
        >>> print(result)
        "PDF created: /path/to/output/bewerbung.pdf\nEmployer: Acme GmbH\nPosition: DevOps Engineer"
    """
    # Get template base path
    template_base = config.get("template_base")
    if not template_base:
        logger.error("Config missing 'template_base' path")
        return None

    template_base_path = Path(template_base)
    if not template_base_path.exists():
        logger.error(f"Template base directory not found: {template_base}")
        return None

    # Select template based on language
    if language.lower() == "de":
        template_file = template_base_path / "bewerbung-template-deutsch.tex"
        greeting = "Sehr geehrte Damen und Herren,"
    elif language.lower() == "en":
        template_file = template_base_path / "bewerbung-template-english.tex"
        greeting = "Dear Hiring Manager,"
    else:
        logger.error(f"Unsupported language: {language}. Use 'de' or 'en'.")
        return None

    if not template_file.exists():
        logger.error(f"Template file not found: {template_file}")
        return None

    # Prepare variables
    template_variables = {
        "employername": employer_name,
        "position": position,
        "date": "\\today",
        "greeting": greeting,
    }

    # Merge custom variables (user-provided)
    if variables:
        for key, value in variables.items():
            # Ensure key is uppercase to match template placeholders
            template_variables[key.upper()] = value

    # Create output directory
    output_dir = template_base_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Compile LaTeX
    pdf_path = compile_latex_letter(str(template_file), template_variables, str(output_dir))

    if not pdf_path:
        logger.error(f"Failed to compile cover letter for {employer_name}")
        return None

    # Generate summary
    summary = f"""PDF created: {pdf_path}
Employer: {employer_name}
Position: {position}
Language: {language.upper()}
Date: {variables.get("date", "Today") if variables else "Today"}"""

    logger.info(f"Cover letter draft created: {summary}")
    return summary
