from unittest.mock import MagicMock, patch

from email_sender.acs import _send_sync, send_email


async def test_send_email_constructs_correct_message() -> None:
    mock_poller = MagicMock()
    mock_poller.result.return_value = {"id": "msg-001"}

    mock_client = MagicMock()
    mock_client.begin_send.return_value = mock_poller

    with patch("email_sender.acs.EmailClient.from_connection_string", return_value=mock_client):
        await send_email(
            connection_string="endpoint=https://test.azure.com/;accesskey=dGVzdA==",
            sender="sender@example.com",
            recipient="recipient@example.com",
            subject="Weekly Movies",
            html_body="<h1>Movies</h1>",
        )

    mock_client.begin_send.assert_called_once()
    call_args = mock_client.begin_send.call_args[0][0]

    assert call_args["senderAddress"] == "sender@example.com"
    assert call_args["recipients"]["to"][0]["address"] == "recipient@example.com"
    assert call_args["content"]["subject"] == "Weekly Movies"
    assert call_args["content"]["html"] == "<h1>Movies</h1>"


async def test_send_email_returns_message_id() -> None:
    mock_poller = MagicMock()
    mock_poller.result.return_value = {"id": "msg-abc-123"}

    mock_client = MagicMock()
    mock_client.begin_send.return_value = mock_poller

    with patch("email_sender.acs.EmailClient.from_connection_string", return_value=mock_client):
        # Should complete without raising
        await send_email(
            connection_string="endpoint=https://test.azure.com/;accesskey=dGVzdA==",
            sender="sender@example.com",
            recipient="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test</p>",
        )

    mock_client.begin_send.assert_called_once()
    mock_poller.result.assert_called_once()


def test_send_sync_creates_client_and_sends() -> None:
    connection_string = "endpoint=https://test.azure.com/;accesskey=dGVzdA=="
    message = {
        "senderAddress": "sender@example.com",
        "recipients": {
            "to": [{"address": "recipient@example.com"}],
        },
        "content": {
            "subject": "Test",
            "html": "<p>Hello</p>",
        },
    }

    mock_poller = MagicMock()
    mock_poller.result.return_value = {"id": "msg-xyz"}

    mock_client = MagicMock()
    mock_client.begin_send.return_value = mock_poller

    with patch("email_sender.acs.EmailClient.from_connection_string", return_value=mock_client) as mock_factory:
        result = _send_sync(connection_string, message)

    mock_factory.assert_called_once_with(connection_string)
    mock_client.begin_send.assert_called_once_with(message)
    assert result == {"id": "msg-xyz"}
