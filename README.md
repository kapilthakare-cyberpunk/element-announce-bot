# Element Announce Bot

A Matrix/Element version of the Telegram Announce Bot. Sends announcements to team members in an encrypted Matrix room. Members confirm engagement by reacting with ✅ to messages.

## Features

- **Announcement broadcasting** — send messages to all team members
- **Engagement tracking** — members react with ✅ to confirm; admin sees live status
- **Retraction** — admin can redact (delete) announcements
- **Test mode** — send to selected members without saving to history
- **Member management** — add/remove/list team members
- **Dual interface** — CLI bot commands AND a desktop GUI admin panel
- **End-to-end encryption** — all messages encrypted via Matrix E2EE

## Bot Commands

| Command | Description |
|---------|-------------|
| `/register <name>` | Register as a team member |
| `/status` | Show latest announcement completion status (admin) |
| `/retract <id>` | Redact an announcement (admin) |
| `/members` | List all registered members (admin) |
| `/settest <user_id>` | Add test user (admin) |
| `/testlist` | List test users (admin) |
| `/announce <text>` | Send announcement to all members (admin) |
| `/help` | Show available commands |

## Setup

### 1. Create a Matrix bot account

1. Register a new account on your Matrix homeserver (or use an existing one)
2. Note the `@user:homeserver.org` format User ID
3. Get the Room ID of your team room (click room settings → Advanced → Room ID)

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```
HOMESERVER=https://matrix.yourserver.org
USER_ID=@yourbot:yourserver.org
PASSWORD=your-bot-password
ADMIN_ID=@admin:yourserver.org
ROOM_ID=!roomid:yourserver.org
```

### 3. Install dependencies

```bash
# macOS (required for E2EE)
brew install libolm

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the bot

```bash
python3 bot.py
```

### 5. Run the admin GUI

```bash
python3 admin_gui.py
```

Or double-click `launch.command` on macOS.

## Data Files

- `config.json` — team member list and test user IDs
- `data.json` — announcement history with completion tracking
- `store/` — Matrix E2EE state (auto-created, do not delete)
- `credentials.json` — bot login session (auto-created)

## How Engagement Works

1. Admin sends announcement via GUI or `/announce` command
2. All team members receive the message in the Matrix room
3. Each member reacts with ✅ to confirm they engaged
4. Admin checks `/status` or the Status tab to see who completed

## Requirements

- Python 3.10+
- `libolm` (for E2EE support)
- A Matrix homeserver account
- Element 1.12.22 or compatible client

## License

MIT
