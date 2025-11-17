import json

from blockkit import Context
from blockkit import Modal
from blockkit import Section
from blockkit import Text
from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.tables import Spoiler
from slack_extra.utils.logging import send_heartbeat


async def view_spoiler_handler(
    ack: AsyncAck, client: AsyncWebClient, respond: AsyncRespond, body: dict
):
    await ack()
    user_id = body["user"]["id"]
    value = body["actions"][0]["value"]
    ts = body["message"]["ts"]
    channel = body["channel"]["id"]
    match value:
        case "metadata":
            try:
                message = await client.conversations_history(
                    oldest=ts,
                    channel=channel,
                    inclusive=True,
                    limit=1,
                    include_all_metadata=True,
                )
            except SlackApiError as e:
                if e.response["error"] == "message_not_found":
                    await client.chat_postEphemeral(
                        channel=channel,
                        user=user_id,
                        text="i couldn't find that message :(\ntry making sure i'm still in the channel?",
                    )
                    return
                elif (
                    e.response["error"] == "not_in_channel"
                    or e.response["error"] == "channel_not_found"
                ):
                    try:
                        await client.conversations_join(channel=channel)
                        message = await client.conversations_history(
                            oldest=ts,
                            channel=channel,
                            inclusive=True,
                            limit=1,
                            include_all_metadata=True,
                        )
                    except SlackApiError as e:
                        await client.chat_postMessage(
                            channel=user_id,
                            text=f"you tried to access a spoiler in <#{channel}> but i'm not there! please add me and try again :)",
                        )

                        await send_heartbeat(
                            heartbeat="Error in view_spoiler_handler",
                            messages=[f"Error details: {e.response['error']}"],
                        )
                        return
                else:
                    await client.chat_postEphemeral(
                        channel=channel,
                        user=user_id,
                        text="oops, something went wrong fetching that message!",
                    )

                    await send_heartbeat(
                        heartbeat="Error in view_spoiler_handler",
                        messages=[f"Error details: {e.response['error']}"],
                    )
                    return

            message = message["messages"][0]
            text = message["metadata"]["event_payload"]["text"]
            poster = message["metadata"]["event_payload"]["poster"]
            modal = (
                Modal()
                .title("Spoiler 👀")
                .add_block(Section(text=text))
                .add_block(
                    Context().add_element(
                        element=Text(type="mrkdwn", text=f"spoilered by <@{poster}>")
                    )
                )
                .close("Close")
            ).build()
            await client.views_open(trigger_id=body["trigger_id"], view=modal)
            return

        case "db":
            spoiler = (
                await Spoiler.objects()
                .where((Spoiler.channel == channel) & (Spoiler.message_ts == ts))
                .first()
            )
            if spoiler:
                modal = {
                    "type": "modal",
                    "title": {"type": "plain_text", "text": "Spoiler 👀"},
                    "close": {"type": "plain_text", "text": "Close"},
                    "blocks": [
                        json.loads(spoiler.message),
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"spoilered by <@{spoiler.user}>",
                                }
                            ],
                        },
                    ],
                }
                await client.views_open(trigger_id=body["trigger_id"], view=modal)
                return
            else:
                await client.chat_postEphemeral(
                    channel=channel,
                    user=user_id,
                    text="oops, something went wrong fetching that message from the database!",
                )
                await send_heartbeat(
                    heartbeat="Error in view_spoiler_handler",
                    messages=[f"Spoiler not found in DB for {channel} at {ts}"],
                )
                return
