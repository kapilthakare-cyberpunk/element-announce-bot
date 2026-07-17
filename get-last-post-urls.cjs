#!/usr/bin/env node
/**
 * get-last-post-urls.js
 *
 * Reads credentials from .env, .env.telegram, .env.element,
 * and pnz-marketing-2026/.env.
 * Queries the official “latest‑post” endpoint for each supported platform
 * and returns the direct public URL (or a clear failure message).
 *
 * Supported platforms:
 *   Telegram   – https://t.me/c/<chatId>/<messageId>
 *   Instagram  – https://www.instagram.com/p/<shortcode>
 *   Facebook   – https://www.facebook.com/<PAGE_ID>/posts/<POST_ID>
 *   LinkedIn   – https://www.linkedin.com/feed/update/<URN>/
 *
 * Unsupported:
 *   WhatsApp, Matrix – no public URL.
 *
 * -------------------------------------------------------------
 * Prerequisites
 * -------------------------------------------------
 *   - node >= 18 (global fetch is available)
 *
 * ------------------------------------------------------------- */

const fs = require("fs");
const path = require("path");

// -------------------------------------------------------------------
// 1️⃣ Helper – load every .env file we might have
// -------------------------------------------------------------------
const dotEnvPaths = [
  path.resolve(process.cwd(), ".env"),                // pnz-marketing-2026/.env
  path.resolve(process.cwd(), ".env.telegram"),      // telegram-announce-bot/.env
  path.resolve(process.cwd(), ".env.element"),       // element-announce-bot/.env.example (renamed)
];

for (const file of dotEnvPaths) {
  if (fs.existsSync(file)) {
    const lines = fs.readFileSync(file, "utf-8").split("\n");
    for (const line of lines) {
      const match = line.match(/^([^#=]+)=(.*)$/);
      if (match) {
        process.env[match[1]] = match[2];
        
        // Map alternative token names for Telegram
        if (match[1] === "BOT_TOKEN") process.env.TELEGRAM_BOT_TOKEN = match[2];
        if (match[1] === "ADMIN_ID") process.env.TELEGRAM_CHANNEL_ID = match[2];
      }
    }
  }
};

// -------------------------------------------------------------------
// 2️⃣ Platform‑specific helpers
// -------------------------------------------------------------------
async function getTelegramLastUrl() {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHANNEL_ID || process.env.TELEGRAM_MY_CHAT_ID;
  if (!token) return null;

  const url = `https://api.telegram.org/bot${token}/getUpdates?offset=-1&timeout=30`;
  const res = await fetch(url);
  const json = await res.json();

  if (!json.ok) return null;
  const msg = json.result?.[0]?.message;
  if (!msg?.chat?.id || !msg?.message_id) return null;

  // Public t.me link: https://t.me/c/<chatId>/<messageId>
  return `https://t.me/c/${msg.chat.id}/${msg.message_id}`;
}

async function getInstagramLastUrl() {
  const igAcct = process.env.INSTAGRAM_BUSINESS_ACCOUNT_ID;
  const pageToken = process.env.FACEBOOK_PAGE_TOKEN;
  if (!igAcct || !pageToken) return null;

  const url = `https://graph.facebook.com/v19.0/${igAcct}/media?fields=id,shortcode,permalink,permalink_url&access_token=${pageToken}&limit=1`;
  const res = await fetch(url);
  const json = await res.json();
  const post = json.data?.[0];
  if (!post) return null;
  return post.permalink || post.permalink_url || (post.shortcode ? `https://www.instagram.com/p/${post.shortcode}/` : `https://www.instagram.com/p/${post.id}/`);
}

async function getFacebookLastUrl() {
  const pageId = process.env.FACEBOOK_PAGE_ID;
  const pageToken = process.env.FACEBOOK_PAGE_TOKEN;
  if (!pageId || !pageToken) return null;

  const url = `https://graph.facebook.com/v19.0/${pageId}/feed?fields=id,permalink_url&limit=1&access_token=${pageToken}`;
  const res = await fetch(url);
  const json = await res.json();
  const post = json.data?.[0];
  if (!post) return null;
  return post.permalink_url || `https://facebook.com/${post.id}`;
}

async function getLinkedInLastUrl() {
  const accessToken = process.env.LINKEDIN_ACCESS_TOKEN;
  const orgId = process.env.LINKEDIN_ORG_ID;
  if (!accessToken || !orgId) return null;

  const url = `https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List(urn%3Ali%3Aorganization%3A${orgId})&count=1`;
  const res = await fetch(url, {
    headers: { 
      Authorization: `Bearer ${accessToken}`,
      "X-Restli-Protocol-Version": "2.0.0"
    },
  });
  const json = await res.json();
  const urn = json.elements?.[0]?.id;
  if (!urn) return null;
  return `https://www.linkedin.com/feed/update/${urn}/`;
};

async function getYouTubeLastUrl() {
  let accessToken = process.env.YOUTUBE_ACCESS_TOKEN;
  const refreshToken = process.env.YOUTUBE_REFRESH_TOKEN;
  const clientId = process.env.YOUTUBE_CLIENT_ID;
  const clientSecret = process.env.YOUTUBE_CLIENT_SECRET;
  
  if (!accessToken && !refreshToken) return null;

  async function fetchLatestVideo(token) {
    const url = `https://www.googleapis.com/youtube/v3/search?part=snippet&forMine=true&order=date&type=video&maxResults=1`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    return res.json();
  }

  let json = await fetchLatestVideo(accessToken);

  if (json.error && json.error.code === 401 && refreshToken) {
    const tokenUrl = "https://oauth2.googleapis.com/token";
    const refreshRes = await fetch(tokenUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: clientId,
        client_secret: clientSecret,
        refresh_token: refreshToken,
        grant_type: "refresh_token"
      })
    });
    const refreshJson = await refreshRes.json();
    if (refreshJson.access_token) {
      accessToken = refreshJson.access_token;
      json = await fetchLatestVideo(accessToken);
    }
  }

  const videoId = json.items?.[0]?.id?.videoId;
  if (!videoId) return null;
  return `https://www.youtube.com/watch?v=${videoId}`;
}

// -------------------------------------------------------------------
// 3️⃣ Main driver – collect and output JSON
// -------------------------------------------------------------------
async function main() {
  const results = {};

  // Telegram
  const tgUrl = await getTelegramLastUrl();
  results.telegram = tgUrl ?? "❌ No recent post / token missing";

  // Instagram
  const IGUrl = await getInstagramLastUrl();
  results.instagram = IGUrl ?? "❌ No recent post / token missing";

  // Facebook
  const FBUrl = await getFacebookLastUrl();
  results.facebook = FBUrl ?? "❌ No recent page post / token missing";

  // LinkedIn
  const LIUrl = await getLinkedInLastUrl();
  results.linkedin = LIUrl ?? "❌ No recent org post / token missing";

  // YouTube
  const YTUrl = await getYouTubeLastUrl();
  results.youtube = YTUrl ?? "❌ No recent video / token missing";

  // Pretty‑print
  console.log("\n📎  LAST POST URLS\n");
  console.log(JSON.stringify(results, null, 2));
  console.log("\n✅ Done.");
}

// -------------------------------------------------------------------
// 6️⃣ Run
// -------------------------------------------------------------------
main()
  .then(() => process.exit(0))
  .catch((e) => {
    console.error("❌ Unexpected error:", e);
    process.exit(1);
  });