from slack_extra.actions.create_mover import create_mover_handler
from slack_extra.actions.edit_movers import edit_movers_handler
from slack_extra.actions.view_spoiler import view_spoiler_handler

ACTIONS = [
    {"id": "view_spoiler", "handler": view_spoiler_handler},
    {"id": "create_mover", "handler": create_mover_handler},
    {"id": "edit_movers", "handler": edit_movers_handler},
]


def register_actions(app):
    for action in ACTIONS:
        app.action(action["id"])(action["handler"])
