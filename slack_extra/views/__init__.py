from slack_extra.views.configure_anchor import configure_anchor_handler
from slack_extra.views.create_spoiler import create_spoiler_handler
from slack_extra.views.edit_move import edit_move_handler
from slack_extra.views.setup_move import setup_move_handler


VIEWS = [
    {"id": "configure_anchor", "handler": configure_anchor_handler},
    {"id": "create_spoiler", "handler": create_spoiler_handler},
    {"id": "setup_move", "handler": setup_move_handler},
    {"id": "edit_move", "handler": edit_move_handler},
]


def register_views(app):
    for view in VIEWS:
        app.view(view["id"])(view["handler"])
