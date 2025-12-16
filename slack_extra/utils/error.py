from blockkit import Header
from blockkit import Modal
from blockkit import Section


def generate_error_view(title: str, body: str):
    view = (
        Modal()
        .add_block(Header(f"wuh woh - {title} :rac_ded:"))
        .add_block(Section(body))
    )
    return view.build()
