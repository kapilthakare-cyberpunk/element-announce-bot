# Code Review: Element Announce Bot

**Date:** 2026-07-24

---

## 1. 🔴 Critical: E2EE is Disabled Despite Claims

`bot.py:614` and `admin_gui.py:83` both set `encryption_enabled=False`. The README and branding claim "End-to-end encrypted" — this is **false**. Messages are sent as plaintext.

**Fix:** Either enable encryption (requires `libolm` and key upload) or update all documentation to remove E2EE claims.

---

## 2. 🟠 Security Issues

### 2.1 Credentials in Plaintext
`bot.py:646-653` — `credentials.json` stores `access_token` and `device_id` in the clear on disk.

**Fix:** Use OS keychain integration or at minimum set restrictive file permissions (`chmod 600`).

### 2.2 No Input Sanitization
`bot.py:275-301` — `/register` accepts arbitrary names with no validation.

**Fix:** Strip HTML, limit length, reject special characters.

### 2.3 No Rate Limiting
`/register` can be spammed by any user in the room.

**Fix:** Add per-user cooldown tracking.

---

## 3. 🟠 Major DRY Violations (Triple Duplicated Code)

The core send-announcement-to-DM logic (including personal name substitution and DM safety verification) is duplicated **3 times**:

| Location | Lines | Context |
|---|---|---|
| `bot.py` | 453–525 | `cmd_confirm` (bot) |
| `admin_gui.py` | 444–554 | `_worker_send_all` (GUI) |
| `admin_gui.py` | 582–668 | `_worker_send_test` (GUI) |

Matrix **login** is also duplicated across `bot.py:633-671` and `admin_gui.py:88-131`.

**Fix:** Extract both login and DM-sending into shared functions in `common.py`.

---

## 4. 🟡 Hardcoded Personalization Logic

```python
# bot.py:497-500 and admin_gui.py:496-501, 630-634
if "abhijit" in m["name"].lower():
    personal_name = "Abhijit Sir"
else:
    personal_name = first_name
```

**Fix:** Move this to a configurable mapping in `config.json`.

---

## 5. 🟡 Threading + asyncio Anti-pattern

The GUI spawns `threading.Thread` with `asyncio.new_event_loop()` for every send/retract operation.

**Fix:** Use a single background event loop with `asyncio.run_coroutine_threadsafe()` instead.

---

## 6. 🟠 Race Conditions on File I/O

`load_config()` / `save_config()` are called from both the bot's async loop and GUI threads simultaneously with **no file locking**. Concurrent writes will corrupt `config.json` / `data.json`.

**Fix:** Add a file-level lock (e.g., `portalocker` or `fcntl`).

---

## 7. 🔴 Bug: GUI Retraction Uses Wrong Room ID

`admin_gui.py:1041` uses the global `ROOM_ID` for redaction, but announcements are sent via DM — each DM has a different room ID. The redaction will silently fail for DMs.

`bot.py`'s `cmd_retract` correctly uses `room.room_id`.

**Fix:** Store the actual DM room ID alongside each `sent_messages` entry and use that for redaction.

---

## 8. 🟡 Fragile Reaction Handling

`bot.py:629` registers `on_reaction` for `UnknownEvent` — unreliable across nio versions. The handler manually parses `event.source` dicts.

**Fix:** Use typed event classes or catch the specific reaction event type.

---

## 9. 🔵 Minor Issues

| # | Issue | Location |
|---|---|---|
| 9.1 | Chinese text mixed into English comment: "真正的 1-on-1 DMs" | `common.py:74` |
| 9.2 | `get-last-post-urls.cjs` references hardcoded `pnz-marketing-2026/` paths that don't exist in this repo | `get-last-post-urls.cjs:33` |
| 9.3 | `fi.mau.dont_render` is non-standard (Element fork flag) | `bot.py:78`, `admin_gui.py:139` |
| 9.4 | `.env.example` missing YouTube/LinkedIn env vars referenced by `*.cjs` scripts | `.env.example` |
| 9.5 | **Zero tests** in the entire codebase | — |
| 9.6 | Template save overwrites without confirmation | `admin_gui.py:722` |

---

## Summary

| Severity | Count | Key Areas |
|---|---|---|
| 🔴 Critical | 2 | E2EE disabled despite claims, GUI retraction uses wrong room |
| 🟠 High | 3 | DRY violations, race conditions on file I/O |
| 🟡 Medium | 4 | No tests, hardcoded logic, fragile threading, reaction handling |
| 🔵 Low | 6 | Chinese comment, stale paths, non-standard flag, missing env vars, overwrite behavior |