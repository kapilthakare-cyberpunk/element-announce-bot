"""
Element Announce Bot — Matrix/Element version of the Telegram Announce Bot.

Sends announcements to team members in an encrypted Matrix room.
Members confirm engagement by reacting with ✅ to the message.

Usage:
    python3 bot.py
"""

import json
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone

from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    JoinError,
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
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("element-bot")

DEVICE_NAME = "element-announce-bot"


# ---------------------------------------------------------------------------
# Matrix helpers
# ---------------------------------------------------------------------------


async def send_text(client, room_id, text):
    """Send a plain text message to a room (no URL previews)."""
    content = {
        "msgtype": "m.text",
        "body": text,
        "fi.mau.dont_render": True,
    }
    resp = await client.room_send(
        room_id,
        "m.room.message",
        content,
        ignore_unverified_devices=True,
    )
    return resp


async def send_html(client, room_id, body, html):
    """Send an HTML-formatted message to a room (no URL previews)."""
    content = {
        "msgtype": "m.text",
        "body": body,
        "format": "org.matrix.custom.html",
        "formatted_body": html,
        "fi.mau.dont_render": True,
    }
    resp = await client.room_send(
        room_id,
        "m.room.message",
        content,
        ignore_unverified_devices=True,
    )
    return resp


async def react_to(client, room_id, event_id, reaction):
    """Send a reaction to an event."""
    content = {
        "m.relates_to": {
            "rel_type": "m.annotation",
            "event_id": event_id,
            "key": reaction,
        }
    }
    resp = await client.room_send(
        room_id,
        "m.reaction",
        content,
        ignore_unverified_devices=True,
    )
    return resp


async def redact_event(client, room_id, event_id, reason="Retracted by admin"):
    """Delete (redact) a message."""
    resp = await client.room_redact(
        room_id,
        event_id,
        reason,
        ignore_unverified_devices=True,
    )
    return resp


async def create_room(client, name, topic, invite_users=None):
    """Create an encrypted room for team communication."""
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


# ---------------------------------------------------------------------------
# Bot callbacks
# ---------------------------------------------------------------------------


class BotCallbacks:
    """Handles incoming Matrix events."""

    def __init__(self, client):
        self.client = client

    async def on_message(self, room, event):
        """Handle incoming text messages."""
        if event.sender == self.client.user_id:
            return

        text = event.body.strip()
        sender = event.sender
        config = load_config()

        # Check if sender is admin
        is_admin = sender == ADMIN_ID

        if text.startswith("/"):
            await self.handle_command(room, event, text, is_admin)

    async def handle_command(self, room, event, text, is_admin):
        """Process bot commands."""
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            await self.cmd_help(room)
        elif cmd == "/register":
            await self.cmd_register(room, event, args)
        elif cmd == "/status":
            if is_admin:
                await self.cmd_status(room)
            else:
                await send_text(
                    self.client, room.room_id, "Only admin can use /status."
                )
        elif cmd == "/retract":
            if is_admin:
                await self.cmd_retract(room, args)
            else:
                await send_text(
                    self.client, room.room_id, "Only admin can use /retract."
                )
        elif cmd == "/members":
            if is_admin:
                await self.cmd_members(room)
            else:
                await send_text(
                    self.client, room.room_id, "Only admin can use /members."
                )
        elif cmd == "/settest":
            if is_admin:
                await self.cmd_settest(room, args)
            else:
                await send_text(
                    self.client, room.room_id, "Only admin can use /settest."
                )
        elif cmd == "/testlist":
            if is_admin:
                await self.cmd_testlist(room)
            else:
                await send_text(
                    self.client, room.room_id, "Only admin can use /testlist."
                )
        elif cmd == "/announce":
            if is_admin:
                await self.cmd_announce(room, args)
            else:
                await send_text(
                    self.client, room.room_id, "Only admin can use /announce."
                )

    async def cmd_help(self, room):
        help_text = (
            "Element Announce Bot — Commands:\n\n"
            "/register <name> — Register as a team member\n"
            "/status — Show latest announcement status (admin)\n"
            "/retract <id> — Retract an announcement (admin)\n"
            "/members — List all members (admin)\n"
            "/settest <user_id> — Add test user (admin)\n"
            "/testlist — List test users (admin)\n"
            "/announce <text> — Send announcement to all members (admin)\n"
            "\nTo confirm engagement: react with ✅ to any announcement message."
        )
        await send_text(self.client, room.room_id, help_text)

    async def cmd_register(self, room, event, name):
        """Register a member."""
        if not name:
            await send_text(self.client, room.room_id, "Usage: /register <your name>")
            return

        user_id = event.sender
        config = load_config()

        for m in config["members"]:
            if m["user_id"] == user_id:
                await send_text(
                    self.client,
                    room.room_id,
                    f"You are already registered as {m['name']}.",
                )
                return

        config["members"].append({"user_id": user_id, "name": name.strip()})
        save_config(config)

        await send_text(
            self.client,
            room.room_id,
            f"Welcome {name.strip()}! You are now registered.",
        )
        log.info(f"New member registered: {name.strip()} ({user_id})")

    async def cmd_status(self, room):
        """Show status of the latest announcement."""
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
        """Retract (redact) all messages for an announcement."""
        if not args:
            await send_text(
                self.client, room.room_id, "Usage: /retract <announcement_id>"
            )
            return

        try:
            ann_id = int(args.strip())
        except ValueError:
            await send_text(self.client, room.room_id, "Invalid announcement ID.")
            return

        data = load_data()
        target = None
        for a in data["announcements"]:
            if a["id"] == ann_id:
                target = a
                break

        if not target:
            await send_text(
                self.client, room.room_id, f"Announcement #{ann_id} not found."
            )
            return

        sent = target.get("sent_messages", [])
        if not sent:
            await send_text(
                self.client,
                room.room_id,
                f"Announcement #{ann_id} has no retractable messages.",
            )
            return

        deleted = 0
        for entry in sent:
            try:
                await redact_event(self.client, room.room_id, entry["event_id"])
                deleted += 1
            except Exception as e:
                log.warning(f"Failed to redact {entry['event_id']}: {e}")

        await send_text(
            self.client,
            room.room_id,
            f"Retracted {deleted}/{len(sent)} messages for announcement #{ann_id}.",
        )

    async def cmd_members(self, room):
        """List all registered members."""
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
        """Add a test user ID."""
        if not args:
            await send_text(self.client, room.room_id, "Usage: /settest <user_id>")
            return

        user_id = args.strip()
        config = load_config()
        test_ids = config.get("test_user_ids", [])

        if user_id in test_ids:
            await send_text(
                self.client, room.room_id, f"{user_id} is already a test user."
            )
            return

        test_ids.append(user_id)
        config["test_user_ids"] = test_ids
        save_config(config)
        await send_text(self.client, room.room_id, f"Added test user: {user_id}")

    async def cmd_testlist(self, room):
        """List test users."""
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
        """Send announcement to all members."""
        if not args:
            await send_text(
                self.client, room.room_id, "Usage: /announce <message text>"
            )
            return

        config = load_config()
        members = config.get("members", [])

        if not members:
            await send_text(
                self.client,
                room.room_id,
                "No members registered. Cannot send announcement.",
            )
            return

        data = load_data()
        ann_id = len(data["announcements"]) + 1
        sent_list = []

        for m in members:
            try:
                dm_room_id = await get_or_create_dm_room(self.client, m["user_id"])
                if dm_room_id:
                    resp = await send_text(self.client, dm_room_id, args)
                    if hasattr(resp, "event_id"):
                        sent_list.append(
                            {
                                "user_id": m["user_id"],
                                "name": m["name"],
                                "event_id": resp.event_id,
                            }
                        )
                        log.info(f"Sent announcement to {m['name']} in DM {dm_room_id}")
            except Exception as e:
                log.error(f"Failed to send to {m['name']}: {e}")

        if sent_list:
            data["announcements"].append(
                {
                    "id": ann_id,
                    "text": args,
                    "completed_by": [],
                    "sent_messages": sent_list,
                }
            )
            save_data(data)

            await send_text(
                self.client,
                room.room_id,
                f"Announcement #{ann_id} sent to DMs of {len(sent_list)}/{len(members)} members. Status will be tracked.",
            )
        else:
            await send_text(self.client, room.room_id, "Failed to send announcement.")

    async def on_reaction(self, room, event):
        """Handle reaction events (✅ confirmations)."""
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

        # Verify the reacted event is from the bot
        try:
            resp = await self.client.room_get_event(room.room_id, reacted_to_id)
            if not hasattr(resp, "event") or resp.event.sender != self.client.user_id:
                return
        except Exception:
            return

        # Find matching announcement
        data = load_data()
        for ann in data["announcements"]:
            for sent in ann.get("sent_messages", []):
                if sent.get("event_id") == reacted_to_id:
                    if sender not in ann["completed_by"]:
                        ann["completed_by"].append(sender)
                        save_data(data)
                        name = get_member_name(load_config(), sender, sender)
                        log.info(
                            f"{name} confirmed engagement for announcement #{ann['id']}"
                        )
                    return

    async def on_invite(self, room, event):
        """Auto-join rooms when invited."""
        if event.state_key == self.client.user_id:
            for attempt in range(3):
                result = await self.client.join(room.room_id)
                if not isinstance(result, JoinError):
                    log.info(f"Joined room {room.room_id}")
                    break
            else:
                log.error(f"Failed to join room {room.room_id} after 3 attempts")

    async def on_decryption_failure(self, room, event):
        """Handle decryption failures."""
        log.warning(f"Decryption failure in {room.room_id}: {event}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


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

    client = AsyncClient(
        HOMESERVER,
        USER_ID,
        store_path=STORE_PATH,
        config=client_config,
    )

    callbacks = BotCallbacks(client)

    # Register callbacks
    client.add_event_callback(callbacks.on_message, RoomMessageText)
    client.add_event_callback(callbacks.on_invite, InviteMemberEvent)
    client.add_event_callback(callbacks.on_reaction, UnknownEvent)
    client.add_event_callback(callbacks.on_decryption_failure, MegolmEvent)

    # Login
    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text())
            client.user_id = creds["user_id"]
            client.access_token = creds["access_token"]
            client.device_id = creds["device_id"]
            log.info("Loaded saved credentials")
        except Exception:
            log.info("Invalid credentials, logging in fresh")
            resp = await client.login(PASSWORD, device_name=DEVICE_NAME)
            if isinstance(resp, LoginError):
                log.error(f"Login failed: {resp.message}")
                return
            CREDENTIALS_FILE.write_text(
                json.dumps(
                    {
                        "user_id": client.user_id,
                        "access_token": client.access_token,
                        "device_id": client.device_id,
                    }
                )
            )
    elif ACCESS_TOKEN:
        client.access_token = ACCESS_TOKEN
        log.info("Using access token from .env")
    else:
        resp = await client.login(PASSWORD, device_name=DEVICE_NAME)
        if isinstance(resp, LoginError):
            log.error(f"Login failed: {resp.message}")
            return
        CREDENTIALS_FILE.write_text(
            json.dumps(
                {
                    "user_id": client.user_id,
                    "access_token": client.access_token,
                    "device_id": client.device_id,
                }
            )
        )

    # Upload encryption keys
    if client.should_upload_keys:
        await client.keys_upload()
        log.info("Encryption keys uploaded")

    log.info(f"Bot started as {USER_ID}")
    log.info(f"Admin: {ADMIN_ID}")

    # Sync forever
    await client.sync_forever(timeout=30000, full_state=True)


if __name__ == "__main__":
    asyncio.run(main())
