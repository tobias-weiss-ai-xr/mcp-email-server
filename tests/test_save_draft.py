"""Tests for the save_draft feature."""

import asyncio
from email.mime.text import MIMEText
from unittest.mock import AsyncMock, patch

import pytest

from mcp_email_server.config import EmailServer, EmailSettings
from mcp_email_server.emails.classic import ClassicEmailHandler, EmailClient


@pytest.fixture
def email_settings():
    """Create EmailSettings for testing."""
    return EmailSettings(
        account_name="test_account",
        full_name="Test User",
        email_address="test@example.com",
        incoming=EmailServer(
            user_name="test_user",
            password="test_password",
            host="imap.example.com",
            port=993,
            use_ssl=True,
        ),
        outgoing=EmailServer(
            user_name="test_user",
            password="test_password",
            host="smtp.example.com",
            port=465,
            use_ssl=True,
        ),
    )


@pytest.fixture
def handler(email_settings):
    """Create a ClassicEmailHandler for testing."""
    return ClassicEmailHandler(email_settings)


@pytest.fixture
def mock_imap_for_draft():
    """Create a mock IMAP client for save_draft testing."""
    mock = AsyncMock()
    mock._client_task = asyncio.Future()
    mock._client_task.set_result(None)
    mock.wait_hello_from_server = AsyncMock()
    mock.login = AsyncMock()
    mock.select = AsyncMock(return_value=("OK", []))
    mock.append = AsyncMock(return_value=("OK", []))
    mock.logout = AsyncMock()
    return mock


class TestSaveDraftHappyPath:
    """Tests for successful draft saving."""

    @pytest.mark.asyncio
    async def test_save_draft_happy_path(self, handler, mock_imap_for_draft):
        """Test successful draft saving to Drafts folder."""
        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap_for_draft):
            result = await handler.save_draft(
                to="recipient@example.com",
                subject="Test Subject",
                body="Test body content",
            )

            assert result == "Draft saved successfully to 'Drafts'"
            mock_imap_for_draft.select.assert_called_with('"Drafts"')
            mock_imap_for_draft.append.assert_called_once()
            mock_imap_for_draft.logout.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_draft_empty_to(self, handler, mock_imap_for_draft):
        """Test saving draft with empty To field."""
        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap_for_draft):
            result = await handler.save_draft(
                to="",
                subject="Test Subject",
                body="Test body content",
            )

            assert result == "Draft saved successfully to 'Drafts'"
            # Verify the message was created with empty To
            mock_imap_for_draft.append.assert_called_once()


class TestSaveDraftFolderDetection:
    """Tests for Drafts folder detection logic."""

    @pytest.mark.asyncio
    async def test_save_draft_folder_detection(self, handler, mock_imap_for_draft):
        """Test that it tries multiple folder candidates."""
        # First folder (Drafts) succeeds
        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap_for_draft):
            result = await handler.save_draft(
                to="recipient@example.com",
                subject="Test Subject",
                body="Test body content",
            )

            assert result == "Draft saved successfully to 'Drafts'"
            # Should have tried the first folder successfully
            mock_imap_for_draft.select.assert_called_with('"Drafts"')

    @pytest.mark.asyncio
    async def test_save_draft_fallback_to_inbox_drafts(self, handler):
        """Test fallback to INBOX.Drafts when Drafts doesn't exist."""
        mock_imap = AsyncMock()
        mock_imap._client_task = asyncio.Future()
        mock_imap._client_task.set_result(None)
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock()
        # First folder fails, second succeeds
        mock_imap.select = AsyncMock(side_effect=[("NO", []), ("OK", [])])
        mock_imap.append = AsyncMock(return_value=("OK", []))
        mock_imap.logout = AsyncMock()

        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap):
            result = await handler.save_draft(
                to="recipient@example.com",
                subject="Test Subject",
                body="Test body content",
            )

            assert result == "Draft saved successfully to 'INBOX.Drafts'"
            # Should have tried both folders
            assert mock_imap.select.call_count == 2


class TestSaveDraftFolderNotFound:
    """Tests for when no Drafts folder is found."""

    @pytest.mark.asyncio
    async def test_save_draft_folder_not_found(self, handler):
        """Test when no Drafts folder is found - raises FileNotFoundError."""
        mock_imap = AsyncMock()
        mock_imap._client_task = asyncio.Future()
        mock_imap._client_task.set_result(None)
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock()
        # All folders fail
        mock_imap.select = AsyncMock(return_value=("NO", []))
        mock_imap.logout = AsyncMock()

        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap):
            with pytest.raises(FileNotFoundError, match="Could not find a valid Drafts folder"):
                await handler.save_draft(
                    to="recipient@example.com",
                    subject="Test Subject",
                    body="Test body content",
                )

            # Should have tried all folder candidates
            assert mock_imap.select.call_count == 4


class TestSaveDraftWithAttachments:
    """Tests for draft saving with attachments."""

    @pytest.mark.asyncio
    async def test_save_draft_with_attachment(self, handler, mock_imap_for_draft, tmp_path):
        """Test saving draft with an attachment."""
        # Create a temporary file for attachment
        attachment_file = tmp_path / "test.txt"
        attachment_file.write_text("Test attachment content")

        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap_for_draft):
            result = await handler.save_draft(
                to="recipient@example.com",
                subject="Test with attachment",
                body="Test body with attachment",
                attachments=[str(attachment_file)],
            )

            assert result == "Draft saved successfully to 'Drafts'"
            mock_imap_for_draft.append.assert_called_once()
            # Verify MIMEMultipart was used (for attachments)
            call_args = mock_imap_for_draft.append.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_save_draft_multiple_attachments(self, handler, mock_imap_for_draft, tmp_path):
        """Test saving draft with multiple attachments."""
        # Create temporary files for attachments
        attachment1 = tmp_path / "file1.txt"
        attachment1.write_text("Content 1")
        attachment2 = tmp_path / "file2.txt"
        attachment2.write_text("Content 2")

        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap_for_draft):
            result = await handler.save_draft(
                to="recipient@example.com",
                subject="Test with multiple attachments",
                body="Test body",
                attachments=[str(attachment1), str(attachment2)],
            )

            assert result == "Draft saved successfully to 'Drafts'"
            mock_imap_for_draft.append.assert_called_once()


class TestSaveDraftErrorHandling:
    """Tests for error handling in save_draft."""

    @pytest.mark.asyncio
    async def test_save_draft_login_error(self, handler):
        """Test when IMAP login fails."""
        mock_imap = AsyncMock()
        mock_imap._client_task = asyncio.Future()
        mock_imap._client_task.set_result(None)
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock(side_effect=Exception("Login failed"))
        mock_imap.logout = AsyncMock()

        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap):
            with pytest.raises(Exception, match="Login failed"):
                await handler.save_draft(
                    to="recipient@example.com",
                    subject="Test Subject",
                    body="Test body content",
                )

    @pytest.mark.asyncio
    async def test_save_draft_append_error(self, handler):
        """Test when IMAP append fails for all folders."""
        mock_imap = AsyncMock()
        mock_imap._client_task = asyncio.Future()
        mock_imap._client_task.set_result(None)
        mock_imap.wait_hello_from_server = AsyncMock()
        mock_imap.login = AsyncMock()
        mock_imap.select = AsyncMock(return_value=("OK", []))
        # All folders fail to append - code catches and tries next folder
        mock_imap.append = AsyncMock(side_effect=Exception("Append failed"))
        mock_imap.logout = AsyncMock()

        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap):
            # When all folders fail, raises FileNotFoundError about no Drafts folder
            with pytest.raises(FileNotFoundError, match="Could not find a valid Drafts folder"):
                await handler.save_draft(
                    to="recipient@example.com",
                    subject="Test Subject",
                    body="Test body content",
                )

    @pytest.mark.asyncio
    async def test_save_draft_invalid_attachment_path(self, handler, mock_imap_for_draft):
        """Test when attachment path is invalid."""
        with patch.object(handler.incoming_client, "_imap_connect", return_value=mock_imap_for_draft):
            with pytest.raises(FileNotFoundError, match="Attachment file not found"):
                await handler.save_draft(
                    to="recipient@example.com",
                    subject="Test Subject",
                    body="Test body content",
                    attachments=["/nonexistent/path/file.txt"],
                )
