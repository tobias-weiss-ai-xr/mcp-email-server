"""Snippet library for reusable cover letter content."""

from pathlib import Path
from typing import Dict, List, Optional
import re


class SnippetLibrary:
    """Load and retrieve cover letter snippets from markdown files."""

    def __init__(self, base_path: str):
        """Initialize snippet library.

        Args:
            base_path: Path to directory containing snippet files.
        """
        self.base_path = Path(base_path)
        self._snippets: Dict[str, Dict[str, Dict[str, str]]] = {}

    def load_snippets(self, language: str) -> None:
        """Load snippets for a specific language.

        Args:
            language: Language code ('de' or 'en').
        """
        if language in self._snippets:
            return  # Already loaded

        snippet_file = self.base_path / f"letter-snippets-{language}.md"
        if not snippet_file.exists():
            return

        content = snippet_file.read_text(encoding="utf-8")
        self._snippets[language] = self._parse_snippets(content)

    def _parse_snippets(self, content: str) -> Dict[str, Dict[str, str]]:
        """Parse markdown content into snippet dictionary.

        Args:
            content: Markdown file content.

        Returns:
            Dictionary mapping categories to variable names and snippet text.
        """
        snippets: Dict[str, Dict[str, str]] = {}
        sections = content.split("##")

        for section in sections[1:]:  # Skip first (title)
            lines = section.strip().split("\n")
            if len(lines) < 2:
                continue

            # First line is category, rest is content
            category = lines[0].strip()
            content_lines = lines[1:]

            # Find variable assignment
            for line in content_lines:
                match = re.match(
                    r"\\(BODY[123])\s*:=\s*(.+)", line.strip(), re.IGNORECASE
                )
                if match:
                    var_name, body_text = match.groups()
                    if category not in snippets:
                        snippets[category] = {}
                    snippets[category][var_name] = body_text.strip()

        return snippets

    def get_snippet(self, language: str, category: str, var_name: str) -> str:
        """Get a specific snippet.

        Args:
            language: Language code ('de' or 'en').
            category: Snippet category (e.g., 'DevOps & Cloud').
            var_name: Variable name (e.g., 'BODY1').

        Returns:
            Snippet text or empty string if not found.
        """
        if language not in self._snippets:
            self.load_snippets(language)

        snippets = self._snippets.get(language, {})
        if category in snippets and var_name in snippets[category]:
            return f"{category}: {snippets[category][var_name]}"
        return ""

    def get_all_snippets_for_language(self, language: str) -> Dict[str, Dict[str, str]]:
        """Get all snippets for a language.

        Args:
            language: Language code ('de' or 'en').

        Returns:
            Dictionary of all snippets organized by category.
        """
        if language not in self._snippets:
            self.load_snippets(language)

        return self._snippets.get(language, {})

    def list_categories(self, language: str) -> List[str]:
        """List available categories for a language.

        Args:
            language: Language code ('de' or 'en').

        Returns:
            List of category names.
        """
        if language not in self._snippets:
            self.load_snippets(language)

        return sorted(self._snippets.get(language, {}).keys())
