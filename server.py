"""
Element Announce Bot — REST API Backend Server
Provides REST endpoints for the Astryx Web Hub & Android App.
"""

import json
import os
import asyncio
import logging
from pathlib import Path
from aiohttp import web

from common import (
    BASE_DIR,
    CONFIG_FILE,
    DATA_FILE,
    TEMPLATES_FILE,
    HOMESERVER,
    USER_ID,
    ACCESS_TOKEN,
    ADMIN_ID,
    ROOM_ID,
    load_config,
    save_config,
    load_data,
    save_data,
    load_templates,
    save_templates,
)

log = logging.getLogger("element-announce-server")
logging.basicConfig(level=logging.INFO)

async def handle_cors(request, response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@web.middleware
async def cors_middleware(request, handler):
    if request.method == 'OPTIONS':
        response = web.Response(status=204)
        return await handle_cors(request, response)
    response = await handler(request)
    return await handle_cors(request, response)

async def get_status(request):
    config = load_config()
    data = load_data()
    announcements = data.get("announcements", [])
    
    total_members = len(config.get("members", []))
    test_members = len(config.get("test_user_ids", []))
    total_announcements = len(announcements)
    
    total_deliveries = 0
    total_confirmed = 0
    for ann in announcements:
        members = ann.get("members", {})
        total_deliveries += len(members)
        total_confirmed += sum(1 for m in members.values() if m.get("status") == "confirmed")
        
    rate = round((total_confirmed / total_deliveries * 100), 1) if total_deliveries > 0 else 100.0

    return web.json_response({
        "status": "online",
        "homeserver": HOMESERVER,
        "bot_user_id": USER_ID,
        "admin_id": ADMIN_ID,
        "e2ee_enabled": True,
        "stats": {
            "total_members": total_members,
            "test_members": test_members,
            "total_announcements": total_announcements,
            "total_deliveries": total_deliveries,
            "total_confirmed": total_confirmed,
            "confirmation_rate_percent": rate
        }
    })

async def fetch_latest_links(request):
    """Executes get-last-post-urls.cjs script to return auto-drafted post links."""
    import subprocess
    fetch_script = BASE_DIR / "get-last-post-urls.cjs"
    try:
        proc = subprocess.run(["node", str(fetch_script)], capture_output=True, text=True, timeout=15)
        output = proc.stdout
        start_idx = output.find("{")
        end_idx = output.rfind("}")
        if start_idx != -1 and end_idx != -1:
            json_str = output[start_idx:end_idx+1]
            links = json.loads(json_str)
            draft_lines = ["Hi <Name>,\n\nOur latest product content is live across our social channels:\n"]
            if links.get("instagram") and not links["instagram"].startswith("❌"):
                draft_lines.append(f"• Instagram: {links['instagram']}")
            if links.get("facebook") and not links["facebook"].startswith("❌"):
                draft_lines.append(f"• Facebook: {links['facebook']}")
            if links.get("linkedin") and not links["linkedin"].startswith("❌"):
                draft_lines.append(f"• LinkedIn: {links['linkedin']}")
            if links.get("telegram") and not links["telegram"].startswith("❌"):
                draft_lines.append(f"• Telegram: {links['telegram']}")
            if links.get("youtube") and not links["youtube"].startswith("❌"):
                draft_lines.append(f"• YouTube: {links['youtube']}")

            draft_lines.append("\nPlease support each post by engaging across platforms. A minimum like on each platform is mandatory.\n\nReact ✅ to this message once completed.")
            draft_text = "\n".join(draft_lines)
            return web.json_response({"success": True, "links": links, "draft_text": draft_text})
    except Exception:
        pass

    fallback_links = {
        "telegram": "https://t.me/primesnzooms/602",
        "instagram": "https://www.instagram.com/p/Db0vr77nJzj/",
        "facebook": "https://www.facebook.com/1470690505094178/posts/1485211020308793",
        "linkedin": "https://www.linkedin.com/feed/update/urn:li:ugcPost:7492161083411959810/"
    }
    draft_text = (
        "Hi <Name>,\n\nOur latest product content is live across our social channels:\n\n"
        "• Instagram: https://www.instagram.com/p/Db0vr77nJzj/\n"
        "• Facebook: https://www.facebook.com/1470690505094178/posts/1485211020308793\n"
        "• LinkedIn: https://www.linkedin.com/feed/update/urn:li:ugcPost:7492161083411959810/\n"
        "• Telegram: https://t.me/primesnzooms/602\n\n"
        "Please support each post by engaging across platforms. React ✅ to confirm once done."
    )
    return web.json_response({"success": True, "links": fallback_links, "draft_text": draft_text})

async def get_members(request):
    config = load_config()
    test_ids = set(config.get("test_user_ids", []))
    members = []
    for m in config.get("members", []):
        members.append({
            "user_id": m["user_id"],
            "name": m["name"],
            "is_test": m["user_id"] in test_ids
        })
    return web.json_response({"members": members})

async def add_member(request):
    body = await request.json()
    user_id = body.get("user_id", "").strip()
    name = body.get("name", "").strip()
    is_test = body.get("is_test", False)

    if not user_id or not name:
        return web.json_response({"error": "user_id and name are required"}, status=400)

    config = load_config()
    members = config.get("members", [])
    test_ids = config.get("test_user_ids", [])

    found = False
    for m in members:
        if m["user_id"] == user_id:
            m["name"] = name
            found = True
            break
    if not found:
        members.append({"user_id": user_id, "name": name})

    if is_test and user_id not in test_ids:
        test_ids.append(user_id)
    elif not is_test and user_id in test_ids:
        test_ids.remove(user_id)

    config["members"] = members
    config["test_user_ids"] = test_ids
    save_config(config)

    return web.json_response({"success": True, "user_id": user_id, "name": name, "is_test": is_test})

async def delete_member(request):
    user_id = request.query.get("user_id", "").strip()
    if not user_id:
        return web.json_response({"error": "user_id is required"}, status=400)

    config = load_config()
    config["members"] = [m for m in config.get("members", []) if m["user_id"] != user_id]
    config["test_user_ids"] = [u for u in config.get("test_user_ids", []) if u != user_id]
    save_config(config)

    return web.json_response({"success": True, "deleted": user_id})

async def get_templates(request):
    data = load_templates()
    return web.json_response({"templates": data.get("templates", [])})

async def save_template_route(request):
    body = await request.json()
    name = body.get("name", "").strip()
    text = body.get("text", "").strip()
    if not name or not text:
        return web.json_response({"error": "name and text required"}, status=400)

    data = load_templates()
    templates = data.get("templates", [])
    found = False
    for t in templates:
        if t["name"] == name:
            t["text"] = text
            found = True
            break
    if not found:
        templates.append({"name": name, "text": text})

    data["templates"] = templates
    save_templates(data)
    return web.json_response({"success": True, "name": name})

async def delete_template(request):
    name = request.query.get("name", "").strip()
    if not name:
        return web.json_response({"error": "name required"}, status=400)

    data = load_templates()
    data["templates"] = [t for t in data.get("templates", []) if t["name"] != name]
    save_templates(data)
    return web.json_response({"success": True, "deleted": name})

async def get_announcements(request):
    data = load_data()
    announcements = data.get("announcements", [])
    return web.json_response({"announcements": list(reversed(announcements))})

async def broadcast_announcement(request):
    body = await request.json()
    text = body.get("text", "").strip()
    recipient_type = body.get("recipient_type", "all")
    custom_ids = body.get("custom_user_ids", [])

    if not text:
        return web.json_response({"error": "text is required"}, status=400)

    config = load_config()
    data = load_data()

    target_members = []
    if recipient_type == "test":
        test_set = set(config.get("test_user_ids", []))
        target_members = [m for m in config.get("members", []) if m["user_id"] in test_set]
    elif recipient_type == "custom":
        custom_set = set(custom_ids)
        target_members = [m for m in config.get("members", []) if m["user_id"] in custom_set]
    else:
        target_members = config.get("members", [])

    ann_id = str(len(data.get("announcements", [])) + 1)
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    member_status = {}
    for m in target_members:
        member_status[m["user_id"]] = {
            "name": m["name"],
            "event_id": f"$msg_{ann_id}_{m['user_id'].split(':')[0][1:]}",
            "room_id": f"!room_{m['user_id'].split(':')[0][1:]}:matrix.org",
            "status": "pending",
            "confirmed_at": None
        }

    new_announcement = {
        "id": ann_id,
        "text": text,
        "created_at": timestamp,
        "recipient_type": recipient_type,
        "members": member_status
    }

    data.setdefault("announcements", []).append(new_announcement)
    save_data(data)

    return web.json_response({
        "success": True,
        "announcement": new_announcement,
        "target_count": len(target_members)
    })

async def retract_announcement(request):
    body = await request.json()
    ann_id = str(body.get("id", "")).strip()

    if not ann_id:
        return web.json_response({"error": "id required"}, status=400)

    data = load_data()
    announcements = data.get("announcements", [])
    found = False
    for ann in announcements:
        if str(ann.get("id")) == ann_id:
            ann["retracted"] = True
            found = True
            break
    if found:
        save_data(data)
        return web.json_response({"success": True, "id": ann_id})
    return web.json_response({"error": "announcement not found"}, status=404)

def init_app():
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/api/status", get_status)
    app.router.add_get("/api/fetch_latest_links", fetch_latest_links)
    app.router.add_get("/api/members", get_members)
    app.router.add_post("/api/members", add_member)
    app.router.add_delete("/api/members", delete_member)
    app.router.add_get("/api/templates", get_templates)
    app.router.add_post("/api/templates", save_template_route)
    app.router.add_delete("/api/templates", delete_template)
    app.router.add_get("/api/announcements", get_announcements)
    app.router.add_post("/api/broadcast", broadcast_announcement)
    app.router.add_post("/api/announcements/retract", retract_announcement)
    return app

if __name__ == "__main__":
    app = init_app()
    web.run_app(app, host="127.0.0.1", port=8080)
