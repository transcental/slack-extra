# import logging
# from blockkit import DatePicker
# from blockkit import Input
# from blockkit import Modal
# from blockkit import PlainTextInput
# from blockkit import UrlInput
# from slack_bolt.async_app import AsyncAck
# from slack_sdk.web.async_client import AsyncWebClient
# from slack_extra.utils.logging import send_heartbeat
# custom_fields = [
#     {"name": "Title", "id": "Xf03USKB04JE", "type": "text"},
#     {"name": "Name Pronunciation", "id": "Xf03USKB04JE", "type": "text"},
#     {"name": "Country", "id": "Xf03V58AC2BT", "type": "text"},
#     {"name": "Phone", "id": "Xf03KV6S6WQH", "type": "text"},
#     {"name": "Manager", "id": "Xf09727DH1J8", "type": "user"},
#     {"name": "Organisation", "id": "Xf03UL1CMTB8", "type": "text"},
#     {"name": "Division", "id": "Xf03UPL28405", "type": "text"},
#     {"name": "Department", "id": "Xf03UC2KD4AK", "type": "text"},
#     {"name": "Start Date", "id": "Xf05GRERG8AE", "type": "date"},
#     {"name": "Website", "id": "Xf5LNGS86L", "type": "url"},
#     {"name": "Scrapbook", "id": "Xf017187T1MW", "type": "url"},
#     {"name": "GitHub", "id": "Xf0DMHFDQA", "type": "url"},
#     {"name": "School", "id": "Xf0DMGGW01", "type": "text"},
#     {"name": "Birthday", "id": "XfQN2QL49W", "type": "date"},
#     {"name": "Favourite Channel(s)", "id": "XfM1701Z9V", "type": "text"},
#     {"name": "Fav Food(s)", "id": "Xf0191PM1588", "type": "text"},
#     {"name": "Fav Band/Artist(s)", "id": "Xf01921WR26N", "type": "text"},
#     {"name": "Location", "id": "Xf01S5PAG9HQ", "type": "text"},
#     {"name": "Fav Activities", "id": "Xf01SBU8GWP6", "type": "text"},
#     {"name": "Fav Languages/Tools", "id": "Xf01S5PRFAQJ", "type": "text"},
#     {"name": "Dog or Cat or Infrastructure?", "id": "Xf06851X9ZEX", "type": "text"},
#     {"name": "HAM Callsign", "id": "Xf068DMM22JE", "type": "text"},
#     {"name": "PFP Credit", "id": "Xf081WUQUEE4", "type": "text"},
#     {"name": "Social Account", "id": "Xf09A42WSW9Z", "type": "url"},
# ]
# def register(app):
#     @app.command("/profile")
#     async def handler(ack: AsyncAck, client: AsyncWebClient, command: dict):
#         logging.info("hi")
#         await ack()
#         await send_heartbeat(str(command))
#         user_id = command["user_id"]
#         trigger_id = command["trigger_id"]
#         user = await client.users_profile_get(user=user_id, include_labels=True)
#         fields = user.get("fields", {})
#         await send_heartbeat(str(user))
#         modal = Modal().title("Update Profile")
#         for field in custom_fields:
#             user_field = fields.get(field["id"])
#             if user_field:
#                 value = user_field.get("value", "Unknown")
#             match field["type"]:
#                 case "text":
#                     modal.add_block(
#                         Input(field["name"]).element(
#                             PlainTextInput().initial_value("a").action_id(field["id"])
#                         )
#                     )
#                 case "url":
#                     # alt =
#                     modal.add_block(
#                         Input(f"{field['name']}: URL").element(
#                             UrlInput()
#                             .initial_value("a")
#                             .action_id(f"{field['id']};url")
#                         )
#                     )
#                     modal.add_block(
#                         Input(f"{field['name']}: Alt").element(
#                             UrlInput()
#                             .initial_value("a")
#                             .action_id(f"{field['id']};alt")
#                         )
#                     )
#                 case "date":
#                     modal.add_block(
#                         Input(field["name"]).element(
#                             DatePicker().initial_date("a").action_id(field["id"])
#                         )
#                     )
#                 case "user":
#                     ...
#         modal = modal.submit("Update").build()
#         await client.views_open(view=modal, user=user_id, trigger_id=trigger_id)
