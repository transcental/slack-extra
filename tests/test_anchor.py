import asyncio
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

from slack_sdk.errors import SlackApiError


# Load handlers without starting the app or needing real configuration/database.
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, Path(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fake_config = ModuleType("slack_extra.config")
fake_config.config = SimpleNamespace(
    slack=SimpleNamespace(
        user_token="admin",
        bot_token="bot",
        maintainer_id="owner",
        support_channel="support",
    )
)
fake_store = ModuleType("slack_extra.datastore")
fake_store.PiccoloInstallationStore = object
fake_tables = ModuleType("slack_extra.tables")
fake_tables.AnchorConfig = object
fake_logging = ModuleType("slack_extra.utils.logging")
fake_logging.send_heartbeat = AsyncMock()
with patch.dict(
    sys.modules,
    {
        "slack_extra.config": fake_config,
        "slack_extra.datastore": fake_store,
        "slack_extra.tables": fake_tables,
        "slack_extra.utils.logging": fake_logging,
    },
):
    cleanup = load("anchor_cleanup", "slack_extra/utils/anchor.py")
    with patch.dict(sys.modules, {"slack_extra.utils.anchor": cleanup}):
        handler = load("anchor_handler", "slack_extra/events/message/anchor.py")
        modal = load("anchor_modal", "slack_extra/views/configure_anchor.py")


class Column:
    def __eq__(self, other):
        return other

    __hash__ = object.__hash__


class Table:
    channel_id = Column()
    message_ts = Column()
    enabled = Column()
    message = Column()
    user_id = Column()

    def __init__(self, records):
        self.records = records

    def objects(self):
        table = self

        class Query:
            def where(self, channel):
                self.channel = channel
                return self

            async def first(self):
                # Return a snapshot, as independent real database reads do.
                return SimpleNamespace(
                    **vars(table.records[self.channel]), update=table.update
                )

        return Query()

    def update(self, values):
        table = self

        class Update:
            async def where(self, channel):
                for field, value in values.items():
                    for name in ("message_ts", "enabled", "message", "user_id"):
                        if field is getattr(table, name):
                            setattr(table.records[channel], name, value)

        return Update()


class Client:
    def __init__(self):
        self.messages = {"C": {"old"}, "D": {"other"}}
        self.pins = {"C": {"old"}, "D": {"other"}}
        self.calls = []
        self.next_ts = 0
        self.first_delete = asyncio.Event()
        self.continue_delete = asyncio.Event()
        self.block_delete = False
        self.fail_delete = None
        self.fail_unpin = None
        self.fail_pin = False
        self.fail_post = False
        self.notifications = []

    async def pins_remove(self, channel, timestamp, token):
        self.calls.append(("unpin", channel, timestamp, token))
        if self.fail_unpin:
            raise SlackApiError("error", {"error": self.fail_unpin})
        self.pins[channel].discard(timestamp)

    async def chat_delete(self, channel, ts, token):
        self.calls.append(("delete", channel, ts, token))
        if self.block_delete and channel == "C" and ts == "old":
            self.first_delete.set()
            await self.continue_delete.wait()
        if self.fail_delete:
            raise SlackApiError("error", {"error": self.fail_delete})
        self.messages[channel].discard(ts)

    async def chat_postMessage(self, channel, **kwargs):
        self.next_ts += 1
        ts = str(self.next_ts)
        self.calls.append(("post", channel, ts))
        if channel not in self.messages:
            self.notifications.append((channel, kwargs["text"]))
            return {"ts": ts}
        if self.fail_post:
            raise SlackApiError("error", {"error": "ratelimited"})
        self.messages[channel].add(ts)
        await asyncio.sleep(0)
        return {"ts": ts}

    async def pins_add(self, channel, timestamp, token):
        self.calls.append(("pin", channel, timestamp, token))
        if self.fail_pin:
            raise SlackApiError("error", {"error": "ratelimited"})
        self.pins[channel].add(timestamp)
        await asyncio.sleep(0)


class AnchorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.records = {
            channel: SimpleNamespace(
                message_ts=ts,
                enabled=True,
                message=json.dumps({"type": "rich_text", "elements": []}),
                user_id="old-owner",
            )
            for channel, ts in (("C", "old"), ("D", "other"))
        }
        self.table = Table(self.records)
        self.store = SimpleNamespace(
            async_find_installation=AsyncMock(
                side_effect=lambda user_id, **kwargs: SimpleNamespace(
                    user_token=user_id, user_scopes=["pins:write"]
                )
            )
        )
        self.client = Client()
        self.patches = [
            patch.object(module, name, value)
            for module in (handler, modal)
            for name, value in (
                ("AnchorConfig", self.table),
                ("PiccoloInstallationStore", lambda: self.store),
            )
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    async def event(self, channel="C", **extra):
        await handler.anchor_message_handler(
            {}, {"channel": channel, **extra}, self.client
        )

    async def test_burst_reads_current_timestamp_inside_lock(self):
        self.client.block_delete = True
        first = asyncio.create_task(self.event())
        await self.client.first_delete.wait()
        rest = [asyncio.create_task(self.event()) for _ in range(10)]
        await asyncio.sleep(0)
        self.assertEqual(len(self.client.calls), 2)
        self.client.continue_delete.set()
        await asyncio.gather(first, *rest)
        current = self.records["C"].message_ts
        self.assertEqual(self.client.messages["C"], {current})
        self.assertEqual(self.client.pins["C"], {current})
        self.assertEqual(
            [c[0] for c in self.client.calls], ["unpin", "delete", "post", "pin"] * 11
        )

    async def test_unrelated_channel_can_progress(self):
        self.client.block_delete = True
        first = asyncio.create_task(self.event())
        await self.client.first_delete.wait()
        await asyncio.wait_for(self.event("D"), 1)
        self.client.continue_delete.set()
        await first

    async def test_cleanup_errors_do_not_create_new_message(self):
        for attr, error in (
            ("fail_unpin", "missing_scope"),
            ("fail_delete", "cant_delete_message"),
        ):
            with self.subTest(error=error):
                setattr(self.client, attr, error)
                await self.event()
                self.assertFalse(any(c[0] == "post" for c in self.client.calls))
                setattr(self.client, attr, None)

    async def test_absent_pin_and_message_are_idempotent(self):
        self.client.fail_unpin = "not_pinned"
        self.client.fail_delete = "message_not_found"
        self.client.messages["C"].clear()
        self.client.pins["C"].clear()
        await self.event()
        self.assertEqual(self.client.messages["C"], {self.records["C"].message_ts})

    async def test_own_metadata_and_thread_replies_are_ignored(self):
        await self.event(metadata={"event_type": "anchor"})
        await self.event(thread_ts="unrelated")
        await self.event(subtype="message_deleted")
        self.assertEqual(self.client.calls, [])

    async def test_pin_failure_keeps_timestamp_for_next_cleanup(self):
        self.client.fail_pin = True
        with self.assertRaises(SlackApiError):
            await self.event()
        failed_ts = self.records["C"].message_ts
        self.client.fail_pin = False
        await self.event()
        self.assertNotIn(failed_ts, self.client.messages["C"])
        self.assertEqual(self.client.messages["C"], {self.records["C"].message_ts})

    def modal_body(self):
        return {
            "user": {"id": "new-owner"},
            "view": {
                "private_metadata": "C|edit",
                "state": {
                    "values": {
                        "anchor_input": {
                            "anchor_input": {
                                "rich_text_value": {"type": "rich_text", "elements": []}
                            }
                        }
                    }
                },
            },
        }

    async def test_modal_post_failure_preserves_old_anchor_and_reports_error(self):
        self.client.fail_post = True
        original = vars(self.records["C"]).copy()
        ack = AsyncMock()
        await modal.configure_anchor_handler(ack, self.modal_body(), self.client)
        ack.assert_awaited_once()
        self.assertEqual(vars(self.records["C"]), original)
        self.assertEqual(self.client.messages["C"], {"old"})
        self.assertEqual(self.client.pins["C"], {"old"})
        self.assertFalse(
            any(c[0] in ("unpin", "delete", "pin") for c in self.client.calls)
        )
        self.assertEqual(self.client.notifications[0][0], "new-owner")
        self.assertIn("could not be posted", self.client.notifications[0][1])

    async def test_modal_posts_before_removing_old_anchor(self):
        await modal.configure_anchor_handler(
            AsyncMock(), self.modal_body(), self.client
        )
        self.assertEqual(
            [c[0] for c in self.client.calls], ["post", "unpin", "delete", "pin"]
        )
        self.assertEqual(self.client.messages["C"], {self.records["C"].message_ts})
        self.assertEqual(self.client.pins["C"], {self.records["C"].message_ts})

    async def test_modal_cleanup_failure_removes_replacement_without_updating_config(
        self,
    ):
        self.client.fail_unpin = "missing_scope"
        original = vars(self.records["C"]).copy()
        await modal.configure_anchor_handler(
            AsyncMock(), self.modal_body(), self.client
        )
        self.assertEqual(vars(self.records["C"]), original)
        self.assertFalse(any(c[0] == "pin" for c in self.client.calls))
        self.assertEqual(self.client.notifications[0][0], "new-owner")
        self.assertIn("could not be removed", self.client.notifications[0][1])

    async def test_modal_edit_shares_lock_and_uses_previous_owner(self):
        self.client.block_delete = True
        event = asyncio.create_task(self.event())
        await self.client.first_delete.wait()
        body = self.modal_body()
        edit = asyncio.create_task(
            modal.configure_anchor_handler(AsyncMock(), body, self.client)
        )
        await asyncio.sleep(0)
        self.assertEqual(len(self.client.calls), 2)
        self.client.continue_delete.set()
        await asyncio.gather(event, edit)
        self.assertEqual(self.client.messages["C"], {self.records["C"].message_ts})
        self.assertEqual(self.client.pins["C"], {self.records["C"].message_ts})
        deletes = [c for c in self.client.calls if c[0] == "delete"]
        self.assertEqual([c[3] for c in deletes], ["old-owner", "old-owner"])
        self.assertEqual(self.records["C"].user_id, "new-owner")


if __name__ == "__main__":
    unittest.main()
