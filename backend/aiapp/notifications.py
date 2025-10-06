# This file was auto-generated as a scaffold.
# SAFE to edit. Keep functions/class names if you rely on them across apps.

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class Notification:
    subject: str
    message: str
    recipient: Optional[str] = None  # email/phone/user-id/etc.

def send(notification: Notification):
    """Pluggable notification shim; replace with email/SMS/push provider."""
    logger.info("NOTIFY: %s -> %s", notification.subject, notification.recipient or "<broadcast>")
    # TODO: wire Django email backend / Twilio / FCM etc.
