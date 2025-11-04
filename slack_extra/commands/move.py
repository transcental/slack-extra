import traceback
from asyncio import sleep

from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.utils.logging import send_heartbeat
from slack_extra.utils.slack import is_channel_manager


async def move_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    start: str,
    end: str,
):
    manage_start = await is_channel_manager(performer, start)
    manage_end = await is_channel_manager(performer, end)
    if not (manage_start and manage_end):
        return await respond(
            "You need to be a channel manager of both channels to move users"
        )

    finished = False
    channel_members = []
    cursor = None
    await respond("Joining both channels")
    try:
        channels = [start, end]
        for c in channels:
            r = await client.conversations_join(channel=c)
            if not r.get("ok"):
                await respond(f"Failed to join <#{c} - `{r.get('error')}`")
    except Exception as e:
        tb = traceback.format_exception(e)

        tb_str = "".join(tb)
        await respond(
            f"Something went wrong trying to join the channels\n```{tb_str}```"
        )
    await respond(f"Fetching members from <#{start}>...")
    while not finished:
        try:
            data = await client.conversations_members(
                channel=start, cursor=cursor, limit=200
            )
            if data.get("ok"):
                cursor = data.get("response_metadata", {}).get("next_cursor")
                channel_members += data.get("members", [])
                finished = not cursor
            else:
                if data.get("error") == "ratelimited":
                    retry_after = int(data.headers.get("Retry-After", 3))
                    await sleep(retry_after)
                else:
                    await send_heartbeat(
                        "Error when moving members (fetching members)",
                        messages=[f"```{data}```"],
                    )
        except Exception as e:
            tb = traceback.format_exception(e)

            tb_str = "".join(tb)
            await send_heartbeat(
                "Uh oh! Something went wrong when moving D:",
                messages=[f"```{tb_str}```"],
            )

    await respond(
        f"{len(channel_members)} members fetched from <#{start}>! Adding to <#{end}>"
    )

    while len(channel_members) > 0:
        try:
            users = channel_members[:100]
            del channel_members[:100]
            res = await client.conversations_invite(
                users=users, channel=end, force=True
            )
            if not res.get("ok"):
                if res.get("error") == "ratelimited":
                    retry_after = int(res.headers.get("Retry-After", 3))
                    await sleep(retry_after)
                else:
                    await send_heartbeat(
                        "Error when moving members (inviting)",
                        messages=[f"```{res}```"],
                    )
        except Exception as e:
            tb = traceback.format_exception(e)

            tb_str = "".join(tb)
            await send_heartbeat(
                "Uh oh! Something went wrong when moving D:",
                messages=[f"```{tb_str}```"],
            )

    await respond(f"Moved members from <#{start}> to <#{end}>")
