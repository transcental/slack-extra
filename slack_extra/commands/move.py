import traceback
from asyncio import sleep

from blockkit import Actions
from blockkit import Button
from blockkit import Modal
from blockkit import Section
from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config
from slack_extra.utils.logging import send_heartbeat
from slack_extra.utils.slack import is_channel_manager


def _is_subteam_id(value: str) -> bool:
    """Check if the value looks like a Slack subteam (user group) ID."""
    return value.startswith("S") and len(value) > 1


async def move_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    raw_command: str,
    command: dict,
    start: str | None = None,
    end: str | None = None,
):
    await ack()
    ran = f"\n_You ran `{raw_command}`_"

    if start and end:
        ran = f"_You ran `{raw_command}`_"

        # Check if end is a user group (subteam)
        if _is_subteam_id(end):
            return await _move_channel_to_usergroup(
                client, respond, performer, start, end, ran
            )

        # Original channel-to-channel move logic
        manage_start = await is_channel_manager(performer, start)
        manage_end = await is_channel_manager(performer, end)
        if not (manage_start and manage_end):
            return await respond(
                f"You need to be a channel manager of both channels to move users{ran}"
            )

        finished = False
        channel_members = []
        cursor = None
        await respond("Joining both channels")
        try:
            channels = [start, end]
            for c in channels:
                try:
                    await client.conversations_join(channel=c)
                except SlackApiError as e:
                    error = e.response.get("error")
                    if error in ["channel_not_found", ""]:
                        await respond(f"Failed to join <#{c} - `{error}`{ran}")
        except Exception as e:
            tb = traceback.format_exception(e)

            tb_str = "".join(tb)
            await respond(
                f"Something went wrong trying to join the channels\n```{tb_str}```{ran}"
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
                    users=users, channel=end, force=True, token=config.slack.user_token
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
        return

    view = (
        Modal()
        .title("Manage Auto Movers")
        .add_block(Section(text="Setup automatic moving channels here!"))
        .add_block(
            Actions()
            .add_element(
                Button("Create Mover").action_id("create_mover").style("primary")
            )
            .add_element(Button("Edit Movers").action_id("edit_movers"))
        )
        .close("Nevermind")
    ).build()

    try:
        await client.views_open(trigger_id=command["trigger_id"], view=view)
    except SlackApiError as e:
        await respond(f"Error opening modal: {e.response['error']}{ran}")
        return


async def _move_channel_to_usergroup(
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    channel: str,
    usergroup: str,
    ran: str,
):
    """Move all members from a channel to a user group (ping group)."""
    # Check if the performer is a channel manager
    manage_channel = await is_channel_manager(performer, channel)
    if not manage_channel:
        return await respond(
            f"You need to be a channel manager of <#{channel}> to move users{ran}"
        )

    # Fetch channel members
    await respond(f"Fetching members from <#{channel}>...")
    channel_members = []
    cursor = None
    finished = False

    while not finished:
        try:
            data = await client.conversations_members(
                channel=channel, cursor=cursor, limit=200
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
                        "Error when moving members to usergroup (fetching members)",
                        messages=[f"```{data}```"],
                    )
                    return await respond(f"Error fetching channel members{ran}")
        except Exception as e:
            tb = traceback.format_exception(e)
            tb_str = "".join(tb)
            await send_heartbeat(
                "Uh oh! Something went wrong when moving to usergroup D:",
                messages=[f"```{tb_str}```"],
            )
            return await respond(f"Error fetching channel members{ran}")

    if not channel_members:
        return await respond(f"No members found in <#{channel}>{ran}")

    await respond(
        f"{len(channel_members)} members fetched from <#{channel}>! Adding to <!subteam^{usergroup}>..."
    )

    # Fetch existing usergroup members
    try:
        existing_members_resp = await client.usergroups_users_list(usergroup=usergroup)
        existing_members = existing_members_resp.get("users", [])
    except SlackApiError as e:
        if e.response.get("error") == "no_users_in_usergroup":
            existing_members = []
        else:
            return await respond(
                f"Error fetching usergroup members: {e.response['error']}{ran}"
            )

    # Merge members (add channel members to existing usergroup members)
    all_members = list(set(existing_members + channel_members))

    # Update the usergroup
    try:
        await client.usergroups_users_update(usergroup=usergroup, users=all_members)
    except SlackApiError as e:
        return await respond(f"Error updating usergroup: {e.response['error']}{ran}")

    added_count = len(all_members) - len(existing_members)
    await respond(
        f"Added {added_count} new members from <#{channel}> to <!subteam^{usergroup}> (total: {len(all_members)} members)"
    )
