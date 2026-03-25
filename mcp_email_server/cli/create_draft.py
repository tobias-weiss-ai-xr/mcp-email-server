#!/usr/bin/env python3
"""CLI tool for creating cover letter drafts from LaTeX templates.

This module provides a command-line interface to create personalized cover
letter drafts using predefined LaTeX templates.
"""

from __future__ import annotations

import sys

import typer

from mcp_email_server.tools.create_draft_letter import create_cover_letter_draft

app = typer.Typer(help="Create cover letter drafts from LaTeX templates.")


@app.command()
def main(
    employer: str = typer.Option(..., "--employer", "-e", help="Company/employer name"),
    position: str = typer.Option(..., "--position", "-p", help="Job position/title"),
    language: str = typer.Option("de", "--language", "-l", help="Language (de or en)"),
    body1: str = typer.Option("", "--body1", "-1", help="First paragraph"),
    body2: str = typer.Option("", "--body2", "-2", help="Second paragraph"),
    body3: str = typer.Option("", "--body3", "-3", help="Third paragraph"),
    greeting: str | None = typer.Option(None, "--greeting", "-g", help="Custom greeting (optional)"),
) -> None:
    """Create a cover letter draft from LaTeX template.

    Generates a personalized cover letter PDF by filling in a LaTeX template
    with the provided information. The PDF is saved in the template directory's
    output folder.

    Example:
        create-draft --employer "Acme GmbH" --position "DevOps Engineer" --language de \\
            --body1 "Ich bewerbe mich um die Position..." --body2 "Meine Qualifikationen..."
    """
    # Validate language
    if language not in ["de", "en"]:
        typer.echo(f"Error: Invalid language '{language}'. Use 'de' or 'en'.", err=True)
        sys.exit(1)

    # Prepare configuration
    config: dict = {"template_base": "D:/Nextcloud/sync/repo/job_applications/00_template"}

    # Prepare variables
    variables: dict = {
        "BODY1": body1,
        "BODY2": body2,
        "BODY3": body3,
    }
    if greeting:
        variables["GREETING"] = greeting

    # Create draft
    result = create_cover_letter_draft(
        config=config,
        employer_name=employer,
        position=position,
        language=language,
        variables=variables,
    )

    if result:
        typer.echo(result)
    else:
        typer.echo("Error: Failed to create cover letter draft", err=True)
        sys.exit(1)


if __name__ == "__main__":
    app()
