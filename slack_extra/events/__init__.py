from slack_extra.events.message import message_handler


EVENTS = [{"id": "message", "handler": message_handler}]


def register_events(app):
    for event in EVENTS:
        app.event(event["id"])(event["handler"])
