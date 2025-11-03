from pyairtable import Api
from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from slack_extra.config import config

HACKATIME_ENDPOINT = "https://hackatime.hackclub.com/api/v1/users/slackid/trust_factor"
IDENTITY_ENDPOINT = "https://identity.hackclub.com/api/external/check"
JOE_ENDPOINT = "https://dash.fraud.land/profile/"


async def info_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    user: str | None = None,
    email: str | None = None,
    channel: str | None = None,
):
    await ack()
    from slack_extra.env import env

    res = f"*User Info{f' for <@{user}>' if user else ''}:*\n"

    if user or email:
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
            else:
                res += "- Could not fetch user info from Slack API.\n"

        if email and user:
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

        if email:
            api = Api(api_key=config.airtable.nda.api_key)
            table = api.table(config.airtable.nda.base_id, config.airtable.nda.table_id)
            nda_records = table.all(
                formula=f"{{Email}} = '{email}'",
                fields=["Email", "Signed?"],
            )
            if nda_records:
                record_url = ""
                for record in nda_records:
                    record_url = f"https://airtable.com/{config.airtable.nda.base_id}/{config.airtable.nda.table_id}/{record.get('id')}"
                    signed = record.get("fields", {}).get("Signed?", False)
                    if signed:
                        res += f"- :tw_shield: *NDA Signed:* Yes _(<{record_url}|View on Airtable>)_\n"
                        break
                else:
                    res += f"- :tw_shield: *NDA Signed:* Sent but not signed _(<{record_url}|View on Airtable>)_\n"
            else:
                res += "- :tw_shield: *NDA Signed:* No record found\n"

    blocks = []
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": res}})
    await respond(blocks=blocks)
