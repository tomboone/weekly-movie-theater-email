import asyncio
import logging

from azure.communication.email import EmailClient

logger = logging.getLogger(__name__)


def _send_sync(connection_string: str, message: dict) -> dict:
    client = EmailClient.from_connection_string(connection_string)
    poller = client.begin_send(message)
    return dict(poller.result())


async def send_email(
    connection_string: str,
    sender: str,
    recipient: str,
    subject: str,
    html_body: str,
) -> None:
    logger.info("Sending email to %s via ACS", recipient)
    message = {
        "senderAddress": sender,
        "recipients": {
            "to": [{"address": recipient}],
        },
        "content": {
            "subject": subject,
            "html": html_body,
        },
    }
    result = await asyncio.to_thread(_send_sync, connection_string, message)
    logger.info("Email sent, message ID: %s", result.get("id", "unknown"))
