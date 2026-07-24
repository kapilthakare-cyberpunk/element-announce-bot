"""
Element Announce Bot — Matrix/Element version of the Telegram Announce Bot.

Sends announcements to team members in an encrypted Matrix room.
Members confirm engagement by reacting with ✅ to the message.
"""

import json
import asyncio
import logging
from pathlib import Path

from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    LoginError,
    MegolmEvent,
    RoomMessageText,
    UnknownEvent,
    RoomCreateResponse,
    RoomCreateError,
)

from common import (
    BASE_DIR,
    CONFIG_FILE,
    DATA_FILE,
    CREDENTIALS_FILE,
    STORE_PATH,
    HOMESERVER,
    USER_ID,
    PASSWORD,
    ACCESS_TOKEN,
    ADMIN_ID,
    ROOM_ID,
    load_config,
    load_data,
    save_config,
    save_data,
    get_member_name,
    get_or_create_dm_room,
    matrix_login,
    send_text,
    send_html,
    react_to,
    redact_event,
    send_announcement_to_members,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
log = logging.getLogger("element-bot")

DEVICE_NAME = "element-announce-bot"


async def create_room(client, name, topic, invite_users=None):
    initial_state = [
        {
            "type": "m.room.encryption",
            "state_key": "",
            "content": {"algorithm": "m.megolm.v1.aes-sha2"},
        }
    ]
    invite_list = invite_users or []
    resp = await client.room_create(
        name=name,
        topic=topic,
        visibility="private",
        preset="trusted_private_chat",
        is_direct=False,
        invite=invite_list,
        initial_state=initial_state,
    )
    if isinstance(resp, RoomCreateResponse):
        log.info(f"Created room {name}: {resp.room_id}")
        return resp.room_id
    else:
        log.error(f"Failed to create room: {resp}")
        return None


class BotCallbacks:
    def __init__(self, client):
        self.client = client
        self.pending_announcement = None

    async def on_message(self, room, event):
        if event.sender == self.client.user_id:
            return
        text = event.body.strip()
        sender = event.sender
        config = load_config()
        is_admin = sender == ADMIN_ID
        if text.startswith("/"):
            await self.handle_command(room, event, text, is_admin)

    async def handle_command(self, room, event, text, is_admin):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        commands = {
            "/help": self.cmd_help,
            "/register": self.cmd_register,
            "/status": self.cmd_status,
            "/retract": self.cmd_retract,
            "/members": self.cmd_members,
            "/settest": self.cmd_settest,
            "/testlist": self.cmd_testlist,
            "/announce": self.cmd_announce,
            "/confirm": self.cmd_confirm,
            "/cancel": self.cmd_cancel,
        }
        handler = commands.get(cmd)
        if not handler:
            return
        if not is_admin and cmd in ("/status", "/retract", "/members", "/settest", "/testlist", "/announce", "/confirm", "/cancel"):
            await send_text(self.client, room.room_id, f"Only admin can use {cmd}.")
            return
        if cmd == "/register":
            await self.cmd_register(room, event, args)
        else:
            await handler(room, args)

    async def cmd_help(self, room, _args=None):
        help_text = (
            "Element Announce Bot — Commands:\n\n"
            "/register <name> — Register as a team member\n"
            "/status — Show latest announcement status (admin)\n"
            "/retract <id> — Retract an announcement (admin)\n"
            "/members — List all members (admin)\n"
            "/settest <user_id> — Add test user (admin)\n"
            "/testlist — List test users (admin)\n"
            "/announce <text> — Create a pending announcement draft (admin)\n"
            "/confirm — Confirm and broadcast the pending announcement (admin)\n"
            "/cancel — Discard the pending announcement draft (admin)\n"
            "\nTo confirm engagement: react with ✅ to any announcement message."
        )
        await send_text(self.client, room.room_id, help_text)

    async def cmd_register(self, room, event, name):
        if not name:
            await send_text(self.client, room.room_id, "Usage: /register <your name>")
            return
        user_id = event.sender
        config = load_config()
        for m in config["members"]:
            if m["user_id"] == user_id:
                await send_text(self.client, room.room_id, f"You are already registered as {m['name']}.")
                return
        config["members"].append({"user_id": user_id, "name": name.strip()})
        save_config(config)
        await send_text(self.client, room.room_id, f"Welcome {name.strip()}! You are now registered.")
        log.info(f"New member registered: {name.strip()} ({user_id})")

    async def cmd_status(self, room, _args=None):
        data = load_data()
        config = load_config()
        if not data["announcements"]:
            await send_text(self.client, room.room_id, "No announcements sent yet.")
            return
        latest = data["announcements"][-1]
        completed = set(latest.get("completed_by", []))
        lines = [f"Announcement #{latest['id']} — Status:"]
        for m in config["members"]:
            icon = "✅" if m["user_id"] in completed else "⬜"
            lines.append(f"  {icon} {m['name']}")
        done = len(completed)
        total = len(config["members"])
        lines.append(f"\n{done}/{total} completed")
        await send_text(self.client, room.room_id, "\n".join(lines))

    async def cmd_retract(self, room, args):
        if not args:
            await send_text(self.client, room.room_id, "Usage: /retract <announcement_id>")
            return
        try:
            ann_id = int(args.strip())
        except ValueError:
            await send_text(self.client, room.room_id, "Invalid announcement ID.")
            return
        data = load_data()
        target = next((a for a in data["announcements"] if a["id"] == ann_id), None)
        if not target:
            await send_text(self.client, room.room_id, f"Announcement #{ann_id} not found.")
            return
        sent = target.get("sent_messages", [])
        if not sent:
            await send_text(self.client, room.room_id, f"Announcement #{ann_id} has no retractable messages.")
            return
        deleted = 0
        for entry in sent:
            try:
                dm_room_id = entry.get("room_id", room.room_id)
                await redact_event(self.client, dm_room_id, entry["event_id"])
                deleted += 1
            except Exception as e:
                log.warning(f"Failed to redact {entry['event_id']}: {e}")
        await send_text(self.client, room.room_id, f"Retracted {deleted}/{len(sent)} messages for announcement #{ann_id}.")

    async def cmd_members(self, room, _args=None):
        config = load_config()
        members = config.get("members", [])
        if not members:
            await send_text(self.client, room.room_id, "No members registered yet.")
            return
        lines = [f"Team Members ({len(members)}):"]
        for m in members:
            lines.append(f"  • {m['name']} ({m['user_id']})")
        await send_text(self.client, room.room_id, "\n".join(lines))

    async def cmd_settest(self, room, args):
        if not args:
            await send_text(self.client, room.room_id, "Usage: /settest <user_id>")
            return
        user_id = args.strip()
        config = load_config()
        test_ids = config.get("test_user_ids", [])
        if user_id in test_ids:
            await send_text(self.client, room.room_id, f"{user_id} is already a test user.")
            return
        test_ids.append(user_id)
        config["test_user_ids"] = test_ids
        save_config(config)
        await send_text(self.client, room.room_id, f"Added test user: {user_id}")

    async def cmd_testlist(self, room, _args=None):
        config = load_config()
        test_ids = config.get("test_user_ids", [])
        if not test_ids:
            await send_text(self.client, room.room_id, "No test users configured.")
            return
        lines = ["Test Users:"]
        for uid in test_ids:
            name = get_member_name(config, uid)
            lines.append(f"  • {name} ({uid})")
        await send_text(self.client, room.room_id, "\n".join(lines))

    async def cmd_announce(self, room, args):
        if not args:
            await send_text(self.client, room.room_id, "Usage: /announce <message text>")
            return
        self.pending_announcement = args
        msg = (
            "⚠️ **Review Announcement Draft**:\n\n"
            f"{args}\n\n"
            "Reply with `/confirm` to broadcast to all members, or `/cancel` to discard this draft."
        )
        await send_text(self.client, room.room_id, msg)

    async def cmd_confirm(self, room, _args=None):
        if not self.pending_announcement:
            await send_text(self.client, room.room_id, "No pending announcement to confirm.")
            return
        text = self.pending_announcement
        self.pending_announcement = None
        config = load_config()
        members = config.get("members", [])
        if not members:
            await send_text(self.client, room.room_id, "No members registered. Cannot send announcement.")
            return
        await send_text(self.client, room.room_id, f"Broadcasting announcement to {len(members)} members...")
        data = load_data()
        await send_announcement_to_members(self.client, config, data, text, members)
        await send_text(self.client, room.room_id, "Announcement broadcast complete. Status will be tracked via ✅ reactions.")

    async def cmd_cancel(self, room, _args=None):
        if not self.pending_announcement:
            await send_text(self.client, room.room_id, "No pending announcement to cancel.")
            return
        self.pending_announcement = None
        await send_text(self.client, room.room_id, "Announcement draft discarded.")

    async def on_reaction(self, room, event):
        if event.type != "m.reaction":
            return
        source = event.source if hasattr(event, "source") else {}
        content = source.get("content", {})
        relates = content.get("m.relates_to", {})
        if relates.get("rel_type") != "m.annotation":
            return
        reacted_to_id = relates.get("event_id")
        reaction_key = relates.get("key", "")
        sender = event.sender
        if sender == self.client.user_id:
            return
        if reaction_key != "✅":
            return
        try:
            resp = await self.client.room_get_event(room.room_id, reacted_to_id)
            if not hasattr(resp, "event") or resp.event.sender != self.client.user_id:
                return
        except Exception:
            return
        data = load_data()
        for ann in data["announcements"]:
            for sent in ann.get("sent_messages", []):
                if sent.get("event_id") == reacted_to_id:
                    if sender not in ann["completed_by"]:
                        ann["completed_by"].append(sender)
                        save_data(data)
                        name = get_member_name(load_config(), sender, sender)
                        log.info(f"{name} confirmed engagement for announcement #{ann['id']}")
                    return

    async def on_invite(self, room, event):
        if event.state_key == self.client.user_id:
            for attempt in range(3):
                result = await self.client.join(room.room_id)
                if not isinstance(result, JoinError):
                    log.info(f"Joined room {room.room_id}")
                    break
            else:
                log.error(f"Failed to join room {room.room_id} after 3 attempts")

    async def on_decryption_failure(self, room, event):
        log.warning(f"Decryption failure in {room.room_id}: {event}")


async def main():
    if not USER_ID:
        log.error("USER_ID must be set in .env")
        return
    if not PASSWORD and not ACCESS_TOKEN:
        log.error("Set either PASSWORD or ACCESS_TOKEN in .env")
        return

    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        store_sync_tokens=True,
        encryption_enabled=False,
    )

    client = AsyncClient(HOMESERVER, USER_ID, store_path=STORE_PATH, config=client_config)
    callbacks = BotCallbacks(client)

    client.add_event_callback(callbacks.on_message, RoomMessageText)
    client.add_event_callback(callbacks.on_invite, InviteMemberEvent)
    client.add_event_callback(callbacks.on_reaction, UnknownEvent)
    client.add_event_callback(callbacks.on_decryption_failure, MegolmEvent)

    if not await matrix_login(client, DEVICE_NAME):
        log.error("Login failed")
        return

    if client.should_upload_keys:
        await client.keys_upload()
        log.info("Encryption keys uploaded")

    log.info(f"Bot started as {USER_ID}")
    log.info(f"Admin: {ADMIN_ID}")
    # Import JoinError here since it's only needed in the callback
    from nio import JoinError
    await client.sync_forever(timeout=30000, full_state=True)


if __name__ == "__main__":
    asyncio.run(main())