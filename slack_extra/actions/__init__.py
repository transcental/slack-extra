from slack_extra.actions.view_spoiler import view_spoiler_handler

ACTIONS = [{"id": "view_spoiler", "handler": view_spoiler_handler}]


def register_actions(app):
    for action in ACTIONS:
        app.action(action["id"])(action["handler"])
