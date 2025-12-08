from slack_extra.events.channel_created import channel_created_handler
from slack_extra.events.member_joined_channel import member_joined_channel_handler
from slack_extra.events.message import message_handler


EVENTS = [
    {"id": "message", "handler": message_handler},
    {"id": "channel_created", "handler": channel_created_handler},
    {"id": "member_joined_channel", "handler": member_joined_channel_handler},
]


def register_events(app):
    for event in EVENTS:
        app.event(event["id"])(event["handler"])
