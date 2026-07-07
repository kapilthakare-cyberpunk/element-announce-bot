import json
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = BASE_DIR / "config.json"
DATA_FILE = BASE_DIR / "data.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
STORE_PATH = str(BASE_DIR / "store")

# Load environment
load_dotenv(BASE_DIR / ".env")

HOMESERVER = os.getenv("HOMESERVER", "https://matrix.example.org")
USER_ID = os.getenv("USER_ID", "")
PASSWORD = os.getenv("PASSWORD", "")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
ROOM_ID = os.getenv("ROOM_ID", "")


def load_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error reading {path}: {e}")
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_config():
    return load_json(CONFIG_FILE, {"members": [], "test_user_ids": []})


def load_data():
    return load_json(DATA_FILE, {"announcements": []})


def save_config(config):
    save_json(CONFIG_FILE, config)


def save_data(data):
    save_json(DATA_FILE, data)


def get_member_name(config, user_id, default=None):
    for m in config["members"]:
        if m["user_id"] == user_id:
            return m["name"]
    return default or user_id


from nio import RoomPreset, RoomCreateResponse


async def find_dm_room(client, target_user_id):
    for room_id, room in client.rooms.items():
        member_ids = list(room.users.keys())
        if len(member_ids) == 2 and target_user_id in member_ids:
            return room_id
    return None


async def get_or_create_dm_room(client, target_user_id):
    dm_room = await find_dm_room(client, target_user_id)
    if dm_room:
        return dm_room

    # Create DM room without encryption (E2EE disabled)
    resp = await client.room_create(
        invite=[target_user_id],
        is_direct=True,
        preset=RoomPreset.trusted_private_chat,
    )
    if isinstance(resp, RoomCreateResponse):
        return resp.room_id
    return None
