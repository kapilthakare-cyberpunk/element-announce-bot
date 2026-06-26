"""
Admin GUI for Element Announce Bot.

A CustomTkinter desktop application that wraps the bot's admin features
into a convenient graphical interface. Shares config.json and data.json
with bot.py but runs as a completely separate process.

Usage:
    python3 admin_gui.py
"""

import json
import os
import asyncio
import threading
from pathlib import Path

import customtkinter as ctk
from dotenv import load_dotenv
from nio import (
    AsyncClient,
    AsyncClientConfig,
    LoginError,
)

# ---------------------------------------------------------------------------
# Appearance
# ---------------------------------------------------------------------------

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------------
# Paths & env
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
DATA_FILE = BASE_DIR / "data.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
STORE_PATH = str(BASE_DIR / "store")

load_dotenv(BASE_DIR / ".env")
HOMESERVER = os.getenv("HOMESERVER", "https://matrix.example.org")
USER_ID = os.getenv("USER_ID", "")
PASSWORD = os.getenv("PASSWORD", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
ROOM_ID = os.getenv("ROOM_ID", "")
DEVICE_NAME = "element-announce-bot-gui"

# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Matrix helpers
# ---------------------------------------------------------------------------


def get_matrix_client():
    """Create an async Matrix client."""
    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        store_sync_tokens=True,
        encryption_enabled=True,
    )
    client = AsyncClient(
        HOMESERVER,
        USER_ID,
        store_path=STORE_PATH,
        config=client_config,
    )
    return client


async def matrix_login(client):
    """Login with saved credentials or fresh login."""
    if CREDENTIALS_FILE.exists():
        try:
            creds = json.loads(CREDENTIALS_FILE.read_text())
            client.user_id = creds["user_id"]
            client.access_token = creds["access_token"]
            client.device_id = creds["device_id"]
            return True
        except Exception:
            pass

    resp = await client.login(PASSWORD, device_name=DEVICE_NAME)
    if isinstance(resp, LoginError):
        return False

    CREDENTIALS_FILE.write_text(json.dumps({
        "user_id": client.user_id,
        "access_token": client.access_token,
        "device_id": client.device_id,
    }))

    if client.should_upload_keys:
        await client.keys_upload()

    return True


async def matrix_send(client, room_id, text):
    """Send a text message to a Matrix room."""
    content = {
        "msgtype": "m.text",
        "body": text,
    }
    resp = await client.room_send(
        room_id,
        "m.room.message",
        content,
        ignore_unverified_devices=True,
    )
    return resp


async def matrix_redact(client, room_id, event_id, reason="Retracted by admin"):
    """Redact (delete) a message."""
    resp = await client.room_redact(
        room_id,
        event_id,
        reason,
        ignore_unverified_devices=True,
    )
    return resp


# ===================================================================
# GUI Application
# ===================================================================


class AdminApp(ctk.CTk):
    """Main admin panel window."""

    def __init__(self):
        super().__init__()

        self.title("Element Announce Bot - Admin Panel")
        self.geometry("1000x720")
        self.minsize(800, 600)

        self.matrix_ready = bool(USER_ID and PASSWORD and ROOM_ID)

        self._build_ui()
        self._refresh_all()

    # ------------------------------------------------------------------
    # UI Build
    # ------------------------------------------------------------------

    def _build_ui(self):
        # -- Top status bar --
        top = ctk.CTkFrame(self, corner_radius=8)
        top.pack(fill="x", padx=12, pady=(12, 0))

        status_text = "Connected" if self.matrix_ready else "Check .env (HOMESERVER, USER_ID, PASSWORD, ROOM_ID)"
        self.status_label = ctk.CTkLabel(
            top,
            text=status_text,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.status_label.pack(side="left", padx=12, pady=10)

        admin_text = f"Admin: {ADMIN_ID}" if ADMIN_ID else "Admin: not set"
        ctk.CTkLabel(top, text=admin_text, font=ctk.CTkFont(size=12)).pack(
            side="right", padx=12, pady=10
        )

        # -- Tab view --
        self.tab = ctk.CTkTabview(self)
        self.tab.pack(fill="both", expand=True, padx=12, pady=(8, 0))

        # -- Bottom status bar --
        self.status_bar = ctk.CTkFrame(self, corner_radius=0, height=28)
        self.status_bar.pack(fill="x", padx=0, pady=(4, 0), side="bottom")
        self.status_bar_label = ctk.CTkLabel(
            self.status_bar, text="", anchor="w", font=ctk.CTkFont(size=12)
        )
        self.status_bar_label.pack(side="left", padx=12, pady=2)

        self._build_announce_tab()
        self._build_status_tab()
        self._build_members_tab()
        self._build_test_tab()
        self._build_settings_tab()

    # ================================
    #  TAB 1 - Announce
    # ================================

    def _build_announce_tab(self):
        tab = self.tab.add("Announce")

        # -- Text editor --
        ctk.CTkLabel(tab, text="Announcement Text", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4)
        )
        self.announce_text = ctk.CTkTextbox(tab, height=200, wrap="word")
        self.announce_text.pack(fill="x", padx=10, pady=(0, 10))

        # -- Buttons --
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 6))

        self.send_all_btn = ctk.CTkButton(
            btn_frame,
            text="Send to All Members",
            command=lambda: self._do_send_all(),
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.send_all_btn.pack(side="left", padx=(0, 8))

        self.send_test_btn = ctk.CTkButton(
            btn_frame,
            text="Send to Checked Members",
            command=lambda: self._do_send_test(),
            height=38,
            fg_color="#3B8ED0",
            font=ctk.CTkFont(size=13),
        )
        self.send_test_btn.pack(side="left")

        # -- Test user checkboxes --
        ctk.CTkLabel(tab, text="Select Test Recipients (checkbox to include)", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )
        self.test_check_frame = ctk.CTkScrollableFrame(tab, height=120)
        self.test_check_frame.pack(fill="x", padx=10, pady=(0, 6))
        self.test_checkvars = {}
        self._refresh_test_checkboxes()

        # -- Send log --
        ctk.CTkLabel(tab, text="Send Results", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=10, pady=(4, 4)
        )
        self.send_log = ctk.CTkScrollableFrame(tab, height=150)
        self.send_log.pack(fill="x", padx=10, pady=(0, 10))

    def _do_send_all(self):
        text = self.announce_text.get("1.0", "end-1c").strip()
        if not text:
            self._log_send("Cannot send - announcement text is empty.", "orange")
            return
        config = load_config()
        member_count = len(config.get("members", []))
        self._show_preview(text, member_count, "Send to All Members", lambda: self._confirm_send_all(text))

    def _confirm_send_all(self, text):
        self.send_all_btn.configure(state="disabled")
        self.send_test_btn.configure(state="disabled")
        self._clear_send_log()
        threading.Thread(
            target=self._send_all_worker, args=(text,), daemon=True
        ).start()

    def _send_all_worker(self, text):
        config = load_config()
        members = config["members"]

        if not members:
            self.after(0, lambda: self._log_send("No members in config. Add some first.", "orange"))
            self.after(0, lambda: self.send_all_btn.configure(state="normal"))
            self.after(0, lambda: self.send_test_btn.configure(state="normal"))
            return

        loop = asyncio.new_event_loop()
        client = get_matrix_client()

        async def _do():
            if not await matrix_login(client):
                self.after(0, lambda: self._log_send("Matrix login failed. Check .env.", "red"))
                return

            data = load_data()
            ann_id = len(data["announcements"]) + 1
            sent_list = []

            for m in members:
                try:
                    resp = await matrix_send(client, ROOM_ID, text)
                    if hasattr(resp, "event_id"):
                        sent_list.append({
                            "user_id": m["user_id"],
                            "name": m["name"],
                            "event_id": resp.event_id,
                        })
                        self.after(0, lambda n=m["name"]: self._log_send(f"Sent to {n}"))
                except Exception as e:
                    self.after(0, lambda n=m["name"]: self._log_send(f"Failed: {n} ({e})", "red"))

            data["announcements"].append({
                "id": ann_id,
                "text": text,
                "completed_by": [],
                "sent_messages": sent_list,
            })
            save_data(data)

            ok = len(sent_list)
            total = len(members)
            self.after(
                0,
                lambda: self._log_send(
                    f"Sent to {ok}/{total} members - announcement #{ann_id}",
                    "green",
                ),
            )
            await client.close()

        loop.run_until_complete(_do())
        loop.close()

        self.after(0, lambda: self.send_all_btn.configure(state="normal"))
        self.after(0, lambda: self.send_test_btn.configure(state="normal"))

    def _do_send_test(self):
        text = self.announce_text.get("1.0", "end-1c").strip()
        if not text:
            self._log_send("Cannot send - announcement text is empty.", "orange")
            return

        checked_ids = [uid for uid, var in self.test_checkvars.items() if var.get()]
        if not checked_ids:
            self._log_send("No test recipients checked. Tick at least one member above.", "orange")
            return

        config = load_config()
        checked_names = [m["name"] for m in config["members"] if m["user_id"] in checked_ids]
        self._show_preview(text, len(checked_names), f"Send to {len(checked_names)} Checked Members", lambda: self._confirm_send_test(text, checked_ids))

    def _confirm_send_test(self, text, checked_ids):
        self.send_all_btn.configure(state="disabled")
        self.send_test_btn.configure(state="disabled")
        self._clear_send_log()
        threading.Thread(
            target=self._send_test_worker, args=(text, checked_ids), daemon=True
        ).start()

    def _send_test_worker(self, text, test_ids):
        config = load_config()
        members = [m for m in config["members"] if m["user_id"] in test_ids]

        if not members:
            self.after(0, lambda: self._log_send("None of the checked IDs match registered members.", "orange"))
            self.after(0, lambda: self.send_all_btn.configure(state="normal"))
            self.after(0, lambda: self.send_test_btn.configure(state="normal"))
            return

        loop = asyncio.new_event_loop()
        client = get_matrix_client()

        async def _do():
            if not await matrix_login(client):
                self.after(0, lambda: self._log_send("Matrix login failed. Check .env.", "red"))
                return

            ok = 0
            for m in members:
                try:
                    resp = await matrix_send(client, ROOM_ID, text)
                    if hasattr(resp, "event_id"):
                        ok += 1
                        self.after(0, lambda n=m["name"]: self._log_send(f"Sent test to {n}"))
                except Exception as e:
                    self.after(0, lambda n=m["name"]: self._log_send(f"Failed: {n} ({e})", "red"))

            self.after(0, lambda: self._log_send(f"Test sent to {ok}/{len(members)} users.", "green"))
            await client.close()

        loop.run_until_complete(_do())
        loop.close()

        self.after(0, lambda: self.send_all_btn.configure(state="normal"))
        self.after(0, lambda: self.send_test_btn.configure(state="normal"))

    def _refresh_test_checkboxes(self):
        for w in self.test_check_frame.winfo_children():
            w.destroy()
        self.test_checkvars.clear()

        config = load_config()
        for m in config["members"]:
            var = ctk.BooleanVar(value=False)
            self.test_checkvars[m["user_id"]] = var
            cb = ctk.CTkCheckBox(
                self.test_check_frame,
                text=f"{m['name']}  ({m['user_id']})",
                variable=var,
                font=ctk.CTkFont(size=12),
            )
            cb.pack(anchor="w", padx=6, pady=1)

    # ---- Send log helpers ----

    def _clear_send_log(self):
        for w in self.send_log.winfo_children():
            w.destroy()

    def _log_send(self, text, color=None):
        lbl = ctk.CTkLabel(self.send_log, text=text, anchor="w", justify="left")
        if color:
            lbl.configure(text_color=color)
        lbl.pack(fill="x", padx=6, pady=1)

    def _status_bar_msg(self, text, color=None):
        self.status_bar_label.configure(text=text)
        if color:
            self.status_bar_label.configure(text_color=color)

    def _show_preview(self, text, recipient_count, button_label, on_confirm):
        win = ctk.CTkToplevel(self)
        win.title("Preview Message")
        win.geometry("520x520")
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="Message Preview", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=14, pady=(14, 6)
        )

        preview = ctk.CTkTextbox(win, height=300, wrap="word")
        preview.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        preview.insert("1.0", text)
        preview.configure(state="disabled")

        info = f"Will be sent to {recipient_count} member(s)"
        ctk.CTkLabel(win, text=info, font=ctk.CTkFont(size=12), text_color="gray").pack(
            anchor="w", padx=14, pady=(0, 10)
        )

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=14, pady=(0, 14))

        def confirm():
            win.destroy()
            on_confirm()

        ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color="gray",
                       command=win.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text=button_label, width=200, height=38,
                       font=ctk.CTkFont(size=13, weight="bold"),
                       command=confirm).pack(side="right")

    # ================================
    #  TAB 2 - Status
    # ================================

    def _build_status_tab(self):
        tab = self.tab.add("Status")

        self.status_header = ctk.CTkLabel(
            tab, text="Latest Announcement", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.status_header.pack(anchor="w", padx=10, pady=(12, 4))

        self.status_frame = ctk.CTkScrollableFrame(tab, height=280)
        self.status_frame.pack(fill="x", padx=10, pady=(0, 8))

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(btn_row, text="Refresh", command=self._refresh_status,
                       width=120).pack(side="left")

        # -- Past announcements --
        ctk.CTkLabel(tab, text="Past Announcements", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )

        past_row = ctk.CTkFrame(tab, fg_color="transparent")
        past_row.pack(fill="x", padx=10, pady=(0, 10))

        self.past_menu = ctk.CTkOptionMenu(past_row, width=250, dynamic_resizing=False)
        self.past_menu.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            past_row, text="Retract Selected", command=self._do_retract,
            fg_color="#C73E3E", hover_color="#962828", width=140
        ).pack(side="left")

    def _refresh_status(self):
        config = load_config()
        data = load_data()

        for w in self.status_frame.winfo_children():
            w.destroy()

        if not data["announcements"]:
            self.status_header.configure(text="Latest Announcement - none yet")
            ctk.CTkLabel(self.status_frame, text="No announcements sent yet.").pack(padx=6, pady=20)
            self.past_menu.configure(values=["(no announcements)"])
            self.past_menu.set("(no announcements)")
            return

        latest = data["announcements"][-1]
        self.status_header.configure(text=f"Announcement #{latest['id']}")
        completed = set(latest.get("completed_by", []))

        for m in config["members"]:
            icon = "✅" if m["user_id"] in completed else "⬜"
            row = ctk.CTkFrame(self.status_frame, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(row, text=f"{icon}  {m['name']}", anchor="w").pack(side="left")

        done = len(completed)
        total = len(config["members"])
        ctk.CTkLabel(
            self.status_frame,
            text=f"\n{done}/{total} completed",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#3B8ED0",
        ).pack(padx=4, pady=(8, 4))

        choices = [f"#{a['id']} - {a['text'][:50].strip()}..." for a in data["announcements"]]
        self.past_menu.configure(values=choices)
        self.past_menu.set(choices[-1])

    def _do_retract(self):
        selection = self.past_menu.get()
        if not selection or selection.startswith("(no"):
            return
        ann_id = int(selection.split("-")[0].strip().lstrip("#"))
        self._run_retract(ann_id)

    def _run_retract(self, ann_id):
        threading.Thread(target=self._retract_worker, args=(ann_id,), daemon=True).start()

    def _retract_worker(self, ann_id):
        data = load_data()
        target = next((a for a in data["announcements"] if a["id"] == ann_id), None)
        if not target or not target.get("sent_messages"):
            self.after(0, lambda: self._status_bar_msg(f"Announcement #{ann_id} has no retractable messages.", "orange"))
            return

        loop = asyncio.new_event_loop()
        client = get_matrix_client()

        async def _do():
            if not await matrix_login(client):
                self.after(0, lambda: self._status_bar_msg("Matrix login failed.", "red"))
                return

            deleted = 0
            total = len(target["sent_messages"])
            for entry in target["sent_messages"]:
                try:
                    await matrix_redact(client, ROOM_ID, entry["event_id"])
                    deleted += 1
                except Exception:
                    pass

            result = f"Retracted {deleted}/{total} messages for announcement #{ann_id}."
            self.after(0, lambda: self._refresh_status())
            self.after(0, lambda: self._status_bar_msg(result, "green" if deleted else "orange"))
            await client.close()

        loop.run_until_complete(_do())
        loop.close()

    # ================================
    #  TAB 3 - Members
    # ================================

    def _build_members_tab(self):
        tab = self.tab.add("Members")

        # -- Add form --
        ctk.CTkLabel(tab, text="Add Member", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4)
        )
        add_row = ctk.CTkFrame(tab, fg_color="transparent")
        add_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(add_row, text="User ID:").pack(side="left")
        self.add_id_entry = ctk.CTkEntry(add_row, width=250, placeholder_text="@user:example.org")
        self.add_id_entry.pack(side="left", padx=(4, 12))

        ctk.CTkLabel(add_row, text="Name:").pack(side="left")
        self.add_name_entry = ctk.CTkEntry(add_row, width=200, placeholder_text="Full name")
        self.add_name_entry.pack(side="left", padx=(4, 8))

        ctk.CTkButton(add_row, text="Add", command=self._do_add_member,
                       width=80).pack(side="left")

        # -- Member list --
        self.member_list_label = ctk.CTkLabel(
            tab, text="Team Members", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.member_list_label.pack(anchor="w", padx=10, pady=(4, 4))

        self.member_frame = ctk.CTkScrollableFrame(tab, height=280)
        self.member_frame.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkButton(tab, text="Refresh", command=self._refresh_members,
                       width=120).pack(anchor="w", padx=10, pady=(0, 10))

    def _refresh_members(self):
        config = load_config()
        for w in self.member_frame.winfo_children():
            w.destroy()

        self.member_list_label.configure(text=f"Team Members ({len(config['members'])})")

        for m in config["members"]:
            row = ctk.CTkFrame(self.member_frame, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(
                row, text=f"  {m['name']}", anchor="w", width=250
            ).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                row, text=f"{m['user_id']}", anchor="w", width=250,
                font=ctk.CTkFont(family="Courier", size=12)
            ).pack(side="left")
            ctk.CTkButton(
                row, text="X", width=32, height=24, fg_color="#C73E3E",
                hover_color="#962828",
                command=lambda uid=m["user_id"]: self._remove_member(uid),
            ).pack(side="right", padx=(0, 4))

    def _do_add_member(self):
        uid = self.add_id_entry.get().strip()
        name = self.add_name_entry.get().strip()
        if not uid or not name:
            self._status_bar_msg("Enter both User ID and Name.", "orange")
            return

        config = load_config()
        if get_member_name(config, uid) != uid:
            self._status_bar_msg(f"{name} is already a member.", "orange")
            return
        config["members"].append({"user_id": uid, "name": name})
        save_config(config)
        self.add_id_entry.delete(0, "end")
        self.add_name_entry.delete(0, "end")
        self._refresh_members()
        self._refresh_test_checkboxes()
        self._status_bar_msg(f"Added {name} ({uid})", "green")

    def _remove_member(self, uid):
        config = load_config()
        before = len(config["members"])
        config["members"] = [m for m in config["members"] if m["user_id"] != uid]
        if len(config["members"]) < before:
            save_config(config)
            self._refresh_members()
            self._refresh_test_checkboxes()

    # ================================
    #  TAB 4 - Test Users
    # ================================

    def _build_test_tab(self):
        tab = self.tab.add("Test Users")

        ctk.CTkLabel(tab, text="Add Test User ID", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4)
        )
        add_row = ctk.CTkFrame(tab, fg_color="transparent")
        add_row.pack(fill="x", padx=10, pady=(0, 10))

        self.test_id_entry = ctk.CTkEntry(add_row, width=250, placeholder_text="@user:example.org")
        self.test_id_entry.pack(side="left", padx=(0, 8))

        ctk.CTkButton(add_row, text="Add ID", command=self._do_add_test_id,
                       width=90).pack(side="left")

        self.test_list_label = ctk.CTkLabel(
            tab, text="Test Recipients", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.test_list_label.pack(anchor="w", padx=10, pady=(4, 4))

        self.test_frame = ctk.CTkScrollableFrame(tab, height=220)
        self.test_frame.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(
            tab,
            text="These users will receive test messages.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=10, pady=(0, 6))

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(btn_row, text="Clear All", command=self._do_clear_test_ids,
                       fg_color="#C73E3E", hover_color="#962828", width=100).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Refresh", command=self._refresh_test,
                       width=100).pack(side="left")

    def _refresh_test(self):
        config = load_config()
        test_ids = config.get("test_user_ids", [])

        for w in self.test_frame.winfo_children():
            w.destroy()

        self.test_list_label.configure(text=f"Test Recipients ({len(test_ids)})")

        for uid in test_ids:
            name = get_member_name(config, uid)
            is_registered = name != uid
            icon = "✅" if is_registered else "❓"
            label_text = f"{icon}  {name} - {uid}" if is_registered else f"{icon}  {uid} - not registered"

            row = ctk.CTkFrame(self.test_frame, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            ctk.CTkLabel(row, text=label_text, anchor="w").pack(side="left")
            ctk.CTkButton(
                row, text="X", width=32, height=24, fg_color="#C73E3E",
                hover_color="#962828",
                command=lambda u=uid: self._remove_test_id(u),
            ).pack(side="right", padx=(0, 4))

    def _do_add_test_id(self):
        uid = self.test_id_entry.get().strip()
        if not uid:
            return

        config = load_config()
        current = config.get("test_user_ids", [])
        if uid in current:
            self._status_bar_msg(f"{uid} is already a test user.", "orange")
            return
        current.append(uid)
        config["test_user_ids"] = current
        save_config(config)
        self.test_id_entry.delete(0, "end")
        self._refresh_test()
        self._status_bar_msg(f"Added test user {uid}", "green")

    def _remove_test_id(self, uid):
        config = load_config()
        current = config.get("test_user_ids", [])
        if uid in current:
            current.remove(uid)
            config["test_user_ids"] = current
            save_config(config)
            self._refresh_test()

    def _do_clear_test_ids(self):
        config = load_config()
        config["test_user_ids"] = []
        save_config(config)
        self._refresh_test()
        self._status_bar_msg("Test user IDs cleared.", "green")

    # ================================
    #  TAB 5 - Settings
    # ================================

    def _build_settings_tab(self):
        tab = self.tab.add("Settings")

        ctk.CTkLabel(
            tab, text="Bot Configuration", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=(16, 12))

        self._settings_row(tab, "Homeserver:", HOMESERVER or "Not set")
        self._settings_row(tab, "User ID:", USER_ID or "Not set")
        self._settings_row(tab, "Room ID:", ROOM_ID or "Not set")
        self._settings_row(tab, "Admin:", ADMIN_ID or "Not set")

        status = "Configured" if self.matrix_ready else "Not configured"
        self._settings_row(tab, "Status:", status)

        ctk.CTkFrame(tab, height=2, fg_color="gray").pack(fill="x", padx=10, pady=16)

        ctk.CTkLabel(
            tab, text="Data Files", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=(0, 12))

        self._settings_row(tab, "Config:", str(CONFIG_FILE))
        self._settings_row(tab, "Data:", str(DATA_FILE))
        self._settings_row(tab, ".env:", str(BASE_DIR / ".env"))

        ctk.CTkLabel(
            tab,
            text="\nThe admin GUI shares config.json and data.json with bot.py.\n"
                 "Changes made here are immediately visible to the bot and vice versa.\n\n"
                 "Members confirm engagement by reacting with ✅ to announcements.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="left",
        ).pack(anchor="w", padx=10, pady=(16, 0))

    @staticmethod
    def _settings_row(parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row, text=label, width=120, anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(row, text=value, anchor="w").pack(side="left", padx=(8, 0))

    # ------------------------------------------------------------------
    # Batch refresh
    # ------------------------------------------------------------------

    def _refresh_all(self):
        self._refresh_status()
        self._refresh_members()
        self._refresh_test()
        self._refresh_test_checkboxes()


# ===================================================================
# Entry point
# ===================================================================

if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
