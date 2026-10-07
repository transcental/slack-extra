from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.datastore import PiccoloInstallationStore
from slack_extra.utils.oauth import generate_oauth_url
from slack_extra.utils.slack import get_channel_managers


HACKATIME_ENDPOINT = "https://hackatime.hackclub.com/api/v1/users/slackid/trust_factor"
IDENTITY_ENDPOINT = "https://identity.hackclub.com/api/external/check"
JOE_ENDPOINT = "https://joe.fraud.hackclub.com/profile/"
NDA_ENDPOINT = "https://nda.hackclub.com/api/v1/nda_status/"


async def get_dm_partner(client: AsyncWebClient, performer: str, dm: str) -> str | None:
    """Resolve the other user in a 1:1 DM using the performer's user token."""
    team_info = await client.team_info()
    team_id = team_info.get("team", {}).get("id") or "T0266FRGM"

    installation = await PiccoloInstallationStore().async_find_installation(
        enterprise_id=None, team_id=team_id, user_id=performer
    )
    if not installation or not installation.user_token:
        return None

    try:
        dm_info = await client.conversations_info(
            channel=dm, token=installation.user_token
        )
    except SlackApiError:
        # most likely missing_scope from a token authorised before im:read
        return None
    return dm_info.get("channel", {}).get("user")


async def info_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    location: str,
    user: str | None = None,
    email: str | None = None,
    channel: str | None = None,
):
    await ack()
    from slack_extra.env import env

    res = "Oops, something went wrong."

    if not user and not email and not channel and location.startswith("D"):
        # the bot isn't in 1:1 DMs, so look up the other person as the performer
        user = await get_dm_partner(client, performer, location)
        if not user:
            oauth_url = await generate_oauth_url(user_scopes=["im:read"])
            await respond(
                f"Click here to authorise: <{oauth_url}|Authorise App>\n\n"
                f"_This will grant the app permission to see who this DM is with using the `im:read` scope._"
            )
            return

    channel = location if not channel else channel

    if user or email:
        res = f"*User Info{f' for <@{user}>' if user else email}:*\n"
        if user:
            user_info = await client.users_info(user=user)
            if user_info.get("ok"):
                user_data = user_info.get("user", {})
                email_addr = user_data.get("profile", {}).get("email", "N/A")
                if not email:
                    email = email_addr
                username = user_data.get("name", "this is wrong, pls contact amber")
                tz = user_data.get("tz", "N/A")
                res += f"- :globe_with_meridians: *Timezone:* {tz}\n"
                res += f"- :slack: *Slack Email:* {email_addr}\n"
                res += f"- :slack: *Slack Username:* {username}\n"
                res += f"- :slack: *Slack ID:* {user}\n"
            else:
                res += "- Could not fetch user info from Slack API.\n"

            # Fetch Hackatime trust
            joe = JOE_ENDPOINT + user
            try:
                async with env.http.get(
                    HACKATIME_ENDPOINT.replace("slackid", user)
                ) as ht_resp:
                    if ht_resp.status == 200:
                        ht_data = await ht_resp.json()
                        trust_factor = "Unknown"
                        colour = ht_data.get("trust_level")
                        value = ht_data.get("trust_value")
                        match colour:
                            case "green":
                                trust_factor = (
                                    f":large_green_circle: Trusted ({value})"
                                )
                            case "blue":
                                trust_factor = (
                                    f":large_blue_circle: Normal ({value})"
                                )
                            case "yellow":
                                trust_factor = (
                                    f":large_yellow_circle: Untrusted ({value})"
                                )
                            case "red":
                                trust_factor = f":red_circle: Banned ({value})"
                            case _:
                                trust_factor = ":question: Unknown"
                        res += f"- :clock1: *Hackatime Trust Factor:* {trust_factor} _(<{joe}|Joe>)_\n"
                    else:
                        res += f"- :clock1: *Hackatime Trust Factor:* N/A _(<{joe}|Joe>)_\n"
            except Exception:
                res += "- :clock1: *Hackatime Trust Factor:* N/A\n"

            # Fetch IDV Status
            if email:
                async with env.http.get(
                    IDENTITY_ENDPOINT, params={"slack_id": user}
                ) as id_resp:
                    if id_resp.status == 200:
                        id_data = await id_resp.json()
                        res += f"- :bust_in_silhouette: *IDV:* {id_data.get('result').replace('_', ' ').capitalize()}\n"
                    else:
                        async with env.http.get(
                            IDENTITY_ENDPOINT, params={"email": email}
                        ) as id_resp:
                            if id_resp.status == 200:
                                id_data = await id_resp.json()
                                res += f"- :bust_in_silhouette: *IDV:* {id_data.get('result').replace('_', ' ').capitalize()}\n"
                            else:
                                res += "- :bust_in_silhouette: *IDV:- N/A\n"
            
            # Fetch NDA Status
            try:
                async with env.http.get(
                    NDA_ENDPOINT + user
                ) as ht_resp:
                if ht_resp.status == 200:
                    ht_data = await ht_resp.json()
                    status = ht_data.get("status")
                    signature_type = ht_data.get("signature_type")

                    res += f"- :tw_shield: *NDA Status:* {status.replace("_", " ").title()}{f" ({signature_type})" if signature_type else ""}"
                else:
                    res += f"- :tw_shield: *NDA Status: Unknown*"
            except Exception:
                res += f"- :tw_shield: *NDA Status: Unknown*"

        if user:
            # https://nda.hackclub.com/api/v1/docs - public, keyed on Slack ID
            try:
                async with env.http.get(NDA_ENDPOINT + user) as nda_resp:
                    if nda_resp.status == 200:
                        nda_data = await nda_resp.json()
                        version = nda_data.get("nda_version", "unknown")
                        if nda_data.get("status") == "signed":
                            signed_at = nda_data.get("signed_at", "")
                            details = f"v{version}"
                            if signed_at:
                                details += f", signed {signed_at[:10]}"
                            if nda_data.get("signature_type") == "legacy":
                                details += ", imported"
                            res += f"- :tw_shield: *NDA Signed:* Yes _({details})_\n"
                        else:
                            res += f"- :tw_shield: *NDA Signed:* No _(current v{version})_\n"
                    elif nda_resp.status == 400:
                        res += "- :tw_shield: *NDA Signed:* N/A _(invalid Slack ID)_\n"
                    elif nda_resp.status == 429:
                        res += "- :tw_shield: *NDA Signed:* N/A _(rate limited, try again shortly)_\n"
                    else:
                        res += "- :tw_shield: *NDA Signed:* N/A\n"
            except Exception:
                res += "- :tw_shield: *NDA Signed:* N/A\n"

    elif channel:
        res = f"*Channel Info for <#{channel}>:*\n"
        channel_info = await client.conversations_info(
            channel=channel, include_num_members=True
        )
        if channel_info.get("ok"):
            channel_data = channel_info.get("channel", {})
            creator = channel_data.get("creator", "N/A")
            created_ts = channel_data.get("created", 0)
            member_count = channel_data.get("num_members", 0)
            res += f"- :bust_in_silhouette: *Creator:* <@{creator}>\n"
            from datetime import datetime

            created_dt = datetime.fromtimestamp(created_ts)
            res += f"- :calendar: *Created On:* {created_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            res += f"- :busts_in_silhouette: *Member Count:* {member_count}\n"
            channel_managers = await get_channel_managers(channel)
            if channel_managers:
                manager_mentions = ", ".join([f"<@{mgr}>" for mgr in channel_managers])
                res += f"- :shield: *Channel Managers:* {manager_mentions}\n"
        else:
            res += "- Could not fetch channel info from Slack API.\n"

    blocks = []
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": res}})
    await respond(blocks=blocks)
