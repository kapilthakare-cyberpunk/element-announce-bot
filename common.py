import json
import os
import fcntl
import logging
from pathlib import Path
from dotenv import load_dotenv
from nio import (
    AsyncClient,
    AsyncClientConfig,
    LoginError,
    RoomPreset,
    RoomCreateResponse,
)

BASE_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = BASE_DIR / "config.json"
DATA_FILE = BASE_DIR / "data.json"
TEMPLATES_FILE = BASE_DIR / "templates.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
STORE_PATH = str(BASE_DIR / "store")

load_dotenv(BASE_DIR / ".env")

HOMESERVER = os.getenv("HOMESERVER", "https://matrix.example.org")
USER_ID = os.getenv("USER_ID", "")
PASSWORD = os.getenv("PASSWORD", "")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
ROOM_ID = os.getenv("ROOM_ID", "")

log = logging.getLogger("element-bot")


def _lock_file(path):
    """Acquire an exclusive lock on a file. Creates the file if it does not exist."""
    f = open(path, "a")
    fcntl.flock(f, fcntl.LOCK_EX)
    return f


def load_json(path, default):
    try:
        if path.exists():
            lock = _lock_file(path)
            try:
                return json.loads(path.read_text())
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
                lock.close()
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"Error reading {path}: {e}")
    return default


def save_json(path, data):
    lock = _lock_file(path)
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def load_config():
    return load_json(CONFIG_FILE, {"members": [], "test_user_ids": [], "name_overrides": {}})


def load_data():
    return load_json(DATA_FILE, {"announcements": []})


def save_config(config):
    save_json(CONFIG_FILE, config)


def save_data(data):
    save_json(DATA_FILE, data)


def load_templates():
    return load_json(TEMPLATES_FILE, {"templates": []})


def save_templates(templates):
    save_json(TEMPLATES_FILE, templates)


def get_member_name(config, user_id, default=None):
    for m in config["members"]:
        if m["user_id"] == user_id:
            return m["name"]
    return default or user_id


def get_personal_name(member_name, config):
    """Apply name overrides (e.g. 'Abhijit Sir') from config."""
    overrides = config.get("name_overrides", {})
    lower = member_name.lower()
    for key, val in overrides.items():
        if key.lower() in lower:
            return val
    return member_name.split()[0]


async def matrix_login(client, device_name="element-announce-bot"):
    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text())
            client.user_id = creds["user_id"]
            client.access_token = creds["access_token"]
            client.device_id = creds["device_id"]
            return True
        except Exception:
            pass
    if ACCESS_TOKEN:
        client.user_id = USER_ID
        client.access_token = ACCESS_TOKEN
        CREDENTIALS_FILE.write_text(
            json.dumps({"user_id": USER_ID, "access_token": ACCESS_TOKEN, "device_id": "web"})
        )
        return True
    if PASSWORD:
        resp = await client.login(PASSWORD, device_name=device_name)
        if isinstance(resp, LoginError):
            return False
        CREDENTIALS_FILE.write_text(
            json.dumps({"user_id": client.user_id, "access_token": client.access_token, "device_id": client.device_id})
        )
        if client.should_upload_keys:
            await client.keys_upload()
        return True
    return False


def is_dm_room(room_obj):
    """Verify a room is a true 1-on-1 DM: exactly 2 members, no name."""
    if not room_obj:
        return False
    if len(room_obj.users) != 2:
        return False
    room_name = getattr(room_obj, "name", None)
    if room_name and room_name.strip():
        return False
    return True


async def find_dm_room(client, target_user_id):
    """Find an existing DM room with the target user."""
    direct_rooms = []
    unnamed_two_member = []

    for room_id, room in client.rooms.items():
        if target_user_id not in room.users:
            continue
        if len(room.users) != 2:
            continue
        room_name = getattr(room, "name", None)
        if room_name and room_name.strip():
            continue
        if hasattr(room, "is_direct") and room.is_direct:
            direct_rooms.append(room_id)
        else:
            unnamed_two_member.append(room_id)

    if direct_rooms:
        return direct_rooms[0]
    if unnamed_two_member:
        return unnamed_two_member[0]
    return None


async def get_or_create_dm_room(client, target_user_id):
    dm_room = await find_dm_room(client, target_user_id)
    if dm_room:
        return dm_room
    resp = await client.room_create(
        invite=[target_user_id],
        is_direct=True,
        preset=RoomPreset.trusted_private_chat,
    )
    if isinstance(resp, RoomCreateResponse):
        return resp.room_id
    return None


async def send_text(client, room_id, text):
    content = {
        "msgtype": "m.text",
        "body": text,
        "fi.mau.dont_render": True,
    }
    return await client.room_send(
        room_id, "m.room.message", content, ignore_unverified_devices=True
    )


async def send_html(client, room_id, body, html):
    content = {
        "msgtype": "m.text",
        "body": body,
        "format": "org.matrix.custom.html",
        "formatted_body": html,
        "fi.mau.dont_render": True,
    }
    return await client.room_send(
        room_id, "m.room.message", content, ignore_unverified_devices=True
    )


async def react_to(client, room_id, event_id, reaction):
    content = {
        "m.relates_to": {"rel_type": "m.annotation", "event_id": event_id, "key": reaction}
    }
    return await client.room_send(
        room_id, "m.reaction", content, ignore_unverified_devices=True
    )


async def redact_event(client, room_id, event_id, reason="Retracted by admin"):
    return await client.room_redact(room_id, event_id, reason, ignore_unverified_devices=True)


async def send_announcement_to_members(client, config, data, text, members, log_callback=None):
    """Send announcement to each member via DM.

    Returns (sent_list, updated_data, success_count).
    sent_list entries contain user_id, name, room_id, event_id.
    """
    _log = log_callback or (lambda msg, *a: log.info(msg))
    sent = []

    for m in members:
        try:
            room = await get_or_create_dm_room(client, m["user_id"])
            if not room:
                _log(f"No DM room for {m['name']}", "warning")
                continue
            room_obj = client.rooms.get(room)
            if not is_dm_room(room_obj):
                name_str = getattr(room_obj, "name", None) or "unnamed"
                member_count = len(room_obj.users) if room_obj else 0
                _log(f"SKIPPED group room for {m['name']}: '{name_str}' ({member_count} members)", "danger")
                continue
            await client.sync(timeout=3000)
            personal_name = get_personal_name(m["name"], config)
            personal_text = text.replace("<Name>", personal_name)
            resp = await send_text(client, room, personal_text)
            if hasattr(resp, "event_id"):
                sent.append({
                    "user_id": m["user_id"],
                    "name": m["name"],
                    "room_id": room,
                    "event_id": resp.event_id,
                })
                _log(f"Sent to {m['name']}", "success")
        except Exception as e:
            _log(f"Failed to send to {m['name']}: {e}", "danger")

    if sent:
        ann_id = len(data["announcements"]) + 1
        data["announcements"].append({
            "id": ann_id,
            "text": text,
            "completed_by": [],
            "sent_messages": sent,
        })
        save_data(data)
        _log(f"Announcement #{ann_id} sent to {len(sent)}/{len(members)} members", "success")
    else:
        _log("Failed to send announcement.", "danger")

    return sent, data, len(sent)