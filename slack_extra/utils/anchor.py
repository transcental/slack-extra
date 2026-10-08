import asyncio
from weakref import WeakValueDictionary

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.utils.logging import send_heartbeat


# The app runs in one event loop. Keep unrelated channels independent, and
# discard idle locks once no handler owns or waits for them.
_anchor_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()


def anchor_lock(channel: str) -> asyncio.Lock:
    lock = _anchor_locks.get(channel)
    if lock is None:
        lock = asyncio.Lock()
        _anchor_locks[channel] = lock
    return lock


async def remove_anchor(
    client: AsyncWebClient,
    channel: str,
    timestamp: str,
    user_token: str,
    pin_token: str,
) -> bool:
    """Do not replace an anchor until its previous message is cleaned up."""
    try:
        await client.pins_remove(channel=channel, timestamp=timestamp, token=pin_token)
    except SlackApiError as e:
        if e.response["error"] not in ("not_pinned", "message_not_found"):
            await send_heartbeat(
                f"Failed to unpin anchor message in channel <#{channel}>: {e.response['error']}"
            )
            return False

    try:
        await client.chat_delete(channel=channel, ts=timestamp, token=user_token)
    except SlackApiError as e:
        if e.response["error"] != "message_not_found":
            await send_heartbeat(
                f"Failed to delete anchor message in channel <#{channel}>: {e.response['error']}"
            )
            return False
    return True
