import os
import re
import json
import logging
import asyncio
import aiohttp
import inspect
from urllib.parse import quote_plus
from datetime import datetime
from bs4 import BeautifulSoup
from collections import defaultdict
from plugins.Dreamxfutures.Imdbposter import get_movie_detailsx, fetch_image, get_movie_details
from database.users_chats_db import db
from pyrogram import Client, filters, enums
from info import CHANNELS, MOVIE_UPDATE_CHANNEL, LINK_PREVIEW, BAD_WORDS, TMDB_POSTER, ADMINS, TMDB_API_KEY
from Script import script
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp
from pymongo.errors import PyMongoError, DuplicateKeyError
from pyrogram.errors import MessageIdInvalid, MessageNotModified, FloodWait
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_HDHUB_DOMAIN = "https://new1.hdhub4u.free"

try:
    from info import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

PIRACY_STRIP_REGEX = re.compile(
    r'\b(?:'
    r'ds4k|ds1080p|ds720p|ds480p|line[\s._-]*aud(?:io)?|line|org[\s._-]*aud(?:io)?|org|'
    r'clean[\s._-]*aud(?:io)?|mic|hq[\s._-]*line|hq[\s._-]*mic|'
    r'esub|esubs|msub|hardsub|softsub|sub|subs|dub|dubbed|multi|dual|'
    r'x264|x265|h264|h265|hevc|avc|10bit|10-bit|8bit|dovi|hdr10\+|hdr10|hdr|dv|'
    r'ddp5\.1|ddp5|dd5\.1|ddp|dd|ac3|eac3|aac|atmos|dts|truehd|mp3|'
    r'webrip|web-dl|webdl|web|dl|bluray|brrip|bdrip|remux|imax|proper|repack|'
    r'hdcam|hdtc|camrip|cam|ts|tc|hdts|telesync|dvdscr|dvdrip|predvd|'
    r'reloaded|uncut|the[\s._-]*rule|rule|special[\s._-]*edition|'
    r'2160p|1440p|1080p|720p|540p|480p|360p|240p|4k|2k|'
    r'v1|v2|v3|v4|v5|v6|ver\d+|version\d+'
    r')\b',
    re.IGNORECASE
)

_BASE_IGNORE_WORDS = {
    "rarbg", "dub", "sub", "sample", "mkv", "mp4", "avi", "aac", "ac3", "eac3", "ddp", "ddp5", "atmos", "dts",
    "combined", "esub", "msub", "proper", "repack", "unrated", "extended", "imax", "remux", "10bit", "10-bit",
    "x264", "x265", "h264", "h265", "hevc", "avc", "dovi", "hdr", "hdr10", "hdr10+",
    "web", "dl", "bonus", "special", "ott", "reloaded", "uncut", "ds4k", "line",
    "action", "adventure", "animation", "biography", "comedy", "crime",
    "documentary", "drama", "fantasy", "film-noir", "history",
    "horror", "music", "musical", "mystery", "romance", "sci-fi", "sport",
    "thriller", "war", "western", "hdcam", "hdtc", "camrip", "cam", "ts", "tc", "hdts",
    "telesync", "dvdscr", "dvdrip", "predvd", "webrip", "web-dl", "tvrip",
    "hdtv", "web dl", "webdl", "bluray", "brrip", "bdrip", "360p", "480p",
    "720p", "1080p", "2160p", "4k", "1440p", "540p", "240p", "140p",
    "hdrip", "hq-hdrip", "hq-hdtc", "hq-cam", "hq-ts", "hq-predvd",
    "dual", "multi", "audio", "dubbed",
    "v1", "v2", "v3", "v4", "v5", "v6", "version", "ver", "cleaned", "clean",
    "nf", "netflix", "sonyliv", "sony", "sliv", "amzn", "prime",
    "primevideo", "hotstar", "zee5", "jio", "jhs", "aha", "hbo", "paramount",
    "apple", "atv", "atvp", "appletv", "hoichoi", "sunnxt", "viki", "cr", "crunchyroll", "hulu",
    "disney", "dnp", "lionsgate", "lionsgateplay", "peacock", "max", "alt",
    "altbalaji", "altt", "shemaroo", "shemaroome", "chaupal", "stage",
    "planetmarathi", "manorama", "manoramamax", "tubi", "mxplayer", "mxtv", "eros", "erosnow",
    "5.1", "7.1", "2.0", "5.1ch", "7.1ch", "dd5.1", "ddp5.1", "dd", "ddp",
    "hin", "hindi", "tam", "tamil", "tel", "telugu", "mal", "malayalam", "kan", "kannada",
    "ben", "bengali", "mar", "marathi", "guj", "gujarati", "pun", "punjabi", "eng", "english",
    "kor", "korean", "jpn", "japanese", "chi", "chinese", "spa", "spanish", "fre", "french"
}

IGNORE_WORDS = _BASE_IGNORE_WORDS | set(BAD_WORDS if isinstance(BAD_WORDS, (list, tuple, set)) else [])

CAPTION_LANGUAGES = {
    "hin": "Hindi", "hindi": "Hindi", "tam": "Tamil", "tamil": "Tamil",
    "kan": "Kannada", "kannada": "Kannada", "tel": "Telugu", "telugu": "Telugu",
    "mal": "Malayalam", "malayalam": "Malayalam", "eng": "English", "english": "English",
    "pun": "Punjabi", "punjabi": "Punjabi", "ben": "Bengali", "bengali": "Bengali",
    "mar": "Marathi", "marathi": "Marathi", "guj": "Gujarati", "gujarati": "Gujarati",
    "urd": "Urdu", "urdu": "Urdu", "kor": "Korean", "korean": "Korean",
    "jpn": "Japanese", "japanese": "Japanese", "bho": "Bhojpuri", "bhojpuri": "Bhojpuri",
    "ori": "Odia", "odia": "Odia", "asm": "Assamese", "assamese": "Assamese",
    "spa": "Spanish", "spanish": "Spanish", "fre": "French", "french": "French",
    "ger": "German", "german": "German", "ita": "Italian", "italian": "Italian",
    "rus": "Russian", "russian": "Russian", "chi": "Chinese", "chinese": "Chinese",
    "tha": "Thai", "thai": "Thai", "ind": "Indonesian", "indonesian": "Indonesian",
    "dual": "Dual Audio", "multi": "Multi Audio"
}

OTT_PLATFORMS = {
    "nf": "Netflix", "netflix": "Netflix", "sonyliv": "SonyLiv", "sony": "SonyLiv",
    "sliv": "SonyLiv", "amzn": "Amazon Prime Video", "prime": "Amazon Prime Video",
    "primevideo": "Amazon Prime Video", "amazon": "Amazon Prime Video",
    "hotstar": "Disney+ Hotstar", "disney": "Disney+", "dnp": "Disney+",
    "zee5": "Zee5", "jio": "JioHotstar", "jhs": "JioHotstar", "jiocinema": "JioCinema",
    "aha": "Aha", "hbo": "HBO Max", "max": "Max", "paramount": "Paramount+",
    "apple": "Apple TV+", "atv": "Apple TV+", "atvp": "Apple TV+", "appletv": "Apple TV+",
    "hoichoi": "Hoichoi", "sunnxt": "Sun NXT", "viki": "Viki", "cr": "Crunchyroll",
    "crunchyroll": "Crunchyroll", "hulu": "Hulu", "peacock": "Peacock",
    "lionsgate": "Lionsgate Play", "lionsgateplay": "Lionsgate Play",
    "altbalaji": "ALTT", "alt": "ALTT", "altt": "ALTT", "shemaroo": "ShemarooMe",
    "shemaroome": "ShemarooMe", "chaupal": "Chaupal", "stage": "Stage",
    "planetmarathi": "Planet Marathi", "manorama": "ManoramaMAX", "manoramamax": "ManoramaMAX",
    "tubi": "Tubi", "eros": "Eros Now", "erosnow": "Eros Now"
}

STANDARD_FORMATS = {
    "hdtc": "HDTC", "hd-tc": "HDTC", "hq-hdtc": "HQ-HDTC", "hdcam": "HDCam",
    "hd-cam": "HDCam", "hq-hdcam": "HQ-HDCam", "cam": "CAM", "camrip": "CamRip",
    "hq-cam": "HQ-CAM", "ts": "TS", "hdts": "HDTS", "hq-ts": "HQ-TS", "tc": "TC",
    "telesync": "TeleSync", "predvd": "PreDVD", "hq-predvd": "HQ-PreDVD",
    "dvdrip": "DVDRip", "dvdscr": "DVDScr", "webrip": "WEBRip", "web-dl": "WEB-DL",
    "webdl": "WEB-DL", "web dl": "WEB-DL", "bluray": "BluRay", "brrip": "BRRip",
    "bdrip": "BDRip", "remux": "Remux", "imax": "IMAX", "hdrip": "HDRip",
    "hq-hdrip": "HQ-HDRip", "hdtv": "HDTV", "tvrip": "TVRip", "hevc": "HEVC",
    "10bit": "10-Bit", "10-bit": "10-Bit", "hdr": "HDR", "hdr10": "HDR10",
    "hdr10+": "HDR10+", "dv": "Dolby Vision", "dovi": "Dolby Vision"
}

RES_ORDER = {
    "140p": 140, "240p": 240, "360p": 360, "480p": 480, "540p": 540,
    "720p": 720, "1080p": 1080, "1440p": 1440, "2160p": 2160, "4k": 2160
}

CLEAN_PATTERN = re.compile(
    r'@[^ \n\r\t\.,:;!?()\[\]{}<>\\/"\'=_%]+|'
    r'https?://\S+|www\.\S+|'
    r'[\U00010000-\U0010ffff]|'
    r'[\u2000-\u3300]|'
    r'[\(\[\{][@#\^\*]+[\)\]\}]'
)

NORMALIZE_PATTERN = re.compile(r"[._\-+]+|[()\[\]{}:;'\"–—!,.?~`*^|\\/]")
RESOLUTION_PATTERN = re.compile(r"\b(?:2160p|4K|1440p|1080p|720p|540p|480p|360p|240p|140p)\b", re.IGNORECASE)
SOURCE_PATTERN = re.compile(
    r"\b(?:HDCam|HD-Cam|HQ-HDCam|HDTC|HD-TC|HQ-HDTC|CamRip|CAM|HQ-CAM|TS|HDTS|HQ-TS|TC|TeleSync|DVDScr|DVDRip|PreDVD|HQ-PreDVD|"
    r"WEBRip|WEB-DL|TVRip|HDTV|WEB DL|WebDl|BluRay|BRRip|BDRip|Remux|IMAX|"
    r"HEVC|10Bit|10-Bit|HDRip|HQ-HDRip|HDR10\+|HDR10|HDR|DV|DoVi)\b",
    re.IGNORECASE
)
VERSION_STANDALONE = re.compile(r"\b(?:[vV]\d+|ver\.?\s*\d+|version\s*\d+)\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:19|20)\d{2}(?![A-Za-z0-9])")
AUDIO_CHANNELS_PATTERN = re.compile(
    r'\b(?:DD|DDP|AC3|EAC3|AAC|TRUEHD|ATMOS|DOLBY)?[\s._-]*[257][\s._-][01](?:[\s._-]*CH)?\b',
    re.IGNORECASE
)

BONUS_RANGE_REGEX = re.compile(r'\bS(\d{1,2})[\s._-]*(?:Bonus|Special)[\s._-]*E(?:p(?:isode)?)?0*(\d{1,3})\s*(?:to|-)\s*(?:E(?:p(?:isode)?)?)?0*(\d{1,3})\b', re.IGNORECASE)
BONUS_REGEX = re.compile(r'\bS(\d{1,2})[\s._-]*(?:Bonus|Special)[\s._-]*E(?:p(?:isode)?)?0*(\d{1,3})\b', re.IGNORECASE)
RANGE_REGEX = re.compile(r'\bS(\d{1,2})[\s._-]*(?:Part)?[\s._-]*E(?:p(?:isode)?)?0*(\d{1,3})\s*(?:to|-)\s*(?:E(?:p(?:isode)?)?)?0*(\d{1,3})', re.IGNORECASE)
SINGLE_REGEX = re.compile(r'\bS(\d{1,2})[\s._-]*(?:Part)?[\s._-]*E(?:p(?:isode)?)?0*(\d{1,3})\b', re.IGNORECASE)
NAMED_REGEX = re.compile(r'Season\s*0*(\d{1,2})[\s\-,:]*(?:Part)?[\s\-,:]*Ep(?:isode)?\s*0*(\d{1,3})\b', re.IGNORECASE)
X_REGEX = re.compile(r'(?<!\d)\b0*([1-9]\d?)\s*[xX]\s*0*([1-9]\d?)\b(?!\d)', re.IGNORECASE)
DAY_REGEX = re.compile(r'\b(?:S(?:eason)?\s*0*(\d{1,2})[\s._-]*)?(?:Day\s*0*(\d{1,3})|D0*([1-9]\d{0,2}))\b', re.IGNORECASE)
NO_S_REGEX = re.compile(r'\b(?:Season|S)\s*0*(\d{1,2})[\s._-]+E(?:p(?:isode)?)?0*(\d{1,3})\b', re.IGNORECASE)
EP_ONLY_RANGE = re.compile(r'\b(?:EP|Episode)0*(\d{1,3})\s*-\s*0*(\d{1,3})\b', re.IGNORECASE)
EP_ONLY_SINGLE = re.compile(r'\b(?:EP|Episode)\.?\s*0*(\d{1,3})\b', re.IGNORECASE)

MEDIA_FILTER = filters.document | filters.video | filters.audio

locks = defaultdict(asyncio.Lock)
pending_updates = {}
sending_updates = set()

def clean_mentions_links(text: str) -> str:
    return CLEAN_PATTERN.sub(" ", text or "").strip()

def normalize(s: str) -> str:
    s = NORMALIZE_PATTERN.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()

def remove_ignored_words(text: str) -> str:
    t = PIRACY_STRIP_REGEX.sub(" ", text)
    ignore_words_lower = {w.lower() for w in IGNORE_WORDS}
    words = [w for w in t.split() if w.lower() not in ignore_words_lower]
    return " ".join(words) if words else text

def is_good_title_match(query: str, found_title: str) -> bool:
    if not query or not found_title:
        return False
    q_clean = normalize(YEAR_PATTERN.sub('', query)).lower()
    f_clean = normalize(YEAR_PATTERN.sub('', found_title)).lower()
    q_words = [w for w in q_clean.split() if len(w) >= 2]
    f_words = [w for w in f_clean.split() if len(w) >= 2]
    if not q_words or not f_words:
        return False
    if q_words == f_words or all(qw in f_words for qw in q_words):
        return True
    return False

# =========================================================================
# CLEAN & NATURAL GEMINI AI IDENTIFIER
# =========================================================================
async def identify_movie_with_gemini(filename: str, caption: str = "", duration_mins: Optional[int] = None) -> dict:
    if not GEMINI_API_KEY:
        return {}

    duration_info = f"{duration_mins} mins" if duration_mins else "Unknown"
    prompt = (
        "Identify the official movie or series name from the following media details:\n"
        f"- Filename: {filename}\n"
        f"- Caption: {caption}\n"
        f"- Runtime: {duration_info}\n\n"
        "Extract the real title without codecs or rip tags, release year, whether it is a series or movie, "
        "and official Indian OTT platforms (e.g. Netflix, Disney+ Hotstar, Amazon Prime Video, JioCinema, SonyLiv, Zee5).\n"
        "Return ONLY a raw JSON dictionary without backticks:\n"
        "{\"title\": \"Movie Name\", \"year\": \"YYYY\", \"is_series\": false, \"ott\": [\"Netflix\"]}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
    }

    models = ["gemini-1.5-flash", "gemini-2.0-flash"]
    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for model in models:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            try:
                async with session.post(endpoint, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        raw_text = re.sub(r"^```(?:json)?|```$", "", raw_text, flags=re.MULTILINE).strip()
                        parsed = json.loads(raw_text)
                        if parsed.get("title"):
                            return parsed
            except Exception as e:
                logger.warning(f"Gemini {model} failed: {e}")
                continue
    return {}

def get_qualities(text: str) -> str:
    if not text:
        return "N/A"
    v_match = VERSION_STANDALONE.search(text)
    version_str = None
    if v_match:
        raw_v = v_match.group(0).upper()
        raw_v = re.sub(r'^(?:VER\.?|VERSION)\s*', 'V', raw_v)
        version_str = raw_v if raw_v.startswith("V") else f"V{raw_v}"

    resolutions = [r.lower() if r.lower() != "4k" else "4K" for r in RESOLUTION_PATTERN.findall(text)]
    resolutions = list(dict.fromkeys(resolutions))

    sources = []
    for s in SOURCE_PATTERN.findall(text):
        s_norm = re.sub(r"[._]+", "-", s).strip().lower()
        formatted = STANDARD_FORMATS.get(s_norm, s.upper())
        if formatted not in sources:
            sources.append(formatted)

    if version_str:
        attached = False
        for idx, s in enumerate(sources):
            if any(k in s.upper() for k in ["HDTC", "CAM", "TS", "PREDVD", "WEBRIP", "WEB-DL", "RIP", "BLURAY"]):
                sources[idx] = f"{s} {version_str}"
                attached = True
                break
        if not attached:
            sources.append(version_str)

    all_items = resolutions + sources
    return ", ".join(all_items) if all_items else "N/A"

def format_movie_qualities(quality_list: list) -> str:
    if not quality_list:
        return "N/A"
    resolutions = set()
    sources = set()
    versions = set()

    for item in quality_list:
        if not item or item == "N/A":
            continue
        for vm in VERSION_STANDALONE.findall(item):
            v_num = re.sub(r"\D", "", vm)
            if v_num:
                versions.add(int(v_num))
        for r in RESOLUTION_PATTERN.findall(item):
            resolutions.add(r.lower() if r.lower() != "4k" else "4K")
        for s in SOURCE_PATTERN.findall(item):
            s_norm = re.sub(r"[._]+", "-", s).strip().lower()
            sources.add(STANDARD_FORMATS.get(s_norm, s.upper()))

    if "HQ-HDTC" in sources and "HDTC" in sources: sources.remove("HDTC")
    if "HQ-CAM" in sources: sources.discard("CAM"); sources.discard("HDCam")
    if "HDCam" in sources and "CAM" in sources: sources.remove("CAM")
    if "HQ-TS" in sources: sources.discard("TS"); sources.discard("HDTS")
    if "HDTS" in sources and "TS" in sources: sources.remove("TS")
    if "HQ-PreDVD" in sources and "PreDVD" in sources: sources.remove("PreDVD")
    if "HDR10+" in sources: sources.discard("HDR10"); sources.discard("HDR")
    elif "HDR10" in sources: sources.discard("HDR")

    sorted_res = sorted(resolutions, key=lambda x: RES_ORDER.get(x.lower(), 9999))
    version_str = f"V{max(versions)}" if versions else ""
    source_list = [s for s in sorted(sources)]

    if version_str:
        attached = False
        for idx, s in enumerate(source_list):
            if any(k in s.upper() for k in ["HDTC", "CAM", "TS", "PREDVD", "WEBRIP", "WEB-DL", "RIP", "BLURAY"]):
                source_list[idx] = f"{s} {version_str}"
                attached = True
                break
        if not attached:
            source_list.append(version_str)

    final_parts = sorted_res + source_list
    return ", ".join(final_parts) if final_parts else "N/A"

def extract_ott_platform(text: str) -> str:
    text = text.lower()
    platforms = {plat for key, plat in OTT_PLATFORMS.items() if re.search(rf"\b{re.escape(key)}\b", text)}
    return " | ".join(sorted(platforms)) if platforms else "N/A"

async def fetch_online_ott(imdb_details: dict, tmdb_details: dict, filename: str, caption: str, ai_ott: list = None) -> str:
    platforms = set()

    if ai_ott and isinstance(ai_ott, list):
        for item in ai_ott:
            clean_item = str(item).lower()
            for key, plat in OTT_PLATFORMS.items():
                if re.search(rf"\b{re.escape(key)}\b", clean_item):
                    platforms.add(plat)

    tmdb_id = tmdb_details.get("id") if isinstance(tmdb_details, dict) else None
    media_type = "tv" if (tmdb_details and tmdb_details.get("first_air_date")) else "movie"
    api_key = TMDB_API_KEY

    if not platforms and tmdb_id and api_key:
        try:
            prov_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/watch/providers?api_key={api_key}"
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(prov_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", {})
                        reg_data = results.get("IN") or results.get("US") or {}
                        providers = reg_data.get("flatrate", []) + reg_data.get("buy", []) + reg_data.get("rent", [])
                        for p in providers:
                            p_name = p.get("provider_name", "").lower()
                            for key, plat in OTT_PLATFORMS.items():
                                if re.search(rf"\b{re.escape(key)}\b", p_name):
                                    platforms.add(plat)
        except Exception:
            pass

    if not platforms and imdb_details and isinstance(imdb_details, dict):
        raw_ott = f"{imdb_details.get('distributors', '')} {imdb_details.get('ott', '')}".lower()
        for key, plat in OTT_PLATFORMS.items():
            if re.search(rf"\b{re.escape(key)}\b", raw_ott):
                platforms.add(plat)

    if not platforms:
        unified_text = f"{filename} {caption}".lower()
        for key, plat in OTT_PLATFORMS.items():
            if re.search(rf"\b{re.escape(key)}\b", unified_text):
                platforms.add(plat)

    if "Disney+ Hotstar" in platforms and "Disney+" in platforms: platforms.discard("Disney+")
    if "JioHotstar" in platforms: platforms.discard("Disney+ Hotstar"); platforms.discard("Disney+")
    if "HBO Max" in platforms and "Max" in platforms: platforms.discard("Max")

    return " | ".join(sorted(platforms)) if platforms else "N/A"

def get_clean_title(name: str) -> str:
    t = re.sub(r'\b(19|20)\d{2}\b', '', name)
    t = PIRACY_STRIP_REGEX.sub(" ", t)
    return normalize(t).lower()

def format_runtime(runtime_val, is_series: bool = False) -> str:
    if not runtime_val or str(runtime_val).strip().upper() in ("N/A", "NONE", "0", "-", ""):
        return "N/A"
    if isinstance(runtime_val, (list, tuple)):
        if not runtime_val:
            return "N/A"
        runtime_val = runtime_val[0]

    runtime_str = str(runtime_val).strip()
    runtime_str = re.sub(r'[\s/]*(?:ep|episode)\b', '', runtime_str, flags=re.IGNORECASE).strip()
    total_mins = 0
    try:
        try:
            total_mins = int(float(runtime_str))
        except ValueError:
            colon_match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", runtime_str)
            if colon_match:
                hours = int(colon_match.group(1))
                mins = int(colon_match.group(2))
                total_mins = (hours * 60) + mins
            else:
                hours_match = re.search(r"(\d+)\s*(?:h|hr|hour)s?", runtime_str, re.IGNORECASE)
                mins_match = re.search(r"(\d+)\s*(?:m|min|minute)s?", runtime_str, re.IGNORECASE)
                if hours_match or mins_match:
                    hours = int(hours_match.group(1)) if hours_match else 0
                    mins = int(mins_match.group(1)) if mins_match else 0
                    total_mins = (hours * 60) + mins
                else:
                    numbers = re.findall(r"\d+", runtime_str)
                    if numbers:
                        total_mins = int(numbers[0])
    except Exception:
        return "N/A"

    if total_mins <= 0: return "N/A"
    if total_mins >= 60:
        hours = total_mins // 60
        mins = total_mins % 60
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
    else:
        return f"{total_mins}m"

async def fetch_imdb_safely(base_name: str, is_series: bool, year: Optional[str] = None) -> dict:
    sig = inspect.signature(get_movie_details)
    kwargs = {}
    if "is_series" in sig.parameters: kwargs["is_series"] = is_series
    elif "media_type" in sig.parameters: kwargs["media_type"] = "tv" if is_series else "movie"

    search_name = re.sub(r'\s+Season\s*\d+', '', base_name, flags=re.IGNORECASE).strip()
    queries = [f"{search_name} {year}".strip() if year else search_name, search_name]

    for q in queries:
        try:
            res = await get_movie_details(q, **kwargs) if kwargs else await get_movie_details(q)
            if res and isinstance(res, dict) and is_good_title_match(search_name, res.get("title", "")):
                return res
        except Exception:
            pass
    return {}

async def fetch_tmdb_safely(tmdb_query: str, base_name: str, is_series: bool) -> dict:
    if not TMDB_POSTER:
        return {}
    sig = inspect.signature(get_movie_detailsx)
    kwargs = {}
    if "is_series" in sig.parameters: kwargs["is_series"] = is_series
    elif "media_type" in sig.parameters: kwargs["media_type"] = "tv" if is_series else "movie"

    if tmdb_query and tmdb_query.startswith("tt"):
        try:
            res = await get_movie_detailsx(tmdb_query, **kwargs) if kwargs else await get_movie_detailsx(tmdb_query)
            if res and not res.get("error"):
                return res
        except Exception:
            pass

    queries = []
    if is_series:
        clean_s = re.sub(r'\s+Season\s*\d+', '', base_name, flags=re.IGNORECASE).strip()
        queries.append(clean_s)
        queries.append(base_name)
    else:
        queries.append(tmdb_query or base_name)
        queries.append(base_name)

    best_fallback = {}
    for q in queries:
        try:
            res = await get_movie_detailsx(q, **kwargs) if kwargs else await get_movie_detailsx(q)
            if res and not res.get("error"):
                title = res.get("title") or res.get("name")
                if title and is_good_title_match(base_name, title):
                    return res
                if not best_fallback:
                    best_fallback = res
        except Exception:
            pass
    return best_fallback

async def search_tmdb_backdrop_force(title: str, year: Optional[str] = None, is_series: bool = False) -> Optional[str]:
    try:
        api_key = TMDB_API_KEY
        if not api_key:
            return None
        clean_q = normalize(re.sub(r'\b(19|20)\d{2}\b', '', title)).strip()
        media_type = "tv" if is_series else "movie"
        url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={api_key}&query={quote_plus(clean_q)}"
        if year and not is_series:
            url += f"&year={year}"

        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("results", []):
                        if item.get("backdrop_path"):
                            return f"https://image.tmdb.org/t/p/original{item['backdrop_path']}"
    except Exception:
        pass
    return None

async def get_hdhub_base_url() -> str:
    try:
        if hasattr(db, 'db'):
            setting = await db.db.settings.find_one({"_id": "hdhub_base_url"})
            if setting and setting.get("url"):
                return setting["url"].rstrip("/")
    except Exception:
        pass
    return DEFAULT_HDHUB_DOMAIN

async def get_blogger_poster_url(base_name: str, year: Optional[str] = None) -> Optional[str]:
    try:
        blog_url = "https://tmdbimdbhdhub4u.blogspot.com"
        feed_url = f"{blog_url}/feeds/posts/default?alt=json&max-results=50"
        timeout = aiohttp.ClientTimeout(total=6)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(feed_url) as resp:
                if resp.status != 200: return None
                data = await resp.json()

        clean_query = f"{normalize(base_name)} {year}".strip() if year else normalize(base_name)
        for entry in data.get("feed", {}).get("entry", []):
            post_title = entry.get("title", {}).get("$t", "")
            if is_good_title_match(clean_query, post_title):
                content_html = entry.get("content", {}).get("$t", "")
                soup = BeautifulSoup(content_html, "html.parser")
                img_tag = soup.find("img")
                if img_tag and img_tag.get("src"):
                    img_url = img_tag["src"]
                    img_url = re.sub(r'/s\d+(-c)?/', '/s1600/', img_url)
                    img_url = re.sub(r'/w\d+-[h\d]+/', '/', img_url)
                    return img_url
    except Exception:
        pass
    return None

async def get_hdhub4u_data(base_name: str) -> Tuple[str, str, str, bool]:
    genres, rating, info_url, is_series = "N/A", "N/A", "", False
    try:
        base_url = await get_hdhub_base_url() or DEFAULT_HDHUB_DOMAIN
        clean_query = normalize(re.sub(r'\b(?:19|20)\d{2}\b', '', base_name)).strip()
        search_words = [w for w in clean_query.split() if len(w) >= 2][:3]
        search_url = f"{base_url.rstrip('/')}/?s={'+'.join(search_words) if search_words else clean_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": base_url
        }

        timeout = aiohttp.ClientTimeout(total=7)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(search_url, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200: return "N/A", "N/A", "", False
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["header", "nav", "footer", "aside", "script", "style", "form"]): tag.decompose()

        candidate_items = []
        for art in soup.select("article, .post-item, .recent-movies li, .entry-title, .thumb"):
            a_tag = art.find("a", href=True)
            if not a_tag: continue
            href = a_tag["href"].strip()
            if not href or href == "#" or any(x in href for x in ["/category/", "/tag/", "/author/", "/page/"]): continue
            if not href.startswith("http"): href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
            candidate_items.append((a_tag.get_text().strip(), href))

        movie_page_url = None
        for title_text, href in candidate_items:
            if is_good_title_match(clean_query, title_text):
                movie_page_url = href
                if re.search(r'\b(?:Season\s*\d+|S\d{1,2}|Series|Episodes?)\b', title_text, re.IGNORECASE): is_series = True
                break

        if not movie_page_url: return "N/A", "N/A", "", False

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(movie_page_url, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200: return "N/A", "N/A", "", is_series
                movie_html = await resp.text()

        movie_soup = BeautifulSoup(movie_html, "html.parser")
        search_area = movie_soup.select_one(".entry-content, .post-content, article") or movie_soup.body or movie_soup

        for a_tag in search_area.find_all("a", href=True):
            href = a_tag["href"].strip()
            m_imdb = re.search(r'imdb\.com/title/(tt\d+)', href, re.IGNORECASE)
            if m_imdb: info_url = f"https://www.imdb.com/title/{m_imdb.group(1)}/"; break
            m_tmdb = re.search(r'themoviedb\.org/(?:movie|tv)/\d+', href, re.IGNORECASE)
            if m_tmdb: info_url = f"https://{m_tmdb.group(0)}" if not m_tmdb.group(0).startswith("http") else m_tmdb.group(0); break

        lines = [re.sub(r'\s+', ' ', line).strip() for line in search_area.get_text().splitlines() if line.strip()]
        for line in lines:
            if not is_series and re.search(r'\b(?:Season|Episodes?)\b\s*[:\-–]', line, re.IGNORECASE): is_series = True
            if rating == "N/A":
                r_match = re.search(r'(?:IMDb|Rating)\s*[:\-•.\s]*\s*([0-9]+(?:\.[0-9]+)?)', line, re.IGNORECASE)
                if r_match: rating = f"{float(r_match.group(1)):.1f}"
            if genres == "N/A":
                g_match = re.search(r'Genre[s]?\s*[:\-–]\s*([^\n\r]+)', line, re.IGNORECASE)
                if g_match:
                    parts = [re.sub(r'\b(?:info|trailer)\b', '', p, flags=re.IGNORECASE).strip().title() for p in re.split(r'[,|/•]', g_match.group(1))]
                    valid_g = [p for p in parts if len(p) >= 2 and not any(bad in p.lower() for bad in ["dropdown", "menu", "select"])]
                    if valid_g: genres = ", ".join(valid_g)
    except Exception:
        pass
    return genres, rating, info_url, is_series

def extract_season_episode(filename: str) -> Tuple[Optional[int], Optional[str]]:
    filename = AUDIO_CHANNELS_PATTERN.sub(" ", filename)
    if m := BONUS_RANGE_REGEX.search(filename): return int(m.group(1)), f"Bonus {int(m.group(2))}-{int(m.group(3))}"
    if m := BONUS_REGEX.search(filename): return int(m.group(1)), f"Bonus {int(m.group(2))}"
    if m := RANGE_REGEX.search(filename): return int(m.group(1)), f"{int(m.group(2))}-{int(m.group(3))}"
    if m := SINGLE_REGEX.search(filename): return int(m.group(1)), str(int(m.group(2)))
    if m := NAMED_REGEX.search(filename): return int(m.group(1)), str(int(m.group(2)))
    if m := X_REGEX.search(filename):
        s_val, ep_val = int(m.group(1)), int(m.group(2))
        if ep_val not in (264, 265, 720, 1080) and s_val not in (264, 265): return s_val, str(ep_val)
    if m := DAY_REGEX.search(filename):
        ep_val = m.group(2) or m.group(3)
        if ep_val: return int(m.group(1)) if m.group(1) else 1, str(int(ep_val))
    if m := NO_S_REGEX.search(filename): return int(m.group(1)), str(int(m.group(2)))
    if m := EP_ONLY_RANGE.search(filename): return 1, f"{int(m.group(1))}-{int(m.group(2))}"
    if m := EP_ONLY_SINGLE.search(filename):
        if int(m.group(1)) not in (264, 265): return 1, str(int(m.group(1)))
    return None, None

def schedule_update(bot, base_name, delay=8):
    if handle := pending_updates.get(base_name):
        if not handle.cancelled(): handle.cancel()
    try: loop = asyncio.get_running_loop()
    except RuntimeError: loop = asyncio.get_event_loop()

    async def wrapper():
        try: await update_movie_message(bot, base_name)
        finally: pending_updates.pop(base_name, None)

    pending_updates[base_name] = loop.call_later(delay, lambda: asyncio.create_task(wrapper()))

def _strip_season_episode_tokens(name: str) -> str:
    if not name: return name
    patterns = [
        r"\bS\d{1,2}[\s._-]*(?:Bonus|Special)[\s._-]*(?:E(?:p(?:isode)?)?)?0*\d{1,3}\b",
        r"\b(?:Bonus|Special)[\s._-]*Ep(?:isode)?\.?\s*\d{1,3}\b",
        r"\bS\d{1,2}E\d{1,3}\b", r"\bS\d{1,2}\b", r"\bE\d{1,3}\b", r"\b\d{1,2}x\d{1,3}\b",
        r"\bSeason\s*\d{1,2}\b", r"\bEp(?:isode)?\.?\s*\d{1,3}\b", r"\bEpisode\s*\d{1,3}\b",
        r"\b[vV]\d+\b", r"\b(?:version|ver)\.?\s*\d+\b",
        r"\b(?:dd|ddp|ac3|eac3|aac)?\s*[257]\s*[._]\s*[01]\b", r"\b(?:dd|ddp)\s*[257]\b",
        r"\b(?:hin|hindi|tam|tamil|tel|telugu|mal|malayalam|kan|kannada|ben|bengali|mar|marathi|guj|gujarati|pun|punjabi|eng|english|kor|korean|jpn|japanese|dual|multi|audio|dubbed)\b",
        r"\b(?:reloaded|uncut)\b",
        r"\b(?:[hH][\s._-]*26[45]|[xX][\s._-]*26[45])\b"
    ]
    for p in patterns: name = re.sub(p, " ", name, flags=re.IGNORECASE)
    return normalize(name).strip()

async def extract_media_info_ai(filename: str, caption: str, duration_mins: Optional[int] = None):
    filename_clean = clean_mentions_links(filename)
    unified = f"{clean_mentions_links(caption).lower()} {filename_clean.lower()}".strip()

    season, episode = extract_season_episode(filename)
    tag = "#SERIES" if season is not None else "#MOVIE"

    quality = get_qualities(caption) or get_qualities(filename) or "N/A"
    ott_platform = extract_ott_platform(unified)

    lang_keys = {k for k in CAPTION_LANGUAGES if re.search(rf"\b{re.escape(k)}\b", unified)}
    language = ", ".join(sorted({CAPTION_LANGUAGES[k] for k in lang_keys})) if lang_keys else "N/A"

    base_raw = AUDIO_CHANNELS_PATTERN.sub(" ", filename_clean)
    prelim_name = remove_ignored_words(_strip_season_episode_tokens(base_raw))
    clean_search = get_clean_title(prelim_name)

    # 1. MongoDB Cache First: Prevent duplicate posts & save quota
    cached_doc = None
    if hasattr(db, "movie_updates"):
        cached_doc = await db.movie_updates.find_one({
            "$or": [{"clean_title": clean_search}, {"_id": clean_search}]
        })

    ai_data = {}
    if not cached_doc and GEMINI_API_KEY:
        ai_data = await identify_movie_with_gemini(filename_clean, caption, duration_mins)

    ai_title = ai_data.get("title")
    ai_year = ai_data.get("year")
    ai_ott = ai_data.get("ott", [])

    if ai_data.get("is_series"):
        tag = "#SERIES"

    year = str(ai_year) if ai_year else None
    if not year:
        year_match = YEAR_PATTERN.search(unified)
        year = year_match.group(0) if year_match else None

    if cached_doc:
        base_name = cached_doc["_id"]
    elif ai_title:
        base_name = normalize(ai_title)
        if year and year not in base_name and tag != "#SERIES":
            base_name = f"{base_name} {year}"
    else:
        base_name = prelim_name
        if year and year not in base_name: base_name = f"{base_name} {year}"

    if season is not None and "Season" not in base_name:
        base_name = f"{base_name} Season {season}"

    if not base_name: base_name = normalize(filename_clean)

    return {
        "processed": normalize(filename_clean),
        "base_name": base_name,
        "tag": tag,
        "season": season,
        "episode": episode,
        "year": year,
        "quality": quality,
        "ott_platform": ott_platform,
        "language": language,
        "ai_ott": ai_ott
    }

async def is_admin_user(user_id):
    if not user_id: return False
    admins_set = {int(a) if str(a).lstrip('-').isdigit() else str(a) for a in ADMINS}
    return (user_id in admins_set) or (str(user_id) in admins_set)

@Client.on_message(filters.command("setdomain"))
async def set_domain_handler(bot, message):
    if not await is_admin_user(message.from_user.id if message.from_user else None): return
    if len(message.command) < 2:
        return await message.reply_text(f"🌐 **Current HDHub4u URL:** <code>{await get_hdhub_base_url()}</code>\n\n💡 **Usage:** <code>/setdomain https://new1.hdhub4u.free</code>")
    raw_url = message.command[1].strip().split("?")[0].rstrip("/")
    if not raw_url.startswith("http"): raw_url = f"https://{raw_url}"
    try:
        await db.db.settings.update_one({"_id": "hdhub_base_url"}, {"$set": {"url": raw_url}}, upsert=True)
        await message.reply_text(f"✅ **HDHub4u base URL successfully updated to:**\n<code>{raw_url}</code>")
    except Exception as e:
        await message.reply_text(f"❌ Failed to update domain: {e}")

@Client.on_message(filters.chat(CHANNELS) & MEDIA_FILTER)
async def media_handler(bot, message):
    media = next((getattr(message, ft) for ft in ("document", "video", "audio") if getattr(message, ft, None)), None)
    if not media: return
    duration_secs = getattr(media, "duration", None) or (message.video.duration if message.video else (message.audio.duration if message.audio else None))
    file_runtime_mins = round(duration_secs / 60) if duration_secs else None

    media.file_type = next(ft for ft in ("document", "video", "audio") if getattr(message, ft, None))
    media.caption = message.caption or ""

    success, info = await save_file(media)
    if not success: return

    try:
        if await db.movie_update_status(bot.me.id):
            await process_and_send_update(bot, media.file_name or message.caption or "Unknown", media.caption, file_runtime_mins)
    except Exception:
        logger.exception("Error processing media")

async def process_and_send_update(bot, filename, caption, file_runtime_mins=None):
    try:
        media_info = await extract_media_info_ai(filename, caption, file_runtime_mins)
        base_name = media_info["base_name"]
        processed = media_info["processed"]

        if not hasattr(db, "movie_updates"): db.movie_updates = db.db.movie_updates

        clean_title = get_clean_title(base_name)
        existing_doc = await db.movie_updates.find_one({"$or": [{"_id": base_name}, {"clean_title": clean_title}]})
        if existing_doc: base_name = existing_doc["_id"]

        lock = locks[base_name]
        async with lock:
            await _process_with_lock(bot, filename, caption, media_info, base_name, processed, file_runtime_mins)
    except Exception as e:
        logger.exception(f"Processing failed in process_and_send_update: {e}")

async def _process_with_lock(bot, filename, caption, media_info, base_name, processed, file_runtime_mins=None):
    if not hasattr(db, "movie_updates"): db.movie_updates = db.db.movie_updates

    clean_title = get_clean_title(base_name)
    movie_doc = await db.movie_updates.find_one({"$or": [{"_id": base_name}, {"clean_title": clean_title}]})
    if movie_doc: base_name = movie_doc["_id"]

    is_series = media_info["tag"] == "#SERIES"
    is_mismatched = False
    if movie_doc:
        stored_title = movie_doc.get("title", "")
        if stored_title and not is_good_title_match(base_name, stored_title): is_mismatched = True

    final_file_runtime = f"{file_runtime_mins}" if file_runtime_mins else "N/A"
    file_data = {
        "filename": filename,
        "processed": processed,
        "quality": media_info["quality"],
        "language": media_info["language"],
        "ott_platform": media_info["ott_platform"],
        "timestamp": datetime.now(),
        "tag": media_info["tag"],
        "season": media_info["season"],
        "episode": media_info["episode"],
        "runtime": final_file_runtime
    }

    if not movie_doc or is_mismatched:
        hdhub_genres, hdhub_rating, hdhub_info_url, hdhub_is_series = await get_hdhub4u_data(base_name)
        if not is_series and hdhub_is_series:
            is_series = True
            media_info["tag"] = "#SERIES"
            file_data["tag"] = "#SERIES"

        tt_match = re.search(r'tt\d+', hdhub_info_url) if hdhub_info_url else None
        hdhub_imdb_id = tt_match.group(0) if tt_match else None

        imdb_details = await fetch_imdb_safely(base_name, is_series=is_series, year=media_info.get("year")) or {}
        official_search_title = imdb_details.get("title") or base_name
        imdb_id = hdhub_imdb_id or imdb_details.get("imdb_id")

        tmdb_query = imdb_id if (imdb_id and imdb_id.startswith("tt")) else official_search_title
        tmdb_details = await fetch_tmdb_safely(tmdb_query, base_name, is_series)

        ott_platform = await fetch_online_ott(imdb_details, tmdb_details, filename, caption, media_info.get("ai_ott"))
        file_data["ott_platform"] = ott_platform

        poster_url = ""
        is_backdrop = False

        blogger_poster = await get_blogger_poster_url(base_name, media_info.get("year"))
        if blogger_poster:
            poster_url = blogger_poster
            is_backdrop = True
        elif tmdb_details.get("backdrop_url"):
            poster_url = tmdb_details["backdrop_url"]
            is_backdrop = True
        else:
            forced_backdrop = await search_tmdb_backdrop_force(official_search_title, media_info.get("year"), is_series)
            if forced_backdrop:
                poster_url = forced_backdrop
                is_backdrop = True
            elif imdb_details.get("backdrop_url"):
                poster_url = imdb_details["backdrop_url"]
                is_backdrop = True
            elif tmdb_details.get("poster_url"):
                poster_url = tmdb_details["poster_url"]
                is_backdrop = False
            else:
                poster_url = imdb_details.get("poster_url", "")
                is_backdrop = False

        tmdb_rate = tmdb_details.get("rating")
        imdb_rate = imdb_details.get("rating")
        if hdhub_rating and hdhub_rating not in ("N/A", "x/10"): rating = hdhub_rating
        elif imdb_rate and str(imdb_rate).strip().upper() not in ("N/A", "NONE", "0", ""): rating = str(imdb_rate).strip()
        elif tmdb_rate and str(tmdb_rate).strip().upper() not in ("N/A", "NONE", "0", ""): rating = str(tmdb_rate).strip()
        else: rating = "6.5"

        imdb_url = hdhub_info_url.strip() if hdhub_info_url else ""
        if not imdb_url:
            final_imdb_id = imdb_details.get("imdb_id") or (tmdb_details.get("imdb_id") if isinstance(tmdb_details, dict) else None) or imdb_id
            if final_imdb_id and str(final_imdb_id).startswith("tt"):
                imdb_url = f"https://www.imdb.com/title/{final_imdb_id}/"
            elif is_series and tmdb_details.get("id"):
                imdb_url = f"https://www.themoviedb.org/tv/{tmdb_details['id']}"
            elif tmdb_details.get("id"):
                imdb_url = f"https://www.themoviedb.org/movie/{tmdb_details['id']}"

        imdb_r = imdb_details.get("runtime")
        tmdb_r = tmdb_details.get("episode_run_time") if is_series and tmdb_details.get("episode_run_time") else tmdb_details.get("runtime")
        if isinstance(imdb_r, (list, tuple)) and imdb_r: imdb_r = imdb_r[0]
        if isinstance(tmdb_r, (list, tuple)) and tmdb_r: tmdb_r = tmdb_r[0]

        if is_series:
            runtime = str(tmdb_r).strip() if (tmdb_r and str(tmdb_r).strip().upper() not in ("N/A", "0")) else (final_file_runtime if final_file_runtime != "N/A" else str(imdb_r or "N/A"))
        else:
            runtime = str(imdb_r).strip() if (imdb_r and str(imdb_r).strip().upper() not in ("N/A", "0")) else (str(tmdb_r).strip() if tmdb_r else final_file_runtime)

        raw_g = tmdb_details.get("genres") or (hdhub_genres if hdhub_genres != "N/A" else imdb_details.get("genres", "Drama"))
        if isinstance(raw_g, list):
            genres = ", ".join([str(x).strip(" '\"") for x in raw_g])
        elif isinstance(raw_g, str):
            clean_g = re.sub(r"[\[\]'\"]", "", raw_g)
            genres = ", ".join([p.strip() for p in clean_g.split(",") if p.strip()])
        else:
            genres = "Drama"

        movie_year = media_info.get("year") or imdb_details.get("year")

        new_doc = {
            "_id": base_name,
            "clean_title": clean_title,
            "title": official_search_title,
            "files": [file_data],
            "poster_url": poster_url,
            "genres": genres,
            "rating": rating,
            "runtime": runtime,
            "imdb_url": imdb_url,
            "year": movie_year,
            "tag": media_info["tag"],
            "ott_platform": ott_platform,
            "message_id": None,
            "is_photo": False,
            "is_backdrop": is_backdrop
        }

        try:
            await db.movie_updates.insert_one(new_doc)
        except DuplicateKeyError:
            await db.movie_updates.update_one({"_id": base_name}, {"$push": {"files": file_data}})
            schedule_update(bot, base_name)
            return

        await send_movie_update(bot, base_name)
    else:
        if any(f.get("filename") == filename for f in movie_doc.get("files", [])): return
        update_fields = {"$push": {"files": file_data}}
        if (not movie_doc.get("runtime") or str(movie_doc.get("runtime")) == "N/A") and final_file_runtime != "N/A":
            update_fields.setdefault("$set", {})["runtime"] = final_file_runtime
        await db.movie_updates.update_one({"_id": base_name}, update_fields)
        schedule_update(bot, base_name)

async def send_movie_update(bot, base_name):
    if base_name in sending_updates: return None
    sending_updates.add(base_name)
    try:
        for _ in range(3):
            try:
                movie_doc = await db.movie_updates.find_one({"_id": base_name})
                if not movie_doc: return None
                if movie_doc.get("message_id"):
                    await update_movie_message(bot, base_name)
                    return None

                text = generate_movie_message(movie_doc, base_name)
                primary_tag = movie_doc.get("tag", "#MOVIE")
                btn_style = enums.ButtonStyle.SUCCESS if primary_tag == "#SERIES" else enums.ButtonStyle.PRIMARY

                match = re.search(r'(.+?)\s+Season\s+(\d+)', base_name, re.IGNORECASE)
                btn_q = f"{match.group(1).strip()}-S{int(match.group(2)):02d}" if match else base_name

                buttons = InlineKeyboardMarkup([[InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇs", url=f"https://t.me/{temp.U_NAME}?start=getfile-{btn_q.replace(' ', '-')}", style=btn_style)]])
                poster_url = movie_doc.get("poster_url")
                is_backdrop = movie_doc.get("is_backdrop", False)
                is_photo, msg = False, None

                if poster_url and not LINK_PREVIEW:
                    try:
                        size = (2560, 1440) if is_backdrop else None
                        photo_to_send = (await fetch_image(poster_url, size)) if size else poster_url
                        msg = await bot.send_photo(chat_id=MOVIE_UPDATE_CHANNEL, photo=photo_to_send or poster_url, caption=text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
                        is_photo = True
                    except Exception:
                        msg = await bot.send_message(chat_id=MOVIE_UPDATE_CHANNEL, text=text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
                else:
                    msg = await bot.send_message(chat_id=MOVIE_UPDATE_CHANNEL, text=text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)

                await db.movie_updates.update_one({"_id": base_name}, {"$set": {"message_id": msg.id, "is_photo": is_photo}})
                return msg
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
            except Exception:
                break
        return None
    finally:
        sending_updates.discard(base_name)

async def update_movie_message(bot, base_name):
    try:
        movie_doc = await db.movie_updates.find_one({"_id": base_name})
        if not movie_doc: return

        text = generate_movie_message(movie_doc, base_name)
        primary_tag = movie_doc.get("tag", "#MOVIE")
        btn_style = enums.ButtonStyle.SUCCESS if primary_tag == "#SERIES" else enums.ButtonStyle.PRIMARY

        match = re.search(r'(.+?)\s+Season\s+(\d+)', base_name, re.IGNORECASE)
        btn_q = f"{match.group(1).strip()}-S{int(match.group(2)):02d}" if match else base_name

        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇs", url=f"https://t.me/{temp.U_NAME}?start=getfile-{btn_q.replace(' ', '-')}", style=btn_style)]])
        message_id = movie_doc.get("message_id")
        is_photo = movie_doc.get("is_photo", False)

        if not message_id:
            await send_movie_update(bot, base_name)
            return

        try:
            if is_photo:
                await bot.edit_message_caption(chat_id=MOVIE_UPDATE_CHANNEL, message_id=message_id, caption=text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
            else:
                await bot.edit_message_text(chat_id=MOVIE_UPDATE_CHANNEL, message_id=message_id, text=text, reply_markup=buttons, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=not LINK_PREVIEW)
        except MessageNotModified:
            pass
        except MessageIdInvalid:
            await db.movie_updates.update_one({"_id": base_name}, {"$set": {"message_id": None}})
            await send_movie_update(bot, base_name)
    except Exception as e:
        logger.error(f"Failed to update movie message: {e}")

def generate_movie_message(movie_doc, base_name):
    all_raw_qualities, all_languages, all_ott_platforms = [], set(), set()
    episodes_by_season = defaultdict(set)
    valid_file_runtimes = []

    for file in movie_doc.get("files", []):
        if file.get("quality") and file.get("quality") != "N/A": all_raw_qualities.append(file["quality"])
        if file.get("language") and file.get("language") != "N/A":
            for lang in file["language"].split(","):
                all_languages.add(CAPTION_LANGUAGES.get(lang.strip().lower(), lang.strip().title()))
        if file.get("ott_platform") and file.get("ott_platform") != "N/A":
            for plat in file["ott_platform"].split("|"):
                all_ott_platforms.add(OTT_PLATFORMS.get(plat.strip().lower(), plat.strip()))
        if file.get("season") is not None and file.get("episode"):
            episodes_by_season[file["season"]].add(str(file["episode"]))
        if file.get("runtime") and str(file["runtime"]).isdigit() and int(file["runtime"]) > 0:
            valid_file_runtimes.append(int(file["runtime"]))

    primary_tag = movie_doc.get("tag", "#MOVIE")
    is_series = (primary_tag == "#SERIES")

    epi_block = ""
    if episodes_by_season:
        episode_lines = []
        for season, episodes in sorted(episodes_by_season.items(), key=lambda x: int(x[0])):
            regular_eps = set()
            for ep in episodes:
                if "-" in ep:
                    try: regular_eps.update(range(int(ep.split("-")[0]), int(ep.split("-")[1]) + 1))
                    except ValueError: pass
                elif ep.isdigit(): regular_eps.add(int(ep))
            sorted_nums = sorted(regular_eps)
            if sorted_nums:
                collapsed = []
                start = end = sorted_nums[0]
                for num in sorted_nums[1:]:
                    if num == end + 1: end = num
                    else: collapsed.append(str(start) if start == end else f"{start}-{end}"); start = end = num
                collapsed.append(str(start) if start == end else f"{start}-{end}")
                episode_lines.append(f"S{int(season)}: {', '.join(collapsed)}")
        if episode_lines: epi_block = f"\n📺 ᴇᴘɪsᴏᴅᴇs : <b>{chr(10).join(episode_lines)}</b>"

    raw_g = movie_doc.get("genres", "Drama")
    if isinstance(raw_g, list):
        genres = ", ".join([str(x).strip(" '\"") for x in raw_g])
    elif isinstance(raw_g, str):
        clean_g = re.sub(r"[\[\]'\"]", "", raw_g)
        genres = ", ".join([p.strip() for p in clean_g.split(",") if p.strip()])
    else:
        genres = "Drama"

    quality_str = format_movie_qualities(all_raw_qualities)
    language_str = ", ".join(sorted(all_languages)) if all_languages else "Hindi"
    ott_str = " | ".join(sorted(all_ott_platforms)) if all_ott_platforms else "N/A"

    raw_rating = str(movie_doc.get("rating", "6.5")).strip()
    clean_rating = raw_rating.split("/")[0].strip() if "/" in raw_rating else (raw_rating if raw_rating not in ("x/10", "x", "N/A", "0") else "6.5")

    raw_runtime = movie_doc.get("runtime", "N/A")
    if not raw_runtime or str(raw_runtime).strip().upper() in ("N/A", "NONE", "0", "-"):
        if is_series and valid_file_runtimes:
            raw_runtime = f"{round(sum(valid_file_runtimes) / len(valid_file_runtimes))}"
        elif not is_series and valid_file_runtimes:
            raw_runtime = f"{valid_file_runtimes[0]}"

    runtime = format_runtime(raw_runtime, is_series=is_series)

    stored_title = movie_doc.get("title", base_name)
    display_title = re.sub(r'[:,]?\s*(?:Episode|Ep)\s*\d+.*|\s+Season\s*\d+|\s+S\d+', '', stored_title, flags=re.IGNORECASE).strip()
    movie_year = movie_doc.get("year")
    filename_display = f"{display_title} {movie_year}".strip() if (movie_year and str(movie_year) not in display_title and not is_series) else display_title

    return script.MOVIE_UPDATE_NOTIFY_TXT.format(
        imdb_url=movie_doc.get("imdb_url") or "https://www.imdb.com",
        filename=filename_display,
        tag=primary_tag,
        genres=genres,
        ott=ott_str,
        runtime=runtime,
        quality=quality_str,
        language=language_str,
        episodes=epi_block,
        rating=clean_rating,
        search_link=temp.B_LINK
    ).strip()
