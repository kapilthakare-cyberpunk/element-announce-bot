"""
Admin GUI for Element Announce Bot — Professional Design.

A CustomTkinter desktop application with clean typography and clear hierarchy.
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
    TEMPLATES_FILE,
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
    load_templates,
    save_templates,
    get_member_name,
    get_or_create_dm_room,
)

# ---------------------------------------------------------------------------
# Visual System
# ---------------------------------------------------------------------------

THEME_PATH = Path(__file__).parent / "theme.json"
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme(str(THEME_PATH))


class Colors:
    TEAL = "#14B8A6"
    TEAL_DARK = "#0D9488"
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    DANGER = "#EF4444"
    DANGER_HOVER = "#DC2626"
    INFO = "#3B82F6"
    BG_DARK = "#0F1117"
    BG_CARD = "#1A1D23"
    BG_CARD_HOVER = "#22262E"
    BORDER = "#2D3139"
    TEXT_PRIMARY = "#F9FAFB"
    TEXT_SECONDARY = "#D1D5DB"
    TEXT_MUTED = "#9CA3AF"


DEVICE_NAME = "element-announce-bot-gui"


# ---------------------------------------------------------------------------
# Matrix helpers
# ---------------------------------------------------------------------------


def get_matrix_client():
    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        store_sync_tokens=True,
        encryption_enabled=False,
    )
    return AsyncClient(HOMESERVER, USER_ID, store_path=STORE_PATH, config=client_config)


async def matrix_login(client):
    """Login with saved credentials, access token, or password."""
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
            json.dumps(
                {
                    "user_id": USER_ID,
                    "access_token": ACCESS_TOKEN,
                    "device_id": "web",
                }
            )
        )
        return True

    if PASSWORD:
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

    return False


async def matrix_sync_and_send(client, room_id, text):
    """Sync rooms then send a message (no URL previews)."""
    content = {
        "msgtype": "m.text",
        "body": text,
        "fi.mau.dont_render": True,
    }
    return await client.room_send(
        room_id, "m.room.message", content, ignore_unverified_devices=True
    )


async def matrix_redact(client, room_id, event_id, reason="Retracted by admin"):
    return await client.room_redact(
        room_id, event_id, reason, ignore_unverified_devices=True
    )


# ===================================================================
# GUI Application
# ===================================================================


class AdminApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Element Announce Bot")
        self.geometry("1100x780")
        self.minsize(900, 650)
        self.matrix_ready = bool(USER_ID and (PASSWORD or ACCESS_TOKEN))
        self._build_ui()
        self._refresh_all()

    def _build_ui(self):
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_header()

        self.tab = ctk.CTkTabview(
            self.main,
            corner_radius=12,
            segmented_button_fg_color=Colors.BG_CARD,
            segmented_button_selected_color=Colors.TEAL,
            segmented_button_selected_hover_color=Colors.TEAL_DARK,
            segmented_button_unselected_color=Colors.BG_CARD,
            segmented_button_unselected_hover_color=Colors.BG_CARD_HOVER,
        )
        self.tab.pack(fill="both", expand=True, pady=(16, 0))

        self._build_footer()
        self._build_announce_tab()
        self._build_status_tab()
        self._build_members_tab()
        self._build_test_tab()
        self._build_settings_tab()

    def _build_header(self):
        h = ctk.CTkFrame(self.main, fg_color="transparent", height=56)
        h.pack(fill="x", pady=(0, 4))
        h.pack_propagate(False)

        left = ctk.CTkFrame(h, fg_color="transparent")
        left.pack(side="left", fill="y")

        ctk.CTkLabel(
            left, text="⚡", font=ctk.CTkFont(size=26), text_color=Colors.TEAL
        ).pack(side="left", padx=(0, 10))

        title_f = ctk.CTkFrame(left, fg_color="transparent")
        title_f.pack(side="left", fill="y")
        ctk.CTkLabel(
            title_f,
            text="Element Announce Bot",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_f,
            text="Team broadcast & engagement tracking",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w")

        right = ctk.CTkFrame(h, fg_color="transparent")
        right.pack(side="right", fill="y")

        dot = Colors.SUCCESS if self.matrix_ready else Colors.DANGER
        txt = "Connected" if self.matrix_ready else "Not Connected"
        sub = f"Admin: {ADMIN_ID.split(':')[0][1:]}" if ADMIN_ID else ""

        ctk.CTkLabel(right, text="●", font=ctk.CTkFont(size=10), text_color=dot).pack(
            side="left", padx=(0, 6)
        )
        info = ctk.CTkFrame(right, fg_color="transparent")
        info.pack(side="left", fill="y")
        ctk.CTkLabel(info, text=txt, font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="e"
        )
        ctk.CTkLabel(
            info, text=sub, font=ctk.CTkFont(size=10), text_color=Colors.TEXT_MUTED
        ).pack(anchor="e")

    def _build_footer(self):
        self.footer = ctk.CTkFrame(
            self.main, corner_radius=8, height=36, fg_color=Colors.BG_CARD
        )
        self.footer.pack(fill="x", pady=(8, 0))
        self.footer.pack_propagate(False)
        self.footer_icon = ctk.CTkLabel(
            self.footer,
            text="ℹ",
            font=ctk.CTkFont(size=12),
            text_color=Colors.INFO,
            width=24,
        )
        self.footer_icon.pack(side="left", padx=(12, 0))
        self.footer_label = ctk.CTkLabel(
            self.footer,
            text="Ready",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_SECONDARY,
        )
        self.footer_label.pack(side="left", padx=(4, 12), fill="y")

    # ---- helpers ----

    def _msg(self, text, color=None):
        self.footer_label.configure(
            text=text, text_color=color or Colors.TEXT_SECONDARY
        )
        icons = {
            Colors.SUCCESS: "✓",
            Colors.WARNING: "⚠",
            Colors.DANGER: "✗",
            Colors.INFO: "ℹ",
        }
        self.footer_icon.configure(
            text=icons.get(color, "ℹ"), text_color=color or Colors.INFO
        )

    def _section(self, parent, title):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            f,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w")
        return f

    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, corner_radius=10, fg_color=Colors.BG_CARD, **kw)

    # ================================
    #  TAB 1 — Announce
    # ================================

    def _build_announce_tab(self):
        tab = self.tab.add("  Announce  ")
        
        # Two-column layout container
        main_container = ctk.CTkFrame(tab, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=16, pady=12)

        left_col = ctk.CTkFrame(main_container, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 16))

        right_col = ctk.CTkFrame(main_container, width=280, fg_color="transparent")
        right_col.pack(side="right", fill="both")

        # --- LEFT COLUMN: COMPOSE & TEMPLATES & LOG ---
        self._section(left_col, "COMPOSE ANNOUNCEMENT")
        ctk.CTkLabel(
            left_col,
            text="Write your message. It will be sent as a DM to each team member.",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=0, pady=(0, 8))

        editor = self._card(left_col)
        editor.pack(fill="both", expand=True, padx=0, pady=(0, 12))
        self.announce_text = ctk.CTkTextbox(
            editor,
            height=200,
            wrap="word",
            corner_radius=10,
            fg_color=Colors.BG_CARD,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
        )
        self.announce_text.pack(fill="both", expand=True, padx=2, pady=2)

        btns = ctk.CTkFrame(left_col, fg_color="transparent")
        btns.pack(fill="x", padx=0, pady=(0, 12))

        self.send_all_btn = ctk.CTkButton(
            btns,
            text="Send to All Members",
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
            command=self._do_send_all,
        )
        self.send_all_btn.pack(side="left", padx=(0, 10))

        self.send_test_btn = ctk.CTkButton(
            btns,
            text="Send to Selected",
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=2,
            border_color=Colors.TEAL,
            text_color=Colors.TEAL,
            hover_color=Colors.BG_CARD_HOVER,
            command=self._do_send_test,
        )
        self.send_test_btn.pack(side="left")

        self._section(left_col, "TEMPLATES")
        tpl_row = ctk.CTkFrame(left_col, fg_color="transparent")
        tpl_row.pack(fill="x", padx=0, pady=(0, 8))

        self.tpl_menu = ctk.CTkOptionMenu(
            tpl_row,
            width=260,
            height=34,
            corner_radius=8,
            fg_color=Colors.BG_CARD,
            button_color=Colors.BORDER,
            button_hover_color=Colors.TEXT_MUTED,
        )
        self.tpl_menu.pack(side="left", padx=(0, 8))
        self._refresh_tpl_menu()

        ctk.CTkButton(
            tpl_row,
            text="Load",
            width=60,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            border_width=2,
            border_color=Colors.TEAL,
            text_color=Colors.TEAL,
            hover_color=Colors.BG_CARD_HOVER,
            command=self._load_template,
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            tpl_row,
            text="Save",
            width=60,
            height=34,
            corner_radius=8,
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
            command=self._save_template,
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            tpl_row,
            text="Delete",
            width=60,
            height=34,
            corner_radius=8,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            command=self._delete_template,
        ).pack(side="left")

        self._section(left_col, "ACTIVITY LOG")
        self.send_log = ctk.CTkScrollableFrame(
            left_col, height=180, corner_radius=8, fg_color=Colors.BG_CARD
        )
        self.send_log.pack(fill="x", padx=0, pady=(0, 0))

        # --- RIGHT COLUMN: SELECT RECIPIENTS ---
        self._section(right_col, "SELECT RECIPIENTS")
        recipients_card = self._card(right_col)
        recipients_card.pack(fill="both", expand=True, pady=(0, 0))

        self.test_check_frame = ctk.CTkScrollableFrame(
            recipients_card, corner_radius=8, fg_color="transparent"
        )
        self.test_check_frame.pack(fill="both", expand=True, padx=2, pady=2)
        self.test_checkvars = {}
        self._refresh_test_checkboxes()

    def _do_send_all(self):
        text = self.announce_text.get("1.0", "end-1c").strip()
        if not text:
            self._log("Cannot send — message is empty.", Colors.WARNING)
            return
        n = len(load_config().get("members", []))
        self._preview(text, n, "Send to All Members", lambda: self._run_send_all(text))

    def _run_send_all(self, text):
        self.send_all_btn.configure(state="disabled")
        self.send_test_btn.configure(state="disabled")
        self._clear_log()
        threading.Thread(
            target=self._worker_send_all, args=(text,), daemon=True
        ).start()

    def _worker_send_all(self, text):
        members = load_config().get("members", [])
        if not members:
            self.after(0, lambda: self._log("No members in config.", Colors.WARNING))
            self.after(0, lambda: self.send_all_btn.configure(state="normal"))
            self.after(0, lambda: self.send_test_btn.configure(state="normal"))
            return

        loop = asyncio.new_event_loop()
        client = get_matrix_client()

        async def run():
            if not await matrix_login(client):
                self.after(
                    0, lambda: self._log("Login failed. Check .env.", Colors.DANGER)
                )
                return
            await client.sync(timeout=5000, full_state=True)

            data = load_data()
            ann_id = len(data["announcements"]) + 1
            sent = []

            for m in members:
                try:
                    room = await get_or_create_dm_room(client, m["user_id"])
                    if not room:
                        self.after(
                            0,
                            lambda n=m["name"]: self._log(
                                f"✗ No DM room: {n}", Colors.WARNING
                            ),
                        )
                        continue

                    # SAFETY: Verify room is a true DM (exactly 2 members, no name)
                    room_obj = client.rooms.get(room)
                    if room_obj:
                        member_count = len(room_obj.users)
                        room_name = getattr(room_obj, "name", None)
                        if member_count != 2 or (room_name and room_name.strip()):
                            self.after(
                                0,
                                lambda n=m["name"], rn=room_name or "unnamed", mc=member_count: (
                                    self._log(
                                        f"✗ SKIPPED group room for {n}: '{rn}' ({mc} members)",
                                        Colors.DANGER,
                                    )
                                ),
                            )
                            continue

                    first_name = m["name"].split()[0]
                    if "abhijit" in m["name"].lower():
                        personal_name = "Abhijit Sir"
                    else:
                        personal_name = first_name
                    personal_text = text.replace("<Name>", personal_name)
                    resp = await matrix_sync_and_send(client, room, personal_text)
                    if hasattr(resp, "event_id"):
                        sent.append(
                            {
                                "user_id": m["user_id"],
                                "name": m["name"],
                                "event_id": resp.event_id,
                            }
                        )
                        self.after(
                            0,
                            lambda n=m["name"]: self._log(
                                f"✓ Sent to {n}", Colors.SUCCESS
                            ),
                        )
                except Exception as e:
                    self.after(
                        0,
                        lambda n=m["name"], err=e: self._log(
                            f"✗ Failed: {n} — {err}", Colors.DANGER
                        ),
                    )

            if sent:
                data["announcements"].append(
                    {
                        "id": ann_id,
                        "text": text,
                        "completed_by": [],
                        "sent_messages": sent,
                    }
                )
                save_data(data)
                self.after(
                    0,
                    lambda: self._log(
                        f"Announcement #{ann_id} → {len(sent)}/{len(members)} members",
                        Colors.SUCCESS,
                    ),
                )
            else:
                self.after(0, lambda: self._log("Failed to send.", Colors.DANGER))
            await client.close()

        try:
            loop.run_until_complete(run())
        finally:
            try:
                loop.close()
            except Exception:
                pass
            self.after(0, lambda: self.send_all_btn.configure(state="normal"))
            self.after(0, lambda: self.send_test_btn.configure(state="normal"))

    def _do_send_test(self):
        text = self.announce_text.get("1.0", "end-1c").strip()
        if not text:
            self._log("Cannot send — message is empty.", Colors.WARNING)
            return
        ids = [u for u, v in self.test_checkvars.items() if v.get()]
        if not ids:
            self._log("No recipients selected.", Colors.WARNING)
            return
        cfg = load_config()
        names = [m["name"] for m in cfg["members"] if m["user_id"] in ids]
        self._preview(
            text,
            len(names),
            f"Send to {len(names)} Selected",
            lambda: self._run_send_test(text, ids),
        )

    def _run_send_test(self, text, ids):
        self.send_all_btn.configure(state="disabled")
        self.send_test_btn.configure(state="disabled")
        self._clear_log()
        threading.Thread(
            target=self._worker_send_test, args=(text, ids), daemon=True
        ).start()

    def _worker_send_test(self, text, ids):
        members = [m for m in load_config().get("members", []) if m["user_id"] in ids]
        if not members:
            self.after(0, lambda: self._log("No matching members.", Colors.WARNING))
            self.after(0, lambda: self.send_all_btn.configure(state="normal"))
            self.after(0, lambda: self.send_test_btn.configure(state="normal"))
            return

        loop = asyncio.new_event_loop()
        client = get_matrix_client()

        async def run():
            if not await matrix_login(client):
                self.after(0, lambda: self._log("Login failed.", Colors.DANGER))
                return
            await client.sync(timeout=5000, full_state=True)

            ok = 0
            for m in members:
                try:
                    room = await get_or_create_dm_room(client, m["user_id"])
                    if not room:
                        self.after(
                            0,
                            lambda n=m["name"]: self._log(
                                f"✗ No DM room: {n}", Colors.WARNING
                            ),
                        )
                        continue

                    # SAFETY: Verify room is a true DM (exactly 2 members, no name)
                    room_obj = client.rooms.get(room)
                    if room_obj:
                        member_count = len(room_obj.users)
                        room_name = getattr(room_obj, "name", None)
                        if member_count != 2 or (room_name and room_name.strip()):
                            self.after(
                                0,
                                lambda n=m["name"], rn=room_name or "unnamed", mc=member_count: (
                                    self._log(
                                        f"✗ SKIPPED group room for {n}: '{rn}' ({mc} members)",
                                        Colors.DANGER,
                                    )
                                ),
                            )
                            continue

                    first_name = m["name"].split()[0]
                    if "abhijit" in m["name"].lower():
                        personal_name = "Abhijit Sir"
                    else:
                        personal_name = first_name
                    personal_text = text.replace("<Name>", personal_name)
                    resp = await matrix_sync_and_send(client, room, personal_text)
                    if hasattr(resp, "event_id"):
                        ok += 1
                        self.after(
                            0,
                            lambda n=m["name"]: self._log(
                                f"✓ Sent to {n}", Colors.SUCCESS
                            ),
                        )
                except Exception as e:
                    self.after(
                        0,
                        lambda n=m["name"], err=e: self._log(
                            f"✗ Failed: {n} — {err}", Colors.DANGER
                        ),
                    )

            self.after(
                0,
                lambda: self._log(
                    f"Test sent to {ok}/{len(members)} members", Colors.SUCCESS
                ),
            )
            await client.close()

        try:
            loop.run_until_complete(run())
        finally:
            try:
                loop.close()
            except Exception:
                pass
            self.after(0, lambda: self.send_all_btn.configure(state="normal"))
            self.after(0, lambda: self.send_test_btn.configure(state="normal"))

    # ---- template helpers ----

    def _refresh_tpl_menu(self):
        templates = load_templates().get("templates", [])
        names = [t["name"] for t in templates] or ["(no templates)"]
        self.tpl_menu.configure(values=names)
        self.tpl_menu.set(names[0])

    def _load_template(self):
        name = self.tpl_menu.get()
        if name.startswith("("):
            return
        templates = load_templates().get("templates", [])
        tpl = next((t for t in templates if t["name"] == name), None)
        if tpl:
            self.announce_text.delete("1.0", "end")
            self.announce_text.insert("1.0", tpl["text"])
            self._msg(f"Loaded template: {name}", Colors.SUCCESS)

    def _save_template(self):
        text = self.announce_text.get("1.0", "end-1c").strip()
        if not text:
            self._msg("Cannot save — message is empty.", Colors.WARNING)
            return
        win = ctk.CTkToplevel(self)
        win.title("Save Template")
        win.geometry("400x150")
        win.transient(self)
        win.grab_set()
        win.configure(fg_color=Colors.BG_DARK)

        ctk.CTkLabel(
            win,
            text="Template name:",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=20, pady=(20, 4))

        entry = ctk.CTkEntry(
            win,
            width=360,
            height=34,
            corner_radius=8,
            placeholder_text="e.g. Social Media Engagement",
        )
        entry.pack(padx=20, pady=(0, 16))

        def confirm():
            name = entry.get().strip()
            if not name:
                return
            data = load_templates()
            data["templates"] = [t for t in data["templates"] if t["name"] != name]
            data["templates"].append({"name": name, "text": text})
            save_templates(data)
            self._refresh_tpl_menu()
            self.tpl_menu.set(name)
            self._msg(f"Saved template: {name}", Colors.SUCCESS)
            win.destroy()

        ctk.CTkButton(
            win,
            text="Save",
            width=100,
            height=34,
            corner_radius=8,
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
            command=confirm,
        ).pack()

    def _delete_template(self):
        name = self.tpl_menu.get()
        if name.startswith("("):
            return
        data = load_templates()
        data["templates"] = [t for t in data["templates"] if t["name"] != name]
        save_templates(data)
        self._refresh_tpl_menu()
        self._msg(f"Deleted template: {name}", Colors.SUCCESS)

    def _refresh_test_checkboxes(self):
        for w in self.test_check_frame.winfo_children():
            w.destroy()
        self.test_checkvars.clear()

        self.select_all_var = ctk.BooleanVar(value=False)
        def on_select_all():
            val = self.select_all_var.get()
            for var in self.test_checkvars.values():
                var.set(val)

        ctk.CTkCheckBox(
            self.test_check_frame,
            text="Select All",
            variable=self.select_all_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Colors.TEAL,
            command=on_select_all
        ).pack(anchor="w", padx=8, pady=(2, 10))

        for m in load_config().get("members", []):
            var = ctk.BooleanVar(value=False)
            self.test_checkvars[m["user_id"]] = var
            ctk.CTkCheckBox(
                self.test_check_frame,
                text=m["name"],
                variable=var,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_PRIMARY,
            ).pack(anchor="w", padx=8, pady=2)

    def _clear_log(self):
        for w in self.send_log.winfo_children():
            w.destroy()

    def _log(self, text, color=None):
        ctk.CTkLabel(
            self.send_log,
            text=text,
            anchor="w",
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color=color or Colors.TEXT_SECONDARY,
        ).pack(fill="x", padx=8, pady=2)

    def _preview(self, text, count, btn_label, on_confirm):
        win = ctk.CTkToplevel(self)
        win.title("Preview")
        win.geometry("540x550")
        win.transient(self)
        win.grab_set()
        win.configure(fg_color=Colors.BG_DARK)

        self._section(win, "MESSAGE PREVIEW")
        ctk.CTkLabel(
            win,
            text=f"Will be sent to {count} member(s) via DM",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        box = self._card(win)
        box.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        tb = ctk.CTkTextbox(
            box,
            wrap="word",
            fg_color=Colors.BG_CARD,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
        )
        tb.pack(fill="both", expand=True, padx=2, pady=2)
        tb.insert("1.0", text)
        tb.configure(state="disabled")

        # Mandatory review checkbox
        confirm_btn = None
        checkbox_var = ctk.BooleanVar(value=False)
        
        def toggle_confirm_btn():
            if checkbox_var.get():
                confirm_btn.configure(state="normal")
            else:
                confirm_btn.configure(state="disabled")

        checkbox = ctk.CTkCheckBox(
            win, 
            text="I have reviewed this announcement and verify it is correct.", 
            variable=checkbox_var,
            command=toggle_confirm_btn,
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK
        )
        checkbox.pack(anchor="w", padx=16, pady=(0, 16))

        bf = ctk.CTkFrame(win, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            bf,
            text="Cancel",
            width=110,
            height=36,
            fg_color="transparent",
            border_width=2,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BG_CARD_HOVER,
            command=win.destroy,
        ).pack(side="left")
        confirm_btn = ctk.CTkButton(
            bf,
            text=btn_label,
            width=200,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
            state="disabled",
            command=lambda: (win.destroy(), on_confirm()),
        )
        confirm_btn.pack(side="right")

    # ================================
    #  TAB 2 — Status
    # ================================

    def _build_status_tab(self):
        tab = self.tab.add("  Status  ")

        self.status_hdr = self._section(tab, "LATEST ANNOUNCEMENT")

        self.status_frame = ctk.CTkScrollableFrame(
            tab, height=260, corner_radius=10, fg_color=Colors.BG_CARD
        )
        self.status_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        ctk.CTkButton(
            tab,
            text="Refresh",
            width=110,
            height=34,
            corner_radius=8,
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
            command=self._refresh_status,
        ).pack(anchor="w", padx=16, pady=(0, 12))

        self._section(tab, "ANNOUNCEMENT HISTORY")
        pr = ctk.CTkFrame(tab, fg_color="transparent")
        pr.pack(fill="x", padx=16, pady=(0, 16))
        self.past_menu = ctk.CTkOptionMenu(
            pr,
            width=340,
            height=34,
            corner_radius=8,
            dynamic_resizing=False,
            fg_color=Colors.BG_CARD,
            button_color=Colors.BORDER,
            button_hover_color=Colors.TEXT_MUTED,
        )
        self.past_menu.pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            pr,
            text="Retract",
            width=100,
            height=34,
            corner_radius=8,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            command=self._do_retract,
        ).pack(side="left")

    def _refresh_status(self):
        config = load_config()
        data = load_data()
        for w in self.status_frame.winfo_children():
            w.destroy()

        if not data["announcements"]:
            self.status_hdr.winfo_children()[0].configure(text="NO ANNOUNCEMENTS YET")
            ctk.CTkLabel(
                self.status_frame,
                text="No announcements sent yet.",
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_MUTED,
            ).pack(pady=40)
            self.past_menu.configure(values=["(none)"])
            self.past_menu.set("(none)")
            return

        latest = data["announcements"][-1]
        self.status_hdr.winfo_children()[0].configure(
            text=f"ANNOUNCEMENT #{latest['id']}"
        )
        completed = set(latest.get("completed_by", []))

        prev = ctk.CTkFrame(
            self.status_frame, corner_radius=8, fg_color=Colors.BG_CARD_HOVER
        )
        prev.pack(fill="x", padx=8, pady=(8, 12))
        ctk.CTkLabel(
            prev,
            text=latest["text"][:200] + ("..." if len(latest["text"]) > 200 else ""),
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_PRIMARY,
            wraplength=700,
            justify="left",
        ).pack(padx=12, pady=10, anchor="w")

        for m in config.get("members", []):
            done = m["user_id"] in completed
            row = ctk.CTkFrame(
                self.status_frame,
                corner_radius=6,
                fg_color=Colors.BG_CARD_HOVER if done else "transparent",
            )
            row.pack(fill="x", padx=8, pady=1)
            icon_color = Colors.SUCCESS if done else Colors.TEXT_MUTED
            ctk.CTkLabel(
                row,
                text="✓" if done else "○",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=icon_color,
                width=24,
            ).pack(side="left", padx=(10, 4), pady=4)
            ctk.CTkLabel(
                row,
                text=m["name"],
                anchor="w",
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_PRIMARY if done else Colors.TEXT_SECONDARY,
            ).pack(side="left", pady=4)

        done_n = len(completed)
        total = len(config.get("members", []))
        sf = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        sf.pack(fill="x", padx=8, pady=(12, 8))
        ctk.CTkLabel(
            sf,
            text=f"{done_n}/{total} completed",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=Colors.TEAL,
        ).pack(anchor="w", padx=4)
        pb = ctk.CTkProgressBar(
            sf,
            width=400,
            height=8,
            corner_radius=4,
            fg_color=Colors.BORDER,
            progress_color=Colors.TEAL,
        )
        pb.pack(anchor="w", padx=4, pady=(6, 0))
        pb.set(done_n / total if total else 0)

        choices = [f"#{a['id']} — {a['text'][:60]}..." for a in data["announcements"]]
        self.past_menu.configure(values=choices)
        self.past_menu.set(choices[-1])

    def _do_retract(self):
        s = self.past_menu.get()
        if not s or s.startswith("(none)"):
            return
        ann_id = int(s.split("—")[0].strip().lstrip("#"))
        threading.Thread(
            target=self._worker_retract, args=(ann_id,), daemon=True
        ).start()

    def _worker_retract(self, ann_id):
        data = load_data()
        target = next((a for a in data["announcements"] if a["id"] == ann_id), None)
        if not target or not target.get("sent_messages"):
            self.after(
                0,
                lambda: self._msg(
                    f"#{ann_id} has no retractable messages.", Colors.WARNING
                ),
            )
            return

        loop = asyncio.new_event_loop()
        client = get_matrix_client()

        async def run():
            if not await matrix_login(client):
                self.after(0, lambda: self._msg("Login failed.", Colors.DANGER))
                return
            deleted = 0
            for entry in target["sent_messages"]:
                try:
                    await matrix_redact(client, ROOM_ID, entry["event_id"])
                    deleted += 1
                except Exception:
                    pass
            self.after(0, self._refresh_status)
            self.after(
                0,
                lambda: self._msg(
                    f"Retracted {deleted}/{len(target['sent_messages'])} for #{ann_id}.",
                    Colors.SUCCESS if deleted else Colors.WARNING,
                ),
            )
            await client.close()

        loop.run_until_complete(run())
        loop.close()

    # ================================
    #  TAB 3 — Members
    # ================================

    def _build_members_tab(self):
        tab = self.tab.add("  Members  ")

        self._section(tab, "ADD MEMBER")
        add_card = self._card(tab)
        add_card.pack(fill="x", padx=16, pady=(0, 12))

        row = ctk.CTkFrame(add_card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(
            row,
            text="User ID:",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(side="left")
        self.add_id = ctk.CTkEntry(
            row,
            width=240,
            height=34,
            corner_radius=8,
            placeholder_text="@user:matrix.org",
        )
        self.add_id.pack(side="left", padx=(6, 16))

        ctk.CTkLabel(
            row, text="Name:", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED
        ).pack(side="left")
        self.add_name = ctk.CTkEntry(
            row, width=180, height=34, corner_radius=8, placeholder_text="Full name"
        )
        self.add_name.pack(side="left", padx=(6, 16))

        ctk.CTkButton(
            row,
            text="Add",
            width=80,
            height=34,
            corner_radius=8,
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
            command=self._do_add_member,
        ).pack(side="left")

        hdr = ctk.CTkFrame(tab, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(0, 6))
        self.member_hdr = ctk.CTkLabel(
            hdr,
            text="TEAM MEMBERS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        )
        self.member_hdr.pack(side="left")
        ctk.CTkButton(
            hdr,
            text="Refresh",
            width=70,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BG_CARD_HOVER,
            command=self._refresh_members,
        ).pack(side="right")

        self.member_frame = ctk.CTkScrollableFrame(
            tab, height=280, corner_radius=10, fg_color=Colors.BG_CARD
        )
        self.member_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _refresh_members(self):
        config = load_config()
        for w in self.member_frame.winfo_children():
            w.destroy()
        self.member_hdr.configure(
            text=f"TEAM MEMBERS ({len(config.get('members', []))})"
        )

        for i, m in enumerate(config.get("members", [])):
            row = ctk.CTkFrame(
                self.member_frame,
                corner_radius=8,
                fg_color=Colors.BG_CARD_HOVER if i % 2 == 0 else "transparent",
            )
            row.pack(fill="x", padx=6, pady=2)

            avatar = ctk.CTkFrame(
                row, width=30, height=30, corner_radius=15, fg_color=Colors.TEAL_DARK
            )
            avatar.pack(side="left", padx=(10, 10), pady=6)
            avatar.pack_propagate(False)
            ctk.CTkLabel(
                avatar,
                text=m["name"][0].upper(),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=Colors.TEXT_PRIMARY,
            ).pack(expand=True)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="y", pady=6)
            ctk.CTkLabel(
                info,
                text=m["name"],
                anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w")
            ctk.CTkLabel(
                info,
                text=m["user_id"],
                anchor="w",
                font=ctk.CTkFont(size=10, family="Courier"),
                text_color=Colors.TEXT_MUTED,
            ).pack(anchor="w")

            ctk.CTkButton(
                row,
                text="Remove",
                width=65,
                height=24,
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
        uid = self.add_id.get().strip()
        name = self.add_name.get().strip()
        if not uid or not name:
            self._msg("Enter both User ID and Name.", Colors.WARNING)
            return
        config = load_config()
        if get_member_name(config, uid) != uid:
            self._msg(f"{name} already exists.", Colors.WARNING)
            return
        config["members"].append({"user_id": uid, "name": name})
        save_config(config)
        self.add_id.delete(0, "end")
        self.add_name.delete(0, "end")
        self._refresh_members()
        self._refresh_test_checkboxes()
        self._msg(f"Added {name}", Colors.SUCCESS)

    def _remove_member(self, uid):
        config = load_config()
        before = len(config["members"])
        config["members"] = [m for m in config["members"] if m["user_id"] != uid]
        if len(config["members"]) < before:
            save_config(config)
            self._refresh_members()
            self._refresh_test_checkboxes()

    # ================================
    #  TAB 4 — Test Users
    # ================================

    def _build_test_tab(self):
        tab = self.tab.add("  Test Users  ")

        self._section(tab, "ADD TEST RECIPIENT")
        add_card = self._card(tab)
        add_card.pack(fill="x", padx=16, pady=(0, 12))
        row = ctk.CTkFrame(add_card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=10)
        self.test_id_entry = ctk.CTkEntry(
            row,
            width=280,
            height=34,
            corner_radius=8,
            placeholder_text="@user:matrix.org",
        )
        self.test_id_entry.pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            row,
            text="Add",
            width=80,
            height=34,
            corner_radius=8,
            fg_color=Colors.TEAL,
            hover_color=Colors.TEAL_DARK,
            command=self._do_add_test_id,
        ).pack(side="left")

        hdr = ctk.CTkFrame(tab, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(0, 6))
        self.test_list_hdr = ctk.CTkLabel(
            hdr,
            text="TEST RECIPIENTS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEAL,
        )
        self.test_list_hdr.pack(side="left")

        self.test_frame = ctk.CTkScrollableFrame(
            tab, height=200, corner_radius=10, fg_color=Colors.BG_CARD
        )
        self.test_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        ctk.CTkLabel(
            tab,
            text="Test users receive announcements when using 'Send to Selected'.",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkButton(
            tab,
            text="Clear All",
            width=90,
            height=30,
            corner_radius=8,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            command=self._do_clear_test_ids,
        ).pack(anchor="w", padx=16, pady=(0, 16))

    def _refresh_test(self):
        config = load_config()
        ids = config.get("test_user_ids", [])
        for w in self.test_frame.winfo_children():
            w.destroy()
        self.test_list_hdr.configure(text=f"TEST RECIPIENTS ({len(ids)})")

        if not ids:
            ctk.CTkLabel(
                self.test_frame,
                text="No test recipients.",
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED,
            ).pack(pady=20)
            return

        for uid in ids:
            name = get_member_name(config, uid)
            reg = name != uid
            row = ctk.CTkFrame(
                self.test_frame, corner_radius=6, fg_color=Colors.BG_CARD_HOVER
            )
            row.pack(fill="x", padx=6, pady=2)
            ctk.CTkLabel(
                row,
                text="✓" if reg else "?",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=Colors.SUCCESS if reg else Colors.WARNING,
                width=24,
            ).pack(side="left", padx=(10, 4), pady=6)
            lbl = f"{name} — {uid}" if reg else f"{uid} (not in members)"
            ctk.CTkLabel(
                row,
                text=lbl,
                anchor="w",
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_PRIMARY if reg else Colors.TEXT_MUTED,
            ).pack(side="left", pady=6)
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
            self._msg(f"{uid} already a test user.", Colors.WARNING)
            return
        current.append(uid)
        config["test_user_ids"] = current
        save_config(config)
        self.test_id_entry.delete(0, "end")
        self._refresh_test()
        self._msg(f"Added {uid}", Colors.SUCCESS)

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
        self._msg("Test users cleared.", Colors.SUCCESS)

    # ================================
    #  TAB 5 — Settings
    # ================================

    def _build_settings_tab(self):
        tab = self.tab.add("  Settings  ")

        self._section(tab, "BOT CONFIGURATION")
        card = self._card(tab)
        card.pack(fill="x", padx=16, pady=(0, 16))
        self._row(card, "Homeserver:", HOMESERVER or "Not set")
        self._row(card, "User ID:", USER_ID or "Not set")
        self._row(card, "Room ID:", ROOM_ID or "Not set (DM mode)")
        self._row(card, "Admin:", ADMIN_ID or "Not set")
        status = "Connected" if self.matrix_ready else "Not configured"
        color = Colors.SUCCESS if self.matrix_ready else Colors.DANGER
        self._row(card, "Status:", status, color)

        self._section(tab, "DATA FILES")
        dc = self._card(tab)
        dc.pack(fill="x", padx=16, pady=(0, 16))
        self._row(dc, "Config:", str(CONFIG_FILE))
        self._row(dc, "Data:", str(DATA_FILE))
        self._row(dc, ".env:", str(BASE_DIR / ".env"))

        self._section(tab, "INFO")
        ic = self._card(tab)
        ic.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkLabel(
            ic,
            text=(
                "This GUI shares config.json and data.json with bot.py. "
                "Changes here are visible to the bot immediately.\n\n"
                "Members confirm engagement by reacting with ✅ to announcements."
            ),
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_SECONDARY,
            justify="left",
            wraplength=700,
        ).pack(anchor="w", padx=16, pady=12)

    @staticmethod
    def _row(parent, label, value, color=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(
            row,
            text=label,
            width=110,
            anchor="w",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEXT_MUTED,
        ).pack(side="left")
        ctk.CTkLabel(
            row,
            text=value,
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=color or Colors.TEXT_PRIMARY,
        ).pack(side="left", padx=(8, 0))

    def _refresh_all(self):
        self._refresh_status()
        self._refresh_members()
        self._refresh_test()
        self._refresh_test_checkboxes()


if __name__ == "__main__":
    AdminApp().mainloop()
