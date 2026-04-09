from mcp_email_server.app import mcp


def test_create_cover_letter_draft_tool_exists():
    """Test that the create_cover_letter_draft tool is registered."""
    tool_names = [t.name for t in mcp._tool_manager._tools.values()]
    assert "create_cover_letter_draft" in tool_names
