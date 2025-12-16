from slack_bolt.async_app import AsyncApp

from slack_extra.shortcuts.delete_message import delete_message_handler
from slack_extra.shortcuts.spoiler import spoiler_handler
# from slack_extra.shortcuts.export_reactions import export_reactions_handler


SHORTCUTS = [
    {
        "id": "delete_message",
        "handler": delete_message_handler,
    },
    {"id": "spoiler", "handler": spoiler_handler},
    # {"id": "export_reactions", "handler": export_reactions_handler},
]


def register_shortcuts(app: AsyncApp):
    for shortcut in SHORTCUTS:
        app.shortcut(shortcut["id"])(shortcut["handler"])
