from slack_extra.views.configure_anchor import configure_anchor_handler


VIEWS = [{"id": "configure_anchor", "handler": configure_anchor_handler}]


def register_views(app):
    for view in VIEWS:
        app.view(view["id"])(view["handler"])
