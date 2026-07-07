"""
Admin GUI for Element Announce Bot — Polished Editorial Design.

A CustomTkinter desktop application with a refined visual system.
Shares config.json and data.json with bot.py.
"""

import json
import os
import asyncio
import threading
from pathlib import Path

import customtkinter as ctk
from nio import (
    AsyncClient,
    AsyncClientConfig,
    LoginError,
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
# Visual System
# ---------------------------------------------------------------------------

THEME_PATH = Path(__file__).parent / "theme.json"
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme(str(THEME_PATH))


# Color palette
class Colors:
    # Primary
    TEAL = "#14B8A6"
    TEAL_DARK = "#0D9488"
    TEAL_DEEPER = "#0F766E"

    # Semantic
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"
    DANGER_HOVER = "#DC2626"
    INFO = "#3B82F6"

    # Neutral
    BG_DARK = "#0F1117"
    BG_CARD = "#1A1D23"
    BG_CARD_HOVER = "#22262E"
    BORDER = "#2D3139"
    TEXT_PRIMARY = "#F9FAFB"
    TEXT_SECONDARY = "#9CA3AF"
    TEXT_MUTED = "#6B7280"


DEVICE_NAME = "element-announce-bot-gui"


# ---------------------------------------------------------------------------
# Matrix helpers
# ---------------------------------------------------------------------------


def get_matrix_client():
    """Create an async Matrix client."""
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

    CREDENTIALS_FILE.write_text(
        json.dumps(
            {
                "user_id": client.user_id,
                "access_token": client.access_token,
                "device_id": client.device_id,
            }
        )
    )

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

        self.title("Element Announce Bot")
        self.geometry("1080x760")
        self.minsize(900, 650)

        self.matrix_ready = bool(USER_ID and (PASSWORD or ACCESS_TOKEN))

        self._build_ui()
        self._refresh_all()

    # ------------------------------------------------------------------
    # UI Build
    # ------------------------------------------------------------------

    def _build_ui(self):
        # -- Main container --
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=16, pady=16)

        # -- Top branding bar --
        self._build_header()

        # -- Tab view --
        self.tab = ctk.CTkTabview(
            self.main_container,
            corner_radius=12,
            segmented_button_fg_color=Colors.BG_CARD,
            segmented_button_selected_color=Colors.TEAL,
            segmented_button_selected_hover_color=Colors.TEAL_DARK,
            segmented_button_unselected_color=Colors.BG_CARD,
            segmented_button_unselected_hover_color=Colors.BG_CARD_HOVER,
        )
        self.tab.pack(fill="both", expand=True, pady=(12, 0))

        # -- Bottom status bar --
        self._build_status_bar()

        self._build_announce_tab()
        self._build_status_tab()
        self._build_members_tab()
        self._build_test_tab()
        self._build_settings_tab()

    def _build_header(self):
        header = ctk.CTkFrame(self.main_container, fg_color="transparent", height=60)
        header.pack(fill="x", pady=(0, 4))
        header.pack_propagate(False)

        # Brand icon + title
        brand_frame = ctk.CTkFrame(header, fg_color="transparent")
        brand_frame.pack(side="left", fill="y")

        ctk.CTkLabel(
            brand_frame,
            text="⚡",
            font=ctk.CTkFont(size=28),
            text_color=Colors.TEAL,
        ).pack(side="left", padx=(0, 8))

        title_frame = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_frame.pack(side="left", fill="y")

        ctk.CTkLabel(
            title_frame,
            text="Element Announce Bot",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_frame,
            text="Team broadcast & engagement tracking",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w")

        # Status indicator
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", fill="y")

        if self.matrix_ready:
            dot_color = Colors.SUCCESS
            status_text = "Connected"
            status_sub = f"Admin: {ADMIN_ID.split(':')[0][1:]}" if ADMIN_ID else ""
        else:
            dot_color = Colors.DANGER
            status_text = "Not Connected"
            status_sub = "Check .env configuration"

        ctk.CTkLabel(
            status_frame,
            text="●",
            font=ctk.CTkFont(size=10),
            text_color=dot_color,
        ).pack(side="left", padx=(0, 4))

        info_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="y")

        ctk.CTkLabel(
            info_frame,
            text=status_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="e")

        ctk.CTkLabel(
            info_frame,
            text=status_sub,
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="e")

    def _build_status_bar(self):
        self.status_bar = ctk.CTkFrame(
            self.main_container,
            corner_radius=8,
            height=36,
            fg_color=Colors.BG_CARD,
        )
        self.status_bar.pack(fill="x", pady=(8, 0))
        self.status_bar.pack_propagate(False)

        self.status_bar_icon = ctk.CTkLabel(
            self.status_bar,
            text="ℹ",
            font=ctk.CTkFont(size=12),
            text_color=Colors.INFO,
            width=24,
        )
        self.status_bar_icon.pack(side="left", padx=(12, 0))

        self.status_bar_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_SECONDARY,
        )
        self.status_bar_label.pack(side="left", padx=(4, 12), fill="y")

    # ================================
    #  TAB 1 - Announce
    # ================================

    def _build_announce_tab(self):
        tab = self.tab.add("  Announce  ")

        # -- Section: Compose --
        compose_header = ctk.CTkFrame(tab, fg_color="transparent")
        compose_header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            compose_header,
            text="COMPOSE ANNOUNCEMENT",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w")

        ctk.CTkLabel(
            compose_header,
            text="Write your message below. It will be sent as a direct message to each team member.",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # -- Text editor with border --
        editor_container = ctk.CTkFrame(
            tab,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
            fg_color=Colors.BG_CARD,
        )
        editor_container.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.announce_text = ctk.CTkTextbox(
            editor_container,
            height=180,
            wrap="word",
            corner_radius=10,
            border_width=0,
            fg_color=Colors.BG_CARD,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
        )
        self.announce_text.pack(fill="both", expand=True, padx=2, pady=2)

        # -- Action buttons --
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        self.send_all_btn = ctk.CTkButton(
            btn_frame,
            text="  Send to All Members  ",
            command=lambda: self._do_send_all(),
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
        )
        self.send_all_btn.pack(side="left", padx=(0, 10))

        self.send_test_btn = ctk.CTkButton(
            btn_frame,
            text="  Send to Selected  ",
            command=lambda: self._do_send_test(),
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=2,
            border_color=Colors.TEAL,
            text_color=Colors.TEAL,
            hover_color=Colors.BG_CARD_HOVER,
        )
        self.send_test_btn.pack(side="left")

        # -- Test recipients section --
        recipients_frame = ctk.CTkFrame(tab, fg_color="transparent")
        recipients_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            recipients_frame,
            text="SELECT RECIPIENTS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w", pady=(0, 6))

        self.test_check_frame = ctk.CTkScrollableFrame(
            recipients_frame,
            height=100,
            corner_radius=8,
            fg_color=Colors.BG_CARD,
        )
        self.test_check_frame.pack(fill="x")
        self.test_checkvars = {}
        self._refresh_test_checkboxes()

        # -- Send log --
        log_frame = ctk.CTkFrame(tab, fg_color="transparent")
        log_frame.pack(fill="x", padx=16, pady=(8, 16))

        ctk.CTkLabel(
            log_frame,
            text="ACTIVITY LOG",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w", pady=(0, 6))

        self.send_log = ctk.CTkScrollableFrame(
            log_frame,
            height=120,
            corner_radius=8,
            fg_color=Colors.BG_CARD,
        )
        self.send_log.pack(fill="x")

    def _do_send_all(self):
        text = self.announce_text.get("1.0", "end-1c").strip()
        if not text:
            self._log_send("Cannot send — announcement text is empty.", Colors.WARNING)
            return
        config = load_config()
        member_count = len(config.get("members", []))
        self._show_preview(
            text,
            member_count,
            "Send to All Members",
            lambda: self._confirm_send_all(text),
        )

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
            self.after(
                0,
                lambda: self._log_send(
                    "No members in config. Add some first.", Colors.WARNING
                ),
            )
            self.after(0, lambda: self.send_all_btn.configure(state="normal"))
            self.after(0, lambda: self.send_test_btn.configure(state="normal"))
            return

        loop = asyncio.new_event_loop()
        client = get_matrix_client()

        async def _do():
            if not await matrix_login(client):
                self.after(
                    0,
                    lambda: self._log_send(
                        "Matrix login failed. Check .env.", Colors.DANGER
                    ),
                )
                return

            data = load_data()
            ann_id = len(data["announcements"]) + 1
            sent_list = []

            for m in members:
                try:
                    dm_room_id = await get_or_create_dm_room(client, m["user_id"])
                    if dm_room_id:
                        resp = await matrix_send(client, dm_room_id, text)
                        if hasattr(resp, "event_id"):
                            sent_list.append(
                                {
                                    "user_id": m["user_id"],
                                    "name": m["name"],
                                    "event_id": resp.event_id,
                                }
                            )
                            self.after(
                                0,
                                lambda n=m["name"]: self._log_send(
                                    f"✓ Sent to {n}", Colors.SUCCESS
                                ),
                            )
                except Exception as e:
                    self.after(
                        0,
                        lambda n=m["name"]: self._log_send(
                            f"✗ Failed: {n} — {e}", Colors.DANGER
                        ),
                    )

            if sent_list:
                data["announcements"].append(
                    {
                        "id": ann_id,
                        "text": text,
                        "completed_by": [],
                        "sent_messages": sent_list,
                    }
                )
                save_data(data)
                self.after(
                    0,
                    lambda: self._log_send(
                        f"Announcement #{ann_id} delivered to {len(sent_list)}/{len(members)} members",
                        Colors.SUCCESS,
                    ),
                )
            else:
                self.after(
                    0,
                    lambda: self._log_send(
                        "Failed to send announcement", Colors.DANGER
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
            self._log_send("Cannot send — announcement text is empty.", Colors.WARNING)
            return

        checked_ids = [uid for uid, var in self.test_checkvars.items() if var.get()]
        if not checked_ids:
            self._log_send(
                "No recipients selected. Check at least one member above.",
                Colors.WARNING,
            )
            return

        config = load_config()
        checked_names = [
            m["name"] for m in config["members"] if m["user_id"] in checked_ids
        ]
        self._show_preview(
            text,
            len(checked_names),
            f"Send to {len(checked_names)} Selected",
            lambda: self._confirm_send_test(text, checked_ids),
        )

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
            self.after(
                0,
                lambda: self._log_send(
                    "None of the checked IDs match registered members.", Colors.WARNING
                ),
            )
            self.after(0, lambda: self.send_all_btn.configure(state="normal"))
            self.after(0, lambda: self.send_test_btn.configure(state="normal"))
            return

        loop = asyncio.new_event_loop()
        client = get_matrix_client()

        async def _do():
            if not await matrix_login(client):
                self.after(
                    0,
                    lambda: self._log_send(
                        "Matrix login failed. Check .env.", Colors.DANGER
                    ),
                )
                return

            ok = 0
            for m in members:
                try:
                    dm_room_id = await get_or_create_dm_room(client, m["user_id"])
                    if dm_room_id:
                        resp = await matrix_send(client, dm_room_id, text)
                        if hasattr(resp, "event_id"):
                            ok += 1
                            self.after(
                                0,
                                lambda n=m["name"]: self._log_send(
                                    f"✓ Sent to {n}", Colors.SUCCESS
                                ),
                            )
                except Exception as e:
                    self.after(
                        0,
                        lambda n=m["name"]: self._log_send(
                            f"✗ Failed: {n} — {e}", Colors.DANGER
                        ),
                    )

            self.after(
                0,
                lambda: self._log_send(
                    f"Test sent to {ok}/{len(members)} members", Colors.SUCCESS
                ),
            )
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
                text=f"{m['name']}",
                variable=var,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_PRIMARY,
            )
            cb.pack(anchor="w", padx=8, pady=2)

    # ---- Send log helpers ----

    def _clear_send_log(self):
        for w in self.send_log.winfo_children():
            w.destroy()

    def _log_send(self, text, color=None):
        lbl = ctk.CTkLabel(
            self.send_log,
            text=text,
            anchor="w",
            justify="left",
            font=ctk.CTkFont(size=11),
        )
        if color:
            lbl.configure(text_color=color)
        else:
            lbl.configure(text_color=Colors.TEXT_SECONDARY)
        lbl.pack(fill="x", padx=8, pady=2)

    def _status_bar_msg(self, text, color=None):
        self.status_bar_label.configure(text=text)
        if color:
            self.status_bar_label.configure(text_color=color)
            icons = {
                Colors.SUCCESS: "✓",
                Colors.WARNING: "⚠",
                Colors.DANGER: "✗",
                Colors.INFO: "ℹ",
            }
            self.status_bar_icon.configure(text=icons.get(color, "ℹ"), text_color=color)

    def _show_preview(self, text, recipient_count, button_label, on_confirm):
        win = ctk.CTkToplevel(self)
        win.title("Preview")
        win.geometry("560x520")
        win.transient(self)
        win.grab_set()
        win.configure(fg_color=Colors.BG_DARK)

        # Header
        header = ctk.CTkFrame(win, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 12))

        ctk.CTkLabel(
            header,
            text="MESSAGE PREVIEW",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text=f"This message will be sent to {recipient_count} member(s) via DM",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # Preview box
        preview_container = ctk.CTkFrame(
            win,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
            fg_color=Colors.BG_CARD,
        )
        preview_container.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        preview = ctk.CTkTextbox(
            preview_container,
            wrap="word",
            corner_radius=10,
            border_width=0,
            fg_color=Colors.BG_CARD,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
        )
        preview.pack(fill="both", expand=True, padx=2, pady=2)
        preview.insert("1.0", text)
        preview.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        def confirm():
            win.destroy()
            on_confirm()

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=120,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            border_width=2,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BG_CARD_HOVER,
            command=win.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text=button_label,
            width=220,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
            command=confirm,
        ).pack(side="right")

    # ================================
    #  TAB 2 - Status
    # ================================

    def _build_status_tab(self):
        tab = self.tab.add("  Status  ")

        # -- Section header --
        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))

        self.status_header = ctk.CTkLabel(
            header,
            text="LATEST ANNOUNCEMENT",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        )
        self.status_header.pack(anchor="w")

        # -- Status content --
        self.status_frame = ctk.CTkScrollableFrame(
            tab,
            height=280,
            corner_radius=10,
            fg_color=Colors.BG_CARD,
        )
        self.status_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # -- Action row --
        action_row = ctk.CTkFrame(tab, fg_color="transparent")
        action_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            action_row,
            text="  Refresh  ",
            command=self._refresh_status,
            width=120,
            height=36,
            corner_radius=8,
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
        ).pack(side="left")

        # -- Past announcements --
        past_header = ctk.CTkFrame(tab, fg_color="transparent")
        past_header.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(
            past_header,
            text="ANNOUNCEMENT HISTORY",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w")

        past_row = ctk.CTkFrame(tab, fg_color="transparent")
        past_row.pack(fill="x", padx=16, pady=(0, 16))

        self.past_menu = ctk.CTkOptionMenu(
            past_row,
            width=350,
            height=36,
            corner_radius=8,
            dynamic_resizing=False,
            fg_color=Colors.BG_CARD,
            button_color=Colors.BORDER,
            button_hover_color=Colors.TEXT_MUTED,
        )
        self.past_menu.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            past_row,
            text="  Retract  ",
            command=self._do_retract,
            width=120,
            height=36,
            corner_radius=8,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
        ).pack(side="left")

    def _refresh_status(self):
        config = load_config()
        data = load_data()

        for w in self.status_frame.winfo_children():
            w.destroy()

        if not data["announcements"]:
            self.status_header.configure(text="NO ANNOUNCEMENTS YET")
            empty_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
            empty_frame.pack(fill="both", expand=True)
            ctk.CTkLabel(
                empty_frame,
                text="No announcements have been sent yet.",
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_MUTED,
            ).pack(pady=40)
            self.past_menu.configure(values=["(no announcements)"])
            self.past_menu.set("(no announcements)")
            return

        latest = data["announcements"][-1]
        self.status_header.configure(text=f"ANNOUNCEMENT #{latest['id']}")
        completed = set(latest.get("completed_by", []))

        # Announcement text preview
        text_preview = ctk.CTkFrame(
            self.status_frame,
            corner_radius=8,
            fg_color=Colors.BG_CARD_HOVER,
        )
        text_preview.pack(fill="x", padx=8, pady=(8, 12))

        ctk.CTkLabel(
            text_preview,
            text=latest["text"][:200] + ("..." if len(latest["text"]) > 200 else ""),
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_PRIMARY,
            wraplength=700,
            justify="left",
        ).pack(padx=12, pady=10, anchor="w")

        # Member status list
        for m in config["members"]:
            is_done = m["user_id"] in completed
            row = ctk.CTkFrame(
                self.status_frame,
                corner_radius=6,
                fg_color=Colors.BG_CARD_HOVER if is_done else "transparent",
            )
            row.pack(fill="x", padx=8, pady=1)

            icon = "✓" if is_done else "○"
            icon_color = Colors.SUCCESS if is_done else Colors.TEXT_MUTED

            ctk.CTkLabel(
                row,
                text=icon,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=icon_color,
                width=24,
            ).pack(side="left", padx=(10, 4), pady=4)

            ctk.CTkLabel(
                row,
                text=m["name"],
                anchor="w",
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_PRIMARY if is_done else Colors.TEXT_SECONDARY,
            ).pack(side="left", padx=(0, 8), pady=4)

        # Summary
        done = len(completed)
        total = len(config["members"])
        summary_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        summary_frame.pack(fill="x", padx=8, pady=(12, 8))

        ctk.CTkLabel(
            summary_frame,
            text=f"{done}/{total} completed",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w", padx=4)

        # Progress bar
        progress = ctk.CTkProgressBar(
            summary_frame,
            width=400,
            height=8,
            corner_radius=4,
            fg_color=Colors.BORDER,
            progress_color=Colors.TEAL,
        )
        progress.pack(anchor="w", padx=4, pady=(6, 0))
        progress.set(done / total if total > 0 else 0)

        # Past announcements menu
        choices = [
            f"#{a['id']} — {a['text'][:60].strip()}..." for a in data["announcements"]
        ]
        self.past_menu.configure(values=choices)
        self.past_menu.set(choices[-1])

    def _do_retract(self):
        selection = self.past_menu.get()
        if not selection or selection.startswith("(no"):
            return
        ann_id = int(selection.split("—")[0].strip().lstrip("#"))
        self._run_retract(ann_id)

    def _run_retract(self, ann_id):
        threading.Thread(
            target=self._retract_worker, args=(ann_id,), daemon=True
        ).start()

    def _retract_worker(self, ann_id):
        data = load_data()
        target = next((a for a in data["announcements"] if a["id"] == ann_id), None)
        if not target or not target.get("sent_messages"):
            self.after(
                0,
                lambda: self._status_bar_msg(
                    f"Announcement #{ann_id} has no retractable messages.",
                    Colors.WARNING,
                ),
            )
            return

        loop = asyncio.new_event_loop()
        client = get_matrix_client()

        async def _do():
            if not await matrix_login(client):
                self.after(
                    0,
                    lambda: self._status_bar_msg("Matrix login failed.", Colors.DANGER),
                )
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
            self.after(
                0,
                lambda: self._status_bar_msg(
                    result, Colors.SUCCESS if deleted else Colors.WARNING
                ),
            )
            await client.close()

        loop.run_until_complete(_do())
        loop.close()

    # ================================
    #  TAB 3 - Members
    # ================================

    def _build_members_tab(self):
        tab = self.tab.add("  Members  ")

        # -- Section: Add member --
        add_header = ctk.CTkFrame(tab, fg_color="transparent")
        add_header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            add_header,
            text="ADD MEMBER",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w")

        add_row = ctk.CTkFrame(
            tab,
            corner_radius=10,
            fg_color=Colors.BG_CARD,
        )
        add_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            add_row,
            text="User ID",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self.add_id_entry = ctk.CTkEntry(
            add_row,
            width=280,
            height=36,
            corner_radius=8,
            placeholder_text="@user:matrix.org",
            placeholder_text_color=Colors.TEXT_MUTED,
        )
        self.add_id_entry.pack(side="left", padx=(12, 16), pady=(0, 10))

        ctk.CTkLabel(
            add_row,
            text="Display Name",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=12, pady=(8, 2))

        self.add_name_entry = ctk.CTkEntry(
            add_row,
            width=220,
            height=36,
            corner_radius=8,
            placeholder_text="Full name",
            placeholder_text_color=Colors.TEXT_MUTED,
        )
        self.add_name_entry.pack(side="left", padx=(0, 16), pady=(0, 10))

        ctk.CTkButton(
            add_row,
            text="  Add Member  ",
            command=self._do_add_member,
            width=120,
            height=36,
            corner_radius=8,
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
        ).pack(side="left", padx=(0, 12), pady=(0, 10))

        # -- Section: Member list --
        list_header = ctk.CTkFrame(tab, fg_color="transparent")
        list_header.pack(fill="x", padx=16, pady=(0, 6))

        self.member_list_label = ctk.CTkLabel(
            list_header,
            text="TEAM MEMBERS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        )
        self.member_list_label.pack(side="left")

        ctk.CTkButton(
            list_header,
            text="Refresh",
            command=self._refresh_members,
            width=80,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BG_CARD_HOVER,
        ).pack(side="right")

        self.member_frame = ctk.CTkScrollableFrame(
            tab,
            height=300,
            corner_radius=10,
            fg_color=Colors.BG_CARD,
        )
        self.member_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _refresh_members(self):
        config = load_config()
        for w in self.member_frame.winfo_children():
            w.destroy()

        self.member_list_label.configure(
            text=f"TEAM MEMBERS ({len(config['members'])})"
        )

        for i, m in enumerate(config["members"]):
            row = ctk.CTkFrame(
                self.member_frame,
                corner_radius=8,
                fg_color=Colors.BG_CARD_HOVER if i % 2 == 0 else "transparent",
            )
            row.pack(fill="x", padx=6, pady=2)

            # Avatar placeholder
            avatar = ctk.CTkFrame(
                row,
                width=32,
                height=32,
                corner_radius=16,
                fg_color=Colors.TEAL_DARK,
            )
            avatar.pack(side="left", padx=(10, 10), pady=6)
            avatar.pack_propagate(False)

            ctk.CTkLabel(
                avatar,
                text=m["name"][0].upper(),
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=Colors.TEXT_PRIMARY,
            ).pack(expand=True)

            # Name and ID
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="y", pady=6)

            ctk.CTkLabel(
                info_frame,
                text=m["name"],
                anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=Colors.TEXT_PRIMARY,
            ).pack(anchor="w")

            ctk.CTkLabel(
                info_frame,
                text=m["user_id"],
                anchor="w",
                font=ctk.CTkFont(size=10, family="Courier"),
                text_color=Colors.TEXT_MUTED,
            ).pack(anchor="w")

            # Remove button
            ctk.CTkButton(
                row,
                text="Remove",
                width=70,
                height=26,
                corner_radius=6,
                font=ctk.CTkFont(size=10),
                fg_color="transparent",
                border_width=1,
                border_color=Colors.DANGER,
                text_color=Colors.DANGER,
                hover_color=Colors.DANGER_HOVER,
                command=lambda uid=m["user_id"]: self._remove_member(uid),
            ).pack(side="right", padx=10, pady=6)

    def _do_add_member(self):
        uid = self.add_id_entry.get().strip()
        name = self.add_name_entry.get().strip()
        if not uid or not name:
            self._status_bar_msg("Enter both User ID and Name.", Colors.WARNING)
            return

        config = load_config()
        if get_member_name(config, uid) != uid:
            self._status_bar_msg(f"{name} is already a member.", Colors.WARNING)
            return
        config["members"].append({"user_id": uid, "name": name})
        save_config(config)
        self.add_id_entry.delete(0, "end")
        self.add_name_entry.delete(0, "end")
        self._refresh_members()
        self._refresh_test_checkboxes()
        self._status_bar_msg(f"Added {name} ({uid})", Colors.SUCCESS)

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
        tab = self.tab.add("  Test Users  ")

        # -- Add test user --
        add_header = ctk.CTkFrame(tab, fg_color="transparent")
        add_header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            add_header,
            text="ADD TEST RECIPIENT",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w")

        add_row = ctk.CTkFrame(
            tab,
            corner_radius=10,
            fg_color=Colors.BG_CARD,
        )
        add_row.pack(fill="x", padx=16, pady=(0, 12))

        self.test_id_entry = ctk.CTkEntry(
            add_row,
            width=300,
            height=36,
            corner_radius=8,
            placeholder_text="@user:matrix.org",
            placeholder_text_color=Colors.TEXT_MUTED,
        )
        self.test_id_entry.pack(side="left", padx=12, pady=10)

        ctk.CTkButton(
            add_row,
            text="  Add  ",
            command=self._do_add_test_id,
            width=90,
            height=36,
            corner_radius=8,
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
        ).pack(side="left", padx=(0, 12), pady=10)

        # -- Test user list --
        list_header = ctk.CTkFrame(tab, fg_color="transparent")
        list_header.pack(fill="x", padx=16, pady=(0, 6))

        self.test_list_label = ctk.CTkLabel(
            list_header,
            text="TEST RECIPIENTS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        )
        self.test_list_label.pack(side="left")

        ctk.CTkButton(
            list_header,
            text="Refresh",
            command=self._refresh_test,
            width=80,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BG_CARD_HOVER,
        ).pack(side="right")

        self.test_frame = ctk.CTkScrollableFrame(
            tab,
            height=220,
            corner_radius=10,
            fg_color=Colors.BG_CARD,
        )
        self.test_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        ctk.CTkLabel(
            tab,
            text="Test users receive announcements when using 'Send to Selected'.",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 4))

        # -- Actions --
        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            btn_row,
            text="  Clear All  ",
            command=self._do_clear_test_ids,
            width=100,
            height=32,
            corner_radius=8,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
        ).pack(side="left")

    def _refresh_test(self):
        config = load_config()
        test_ids = config.get("test_user_ids", [])

        for w in self.test_frame.winfo_children():
            w.destroy()

        self.test_list_label.configure(text=f"TEST RECIPIENTS ({len(test_ids)})")

        if not test_ids:
            ctk.CTkLabel(
                self.test_frame,
                text="No test recipients configured.",
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED,
            ).pack(pady=20)
            return

        for uid in test_ids:
            name = get_member_name(config, uid)
            is_registered = name != uid

            row = ctk.CTkFrame(
                self.test_frame,
                corner_radius=6,
                fg_color=Colors.BG_CARD_HOVER,
            )
            row.pack(fill="x", padx=6, pady=2)

            icon = "✓" if is_registered else "?"
            icon_color = Colors.SUCCESS if is_registered else Colors.WARNING

            ctk.CTkLabel(
                row,
                text=icon,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=icon_color,
                width=24,
            ).pack(side="left", padx=(10, 4), pady=6)

            display = f"{name} — {uid}" if is_registered else f"{uid} (not in members)"
            ctk.CTkLabel(
                row,
                text=display,
                anchor="w",
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_PRIMARY if is_registered else Colors.TEXT_MUTED,
            ).pack(side="left", padx=(0, 8), pady=6)

            ctk.CTkButton(
                row,
                text="Remove",
                width=60,
                height=24,
                corner_radius=6,
                font=ctk.CTkFont(size=10),
                fg_color="transparent",
                border_width=1,
                border_color=Colors.DANGER,
                text_color=Colors.DANGER,
                hover_color=Colors.DANGER_HOVER,
                command=lambda u=uid: self._remove_test_id(u),
            ).pack(side="right", padx=8, pady=6)

    def _do_add_test_id(self):
        uid = self.test_id_entry.get().strip()
        if not uid:
            return

        config = load_config()
        current = config.get("test_user_ids", [])
        if uid in current:
            self._status_bar_msg(f"{uid} is already a test user.", Colors.WARNING)
            return
        current.append(uid)
        config["test_user_ids"] = current
        save_config(config)
        self.test_id_entry.delete(0, "end")
        self._refresh_test()
        self._status_bar_msg(f"Added test user {uid}", Colors.SUCCESS)

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
        self._status_bar_msg("Test user IDs cleared.", Colors.SUCCESS)

    # ================================
    #  TAB 5 - Settings
    # ================================

    def _build_settings_tab(self):
        tab = self.tab.add("  Settings  ")

        # -- Configuration section --
        config_header = ctk.CTkFrame(tab, fg_color="transparent")
        config_header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            config_header,
            text="BOT CONFIGURATION",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w")

        config_card = ctk.CTkFrame(
            tab,
            corner_radius=10,
            fg_color=Colors.BG_CARD,
        )
        config_card.pack(fill="x", padx=16, pady=(0, 16))

        self._settings_row(config_card, "Homeserver:", HOMESERVER or "Not set")
        self._settings_row(config_card, "User ID:", USER_ID or "Not set")
        self._settings_row(config_card, "Room ID:", ROOM_ID or "Not set (DM mode)")
        self._settings_row(config_card, "Admin:", ADMIN_ID or "Not set")

        status = "Connected" if self.matrix_ready else "Not configured"
        status_color = Colors.SUCCESS if self.matrix_ready else Colors.DANGER
        self._settings_row(config_card, "Status:", status, status_color)

        # -- Data files section --
        data_header = ctk.CTkFrame(tab, fg_color="transparent")
        data_header.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            data_header,
            text="DATA FILES",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w")

        data_card = ctk.CTkFrame(
            tab,
            corner_radius=10,
            fg_color=Colors.BG_CARD,
        )
        data_card.pack(fill="x", padx=16, pady=(0, 16))

        self._settings_row(data_card, "Config:", str(CONFIG_FILE))
        self._settings_row(data_card, "Data:", str(DATA_FILE))
        self._settings_row(data_card, ".env:", str(BASE_DIR / ".env"))

        # -- Info section --
        info_card = ctk.CTkFrame(
            tab,
            corner_radius=10,
            fg_color=Colors.BG_CARD,
        )
        info_card.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkLabel(
            info_card,
            text="This admin GUI shares config.json and data.json with bot.py. "
            "Changes made here are immediately visible to the bot and vice versa.\n\n"
            "Members confirm engagement by reacting with ✅ to announcements.",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_SECONDARY,
            justify="left",
            wraplength=700,
        ).pack(anchor="w", padx=16, pady=12)

    @staticmethod
    def _settings_row(parent, label, value, value_color=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            row,
            text=label,
            width=120,
            anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEXT_MUTED,
        ).pack(side="left")

        lbl = ctk.CTkLabel(
            row,
            text=value,
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=value_color or Colors.TEXT_PRIMARY,
        )
        lbl.pack(side="left", padx=(8, 0))

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
