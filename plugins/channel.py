import re
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

# =========================================================================
# ULTRA COMPREHENSIVE JUNK & IGNORE WORDS LIST
# =========================================================================
_BASE_IGNORE_WORDS = {
    "rarbg", "dub", "sub", "sample", "mkv", "mp4", "avi", "aac", "ac3", "eac3", "ddp", "ddp5", "atmos", "dts",
    "combined", "esub", "msub", "proper", "repack", "unrated", "extended", "imax", "remux", "10bit", "10-bit",
    "x264", "x265", "h264", "h265", "hevc", "avc", "dovi", "hdr", "hdr10", "hdr10+",
    "web", "dl", "bonus", "special", "ott",
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
    "hin": "Hindi", "hindi": "Hindi",
    "tam": "Tamil", "tamil": "Tamil",
    "kan": "Kannada", "kannada": "Kannada",
    "tel": "Telugu", "telugu": "Telugu",
    "mal": "Malayalam", "malayalam": "Malayalam",
    "eng": "English", "english": "English",
    "pun": "Punjabi", "punjabi": "Punjabi",
    "ben": "Bengali", "bengali": "Bengali",
    "mar": "Marathi", "marathi": "Marathi",
    "guj": "Gujarati", "gujarati": "Gujarati",
    "urd": "Urdu", "urdu": "Urdu",
    "kor": "Korean", "korean": "Korean",
    "jpn": "Japanese", "japanese": "Japanese",
    "bho": "Bhojpuri", "bhojpuri": "Bhojpuri",
    "ori": "Odia", "odia": "Odia", "oriya": "Odia",
    "asm": "Assamese", "assamese": "Assamese",
    "spa": "Spanish", "spanish": "Spanish",
    "fre": "French", "french": "French",
    "ger": "German", "german": "German",
    "ita": "Italian", "italian": "Italian",
    "rus": "Russian", "russian": "Russian",
    "chi": "Chinese", "chinese": "Chinese", "zho": "Chinese",
    "tha": "Thai", "thai": "Thai",
    "ind": "Indonesian", "indonesian": "Indonesian",
    "dual": "Dual Audio", "multi": "Multi Audio"
}

OTT_PLATFORMS = {
    "nf": "Netflix", "netflix": "Netflix",
    "sonyliv": "SonyLiv", "sony": "SonyLiv", "sliv": "SonyLiv",
    "amzn": "Amazon Prime Video", "prime": "Amazon Prime Video", "primevideo": "Amazon Prime Video", "amazon": "Amazon Prime Video",
    "hotstar": "Disney+ Hotstar", "disney": "Disney+", "dnp": "Disney+",
    "zee5": "Zee5",
    "jio": "JioHotstar", "jhs": "JioHotstar", "jiocinema": "JioCinema",
    "aha": "Aha", "hbo": "HBO Max", "max": "Max",
    "paramount": "Paramount+",
    "apple": "Apple TV+", "atv": "Apple TV+", "atvp": "Apple TV+", "appletv": "Apple TV+",
    "hoichoi": "Hoichoi", "sunnxt": "Sun NXT", "viki": "Viki",
    "cr": "Crunchyroll", "crunchyroll": "Crunchyroll",
    "hulu": "Hulu", "peacock": "Peacock",
    "lionsgate": "Lionsgate Play", "lionsgateplay": "Lionsgate Play",
    "altbalaji": "ALTT", "alt": "ALTT", "altt": "ALTT",
    "shemaroo": "ShemarooMe", "shemaroome": "ShemarooMe",
    "chaupal": "Chaupal", "stage": "Stage",
    "planetmarathi": "Planet Marathi", "manorama": "ManoramaMAX", "manoramamax": "ManoramaMAX",
    "tubi": "Tubi", "eros": "Eros Now", "erosnow": "Eros Now"
}

STANDARD_FORMATS = {
    "hdtc": "HDTC", "hd-tc": "HDTC", "hq-hdtc": "HQ-HDTC",
    "hdcam": "HDCam", "hd-cam": "HDCam", "hq-hdcam": "HQ-HDCam",
    "cam": "CAM", "camrip": "CamRip", "hq-cam": "HQ-CAM",
    "ts": "TS", "hdts": "HDTS", "hq-ts": "HQ-TS", "tc": "TC",
    "telesync": "TeleSync", "predvd": "PreDVD", "hq-predvd": "HQ-PreDVD",
    "dvdrip": "DVDRip", "dvdscr": "DVDScr",
    "webrip": "WEBRip", "web-dl": "WEB-DL", "webdl": "WEB-DL", "web dl": "WEB-DL",
    "bluray": "BluRay", "brrip": "BRRip", "bdrip": "BDRip",
    "remux": "Remux", "imax": "IMAX",
    "hdrip": "HDRip", "hq-hdrip": "HQ-HDRip",
    "hdtv": "HDTV", "tvrip": "TVRip",
    "hevc": "HEVC", "10bit": "10-Bit", "10-bit": "10-Bit",
    "hdr": "HDR", "hdr10": "HDR10", "hdr10+": "HDR10+",
    "dv": "Dolby Vision", "dovi": "Dolby Vision"
}

RES_ORDER = {
    "140p": 140, "240p": 240, "360p": 360, "480p": 480,
    "540p": 540, "720p": 720, "1080p": 1080, "1440p": 1440,
    "2160p": 2160, "4k": 2160
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
    ignore_words_lower = {w.lower() for w in IGNORE_WORDS}
    return " ".join(word for word in text.split() if word.lower() not in ignore_words_lower)

def is_good_title_match(query: str, found_title: str) -> bool:
    if not query or not found_title:
        return False
    q_raw = YEAR_PATTERN.sub('', query).strip()
    f_raw = YEAR_PATTERN.sub('', found_title).strip()

    def clean_words(s: str):
        s = re.sub(r'\(?\b(?:full\s*movie|full\s*series|full\s*film|hd|rip|dubbed)\b\)?', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^(the|a|an)\s+', '', s, flags=re.IGNORECASE)
        s = re.sub(r"['’]", "", s)
        s = normalize(s).lower()
        return [w for w in s.split() if w and w not in _BASE_IGNORE_WORDS]

    q_words = clean_words(q_raw)
    f_words = clean_words(f_raw)
    if not q_words or not f_words:
        return False
    if q_words == f_words or all(qw in f_words for qw in q_words):
        return True

    for sep in [':', '-', '–', '—', '|']:
        if sep in f_raw:
            main_part = f_raw.split(sep)[0].strip()
            if q_words == clean_words(main_part):
                return True
    return False

def get_qualities(text: str) -> str:
    if not text:
        return "N/A"
    v_match = VERSION_STANDALONE.search(text)
    version_str = None
    if v_match:
        raw_v = v_match.group(0).upper()
        raw_v = re.sub(r'^(?:VER\.?|VERSION)\s*', 'V', raw_v)
        if not raw_v.startswith("V"):
            raw_v = f"V{raw_v}"
        version_str = raw_v

    resolutions = []
    for r in RESOLUTION_PATTERN.findall(text):
        norm_r = r.lower() if r.lower() != "4k" else "4K"
        if norm_r not in resolutions:
            resolutions.append(norm_r)

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
        v_matches = VERSION_STANDALONE.findall(item)
        for vm in v_matches:
            v_num = re.sub(r"\D", "", vm)
            if v_num:
                versions.add(int(v_num))
        for r in RESOLUTION_PATTERN.findall(item):
            norm_r = r.lower() if r.lower() != "4k" else "4K"
            resolutions.add(norm_r)
        for s in SOURCE_PATTERN.findall(item):
            s_norm = re.sub(r"[._]+", "-", s).strip().lower()
            formatted = STANDARD_FORMATS.get(s_norm, s.upper())
            sources.add(formatted)

    if "HQ-HDTC" in sources and "HDTC" in sources:
        sources.remove("HDTC")
    if "HQ-CAM" in sources:
        sources.discard("CAM")
        sources.discard("HDCam")
    if "HDCam" in sources and "CAM" in sources:
        sources.remove("CAM")
    if "HQ-TS" in sources:
        sources.discard("TS")
        sources.discard("HDTS")
    if "HDTS" in sources and "TS" in sources:
        sources.remove("TS")
    if "HQ-PreDVD" in sources and "PreDVD" in sources:
        sources.remove("PreDVD")
    if "HDR10+" in sources:
        sources.discard("HDR10")
        sources.discard("HDR")
    elif "HDR10" in sources:
        sources.discard("HDR")

    sorted_res = sorted(resolutions, key=lambda x: RES_ORDER.get(x.lower(), 9999))
    version_str = f"V{max(versions)}" if versions else ""

    source_list = []
    for s in sorted(sources):
        if s and s not in source_list:
            source_list.append(s)

    if version_str:
        attached = False
        for idx, s in enumerate(source_list):
            if any(k in s.upper() for k in ["HDTC", "CAM", "TS", "PREDVD", "WEBRIP", "WEB-DL", "RIP", "BLURAY"]):
                source_list[idx] = f"{s} {version_str}"
                attached = True
                break
        if not attached:
            sources.append(version_str)

    final_parts = sorted_res + source_list
    return ", ".join(final_parts) if final_parts else "N/A"

def extract_ott_platform(text: str) -> str:
    text = text.lower()
    platforms = {plat for key, plat in OTT_PLATFORMS.items() if re.search(rf"\b{re.escape(key)}\b", text)}
    return " | ".join(sorted(platforms)) if platforms else "N/A"

# =========================================================================
# ULTRA POWERFUL OTT ENGINE (Direct TMDb /watch/providers with Region IN)
# =========================================================================
async def fetch_online_ott(imdb_details: dict, tmdb_details: dict, filename: str, caption: str) -> str:
    platforms = set()

    # 1. Direct TMDb Watch Providers API (Primary & Most Reliable)
    tmdb_id = tmdb_details.get("id") if isinstance(tmdb_details, dict) else None
    media_type = "tv" if (tmdb_details and tmdb_details.get("first_air_date")) else "movie"
    api_key = TMDB_API_KEY

    if tmdb_id and api_key:
        try:
            prov_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/watch/providers?api_key={api_key}"
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(prov_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", {})
                        # Prioritize India (IN), then fallback to US or global
                        reg_data = results.get("IN") or results.get("US") or {}
                        providers = reg_data.get("flatrate", []) + reg_data.get("buy", []) + reg_data.get("rent", [])
                        for p in providers:
                            p_name = p.get("provider_name", "").lower()
                            for key, plat in OTT_PLATFORMS.items():
                                if re.search(rf"\b{re.escape(key)}\b", p_name):
                                    platforms.add(plat)
        except Exception as e:
            logger.warning(f"TMDb watch providers fetch failed: {e}")

    # 2. IMDb Priority
    if not platforms and imdb_details and isinstance(imdb_details, dict):
        raw_ott = f"{imdb_details.get('distributors', '')} {imdb_details.get('ott', '')}".lower()
        for key, plat in OTT_PLATFORMS.items():
            if re.search(rf"\b{re.escape(key)}\b", raw_ott):
                platforms.add(plat)

    # 3. File & Caption Regex Fallback
    if not platforms:
        unified_text = f"{filename} {caption}".lower()
        for key, plat in OTT_PLATFORMS.items():
            if re.search(rf"\b{re.escape(key)}\b", unified_text):
                platforms.add(plat)

    if "Disney+ Hotstar" in platforms and "Disney+" in platforms:
        platforms.discard("Disney+")
    if "JioHotstar" in platforms:
        platforms.discard("Disney+ Hotstar")
        platforms.discard("Disney+")
    if "HBO Max" in platforms and "Max" in platforms:
        platforms.discard("Max")

    return " | ".join(sorted(platforms)) if platforms else "N/A"

def get_clean_title(name: str) -> str:
    t = re.sub(r'\b(19|20)\d{2}\b', '', name)
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

    if total_mins <= 0:
        return "N/A"
    if total_mins >= 60:
        hours = total_mins // 60
        mins = total_mins % 60
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
    else:
        return f"{total_mins}m"

async def fetch_imdb_safely(base_name: str, is_series: bool, year: Optional[str] = None) -> dict:
    sig = inspect.signature(get_movie_details)
    kwargs = {}
    if "is_series" in sig.parameters:
        kwargs["is_series"] = is_series
    elif "media_type" in sig.parameters:
        kwargs["media_type"] = "tv" if is_series else "movie"

    search_name = re.sub(r'\s+Season\s*\d+', '', base_name, flags=re.IGNORECASE).strip() if is_series else base_name
    queries = []
    if is_series:
        if year:
            queries.append(f"{search_name} {year}")
        queries.append(f"{search_name} Series")
        queries.append(f"{search_name} TV")
        queries.append(search_name)
    else:
        if year:
            queries.append(f"{base_name} {year}")
        queries.append(base_name)

    best_fallback = {}
    for q in queries:
        try:
            res = await get_movie_details(q, **kwargs) if kwargs else await get_movie_details(q)
            if res and isinstance(res, dict):
                title = res.get("title")
                if title and is_good_title_match(search_name if is_series else base_name, title):
                    return res
                if not best_fallback and res:
                    best_fallback = res
        except Exception as e:
            logger.warning(f"Error fetching IMDb details for '{q}': {e}")
    return best_fallback

async def fetch_tmdb_safely(tmdb_query: str, base_name: str, is_series: bool) -> dict:
    if not TMDB_POSTER:
        return {}
    sig = inspect.signature(get_movie_detailsx)
    kwargs = {}
    if "is_series" in sig.parameters:
        kwargs["is_series"] = is_series
    elif "media_type" in sig.parameters:
        kwargs["media_type"] = "tv" if is_series else "movie"

    if tmdb_query and tmdb_query.startswith("tt"):
        try:
            res = await get_movie_detailsx(tmdb_query, **kwargs) if kwargs else await get_movie_detailsx(tmdb_query)
            if res and not res.get("error"):
                if res.get("backdrop_url"):
                    return res
        except Exception:
            pass

    queries = []
    if is_series:
        clean_s = re.sub(r'\s+Season\s*\d+', '', base_name, flags=re.IGNORECASE).strip()
        queries.append(clean_s)
        queries.append(f"{clean_s} Series")
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
                    if res.get("backdrop_url"):
                        return res
                    if not best_fallback:
                        best_fallback = res
                elif not best_fallback:
                    best_fallback = res
        except Exception:
            pass
    return best_fallback

async def search_tmdb_backdrop_force(title: str, year: Optional[str] = None, is_series: bool = False) -> Optional[str]:
    """Force hunt for 16:9 Landscape Banner from TMDB."""
    try:
        api_key = TMDB_API_KEY
        if not api_key:
            return None
        clean_q = re.sub(r'\b(19|20)\d{2}\b', '', title)
        clean_q = re.sub(r'\s+Season\s*\d+', '', clean_q, flags=re.IGNORECASE).strip()
        media_type = "tv" if is_series else "movie"
        url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={api_key}&query={quote_plus(clean_q)}"
        if year and not is_series:
            url += f"&year={year}"

        timeout = aiohttp.ClientTimeout(total=6)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        results = data.get("results", [])
        for item in results:
            if item.get("backdrop_path"):
                return f"https://image.tmdb.org/t/p/original{item['backdrop_path']}"
    except Exception as e:
        logger.warning(f"Error in force backdrop search: {e}")
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
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(feed_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        entries = data.get("feed", {}).get("entry", [])
        clean_query = f"{base_name} {year}".strip() if year else base_name
        for entry in entries:
            post_title = entry.get("title", {}).get("$t", "")
            if is_good_title_match(clean_query, post_title) or is_good_title_match(base_name, post_title):
                content_html = entry.get("content", {}).get("$t", "")
                soup = BeautifulSoup(content_html, "html.parser")
                img_tag = soup.find("img")
                if img_tag and img_tag.get("src"):
                    img_url = img_tag["src"]
                    img_url = re.sub(r'/s\d+(-c)?/', '/s1600/', img_url)
                    img_url = re.sub(r'/w\d+-[h\d]+/', '/', img_url)
                    return img_url
    except Exception as e:
        logger.error(f"Error fetching Blogger poster: {e}")
    return None

async def get_hdhub4u_data(base_name: str) -> Tuple[str, str, str, bool]:
    genres = "N/A"
    rating = "N/A"
    info_url = ""
    is_series = False
    try:
        base_url = await get_hdhub_base_url() or DEFAULT_HDHUB_DOMAIN
        clean_search_query = re.sub(r'\b(?:season|s)\s*\d+\b', '', base_name, flags=re.IGNORECASE)
        clean_search_query = re.sub(r'\b(?:19|20)\d{2}\b', '', clean_search_query).strip()
        clean_query = normalize(clean_search_query).strip()

        search_words = [w for w in clean_query.split() if len(w) >= 2][:3]
        effective_query = "+".join(search_words) if search_words else clean_query.replace(" ", "+")
        search_url = f"{base_url.rstrip('/')}/?s={effective_query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": base_url
        }

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(search_url, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200:
                    return "N/A", "N/A", "", False
                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["header", "nav", "footer", "aside", "script", "style", "form"]):
            tag.decompose()

        candidate_items = []
        for art in soup.select("article, .post-item, .recent-movies li, .entry-title, .thumb"):
            a_tag = art.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag["href"].strip()
            if not href or href == "#" or any(x in href for x in ["/category/", "/tag/", "/author/", "/page/", "/wp-content/"]):
                continue
            if not href.startswith("http"):
                href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
            img_alt = art.find("img").get("alt", "") if art.find("img") else ""
            title_text = f"{a_tag.get('title', '')} {a_tag.get_text()} {img_alt}".strip()
            candidate_items.append((title_text, href))

        if not candidate_items:
            for a in soup.select("h2 a, h3 a, .entry-title a, .recent-movies a, a[rel='bookmark']"):
                href = a.get("href", "")
                if href and not any(x in href for x in ["/category/", "/tag/", "/author/", "/page/"]):
                    if not href.startswith("http"):
                        href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                    candidate_items.append((a.get_text().strip(), href))

        movie_page_url = None
        matched_title = ""
        core_tokens = [re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in clean_query.split() if len(w) >= 2]

        for title_text, href in candidate_items:
            clean_cand = normalize(title_text).lower()
            if is_good_title_match(clean_query, title_text) or is_good_title_match(base_name, title_text):
                movie_page_url = href
                matched_title = title_text
                break
            if core_tokens and all(tok in clean_cand for tok in core_tokens):
                movie_page_url = href
                matched_title = title_text
                break

        if not movie_page_url:
            return "N/A", "N/A", "", False

        if re.search(r'\b(?:Season\s*\d+|S\d{1,2}|Series|Episodes?|Complete)\b', matched_title, re.IGNORECASE):
            is_series = True

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(movie_page_url, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200:
                    return "N/A", "N/A", "", is_series
                movie_html = await resp.text()

        movie_soup = BeautifulSoup(movie_html, "html.parser")
        search_area = (
            movie_soup.select_one(".entry-content, .post-content, article, .k-post-content")
            or movie_soup.body
            or movie_soup
        )

        for a_tag in search_area.find_all("a", href=True):
            href = a_tag["href"].strip()
            m_imdb = re.search(r'https?://(?:www\.)?(?:m\.)?imdb\.com/title/(tt\d+)/?', href, re.IGNORECASE) or re.search(r'imdb\.com/title/(tt\d+)', href, re.IGNORECASE)
            if m_imdb:
                info_url = f"https://www.imdb.com/title/{m_imdb.group(1)}/"
                break
            m_tmdb = re.search(r'https?://(?:www\.)?themoviedb\.org/(?:movie|tv)/\d+', href, re.IGNORECASE) or re.search(r'themoviedb\.org/(?:movie|tv)/\d+', href, re.IGNORECASE)
            if m_tmdb:
                info_url = m_tmdb.group(0)
                if not info_url.startswith("http"):
                    info_url = f"https://{info_url}"
                break

        raw_content_str = str(search_area)
        if not info_url:
            m_imdb = re.search(r'https?://(?:www\.)?(?:m\.)?imdb\.com/title/(tt\d+)/?', raw_content_str, re.IGNORECASE)
            if m_imdb:
                info_url = f"https://www.imdb.com/title/{m_imdb.group(1)}/"
            else:
                m_tmdb = re.search(r'https?://(?:www\.)?themoviedb\.org/(?:movie|tv)/\d+', raw_content_str, re.IGNORECASE)
                if m_tmdb:
                    info_url = m_tmdb.group(0)

        for br in movie_soup.find_all(["br", "hr"]):
            br.replace_with("\n")
        for block_elem in movie_soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "li", "tr"]):
            block_elem.append("\n")
        for tag in movie_soup(["header", "nav", "footer", "aside", "script", "style", "iframe"]):
            tag.decompose()

        cat_links = search_area.select(".cat-links a, a[rel='category tag'], .entry-category a, .genres a")
        extracted_categories = []
        for c in cat_links:
            cat_name = c.get_text().strip()
            cat_lower = cat_name.lower()
            if any(term in cat_lower for term in ["web series", "tv shows", "tv series", "series", "k-drama", "anime"]):
                is_series = True
            elif len(cat_name) >= 3 and not any(bad in cat_lower for bad in ["movies", "bollywood", "hollywood", "dual", "hindi", "720p", "480p", "1080p", "hevc"]):
                extracted_categories.append(cat_name.title())

        lines = [re.sub(r'\s+', ' ', line).strip() for line in search_area.get_text().splitlines() if line.strip()]
        for line in lines:
            if not is_series and re.search(r'\b(?:Season|Episodes?|Complete Pack)\b\s*[:\-–]', line, re.IGNORECASE):
                is_series = True
            if rating == "N/A" and re.search(r'\b(?:IMDb|IMDB|Rating|Ratings)\b', line, re.IGNORECASE):
                r_match = re.search(
                    r'(?:IMDb|IMDB|Rating|Ratings)\s*(?:Rating|Ratings)?\s*[:\-•.\s]*\s*([0-9]+(?:\.[0-9]+)?|[xX]|N/?A)',
                    line,
                    re.IGNORECASE
                )
                if r_match:
                    raw_val = r_match.group(1).strip()
                    if raw_val.lower() in ("x", "n/a", "na"):
                        rating = "x/10"
                    else:
                        try:
                            val = float(raw_val)
                            if 0.0 < val <= 10.0:
                                rating = f"{val:.1f}"
                        except ValueError:
                            rating = "x/10"

            if genres == "N/A" and re.search(r'\b(?:Genre|Genres)\b', line, re.IGNORECASE):
                g_match = re.search(r'\b(?:Genre|Genres)\s*[:\-–]\s*([^\n\r]+)', line, re.IGNORECASE)
                if g_match:
                    candidate = g_match.group(1).strip()
                    candidate = re.split(
                        r'\b(?:Release|IMDb|Rating|Language|Audio|Stars|Cast|Director|Quality|Size|Source|Format|Storyline|Info|Trailer|Screenshots?|Plot)\b',
                        candidate,
                        flags=re.IGNORECASE
                    )[0]
                    candidate = re.sub(r'["\'<>{}[\]\\]', '', candidate)
                    parts = re.split(r'[,|/•]', candidate)
                    cleaned_genres = []
                    for p in parts:
                        p_clean = re.sub(r'\b(?:info|trailer)\b', '', p, flags=re.IGNORECASE).strip().title()
                        if p_clean and 2 <= len(p_clean) <= 25 and not any(
                            bad in p_clean.lower() for bad in ["dropdown", "menu", "select", "category", "home", "search", "click", "download"]
                        ):
                            cleaned_genres.append(p_clean)
                    if cleaned_genres:
                        genres = ", ".join(cleaned_genres)

        if genres == "N/A" and extracted_categories:
            genres = ", ".join(extracted_categories[:4])

    except Exception as e:
        logger.error(f"Error scraping HDHub4u data: {e}")
    return genres, rating, info_url, is_series

def extract_season_episode(filename: str) -> Tuple[Optional[int], Optional[str]]:
    filename = AUDIO_CHANNELS_PATTERN.sub(" ", filename)
    if m := BONUS_RANGE_REGEX.search(filename):
        return int(m.group(1)), f"Bonus {int(m.group(2))}-{int(m.group(3))}"
    if m := BONUS_REGEX.search(filename):
        return int(m.group(1)), f"Bonus {int(m.group(2))}"
    if m := RANGE_REGEX.search(filename):
        return int(m.group(1)), f"{int(m.group(2))}-{int(m.group(3))}"
    if m := SINGLE_REGEX.search(filename):
        return int(m.group(1)), str(int(m.group(2)))
    if m := NAMED_REGEX.search(filename):
        return int(m.group(1)), str(int(m.group(2)))
    if m := X_REGEX.search(filename):
        s_val = int(m.group(1))
        ep_val = int(m.group(2))
        if ep_val not in (264, 265, 720, 1080, 480) and s_val not in (264, 265, 720, 1080):
            return s_val, str(ep_val)
    if m := DAY_REGEX.search(filename):
        season = int(m.group(1)) if m.group(1) else 1
        ep_val = m.group(2) or m.group(3)
        if ep_val:
            return season, str(int(ep_val))
    if m := NO_S_REGEX.search(filename):
        return int(m.group(1)), str(int(m.group(2)))
    if m := EP_ONLY_RANGE.search(filename):
        return 1, f"{int(m.group(1))}-{int(m.group(2))}"
    if m := EP_ONLY_SINGLE.search(filename):
        ep_val = int(m.group(1))
        if ep_val not in (264, 265):
            return 1, str(ep_val)
    return None, None

def schedule_update(bot, base_name, delay=8):
    if handle := pending_updates.get(base_name):
        if not handle.cancelled():
            handle.cancel()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()

    async def wrapper():
        try:
            await update_movie_message(bot, base_name)
        finally:
            pending_updates.pop(base_name, None)

    pending_updates[base_name] = loop.call_later(
        delay,
        lambda: asyncio.create_task(wrapper())
    )

def _strip_season_episode_tokens(name: str) -> str:
    if not name:
        return name
    year_match = re.search(r"\(?\b(19|20)\d{2}\b\)?\s*$", name)
    year_part = ""
    if year_match:
        year_part = year_match.group(0)
        name = name[:year_match.start()].strip()

    patterns = [
        r"\bS\d{1,2}[\s._-]*(?:Bonus|Special)[\s._-]*(?:E(?:p(?:isode)?)?)?0*\d{1,3}\b",
        r"\b(?:Bonus|Special)[\s._-]*Ep(?:isode)?\.?\s*\d{1,3}\b",
        r"\bS\d{1,2}E\d{1,3}\b", r"\bS\d{1,2}\b", r"\bE\d{1,3}\b", r"\b\d{1,2}x\d{1,3}\b",
        r"\bSeason\s*\d{1,2}\b", r"\bEp(?:isode)?\.?\s*\d{1,3}\b", r"\bEpisode\s*\d{1,3}\b",
        r"\bPart\s*\d{1,2}\b", r"\bDay\s*\d{1,3}\b", r"\bBonus\b", r"\bSpecial\b",
        r"\b[vV]\d+\b", r"\b(?:version|ver)\.?\s*\d+\b",
        r"\b(?:dd|ddp|ac3|eac3|aac)?\s*[257]\s*[._]\s*[01]\b", r"\b(?:dd|ddp)\s*[257]\b",
        r"\b(?:hin|hindi|tam|tamil|tel|telugu|mal|malayalam|kan|kannada|ben|bengali|mar|marathi|guj|gujarati|pun|punjabi|eng|english|kor|korean|jpn|japanese|dual|multi|audio|dubbed)\b"
    ]
    for p in patterns:
        name = re.sub(p, " ", name, flags=re.IGNORECASE)

    name = re.sub(r"[_\.\-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    if year_part:
        y = re.search(r"(19|20)\d{2}", year_part)
        if y:
            name = f"{name} {y.group(0)}"
    return name.strip()

def extract_media_info(filename: str, caption: str):
    filename_clean = clean_mentions_links(filename)
    filename = normalize(filename_clean.title())
    caption_clean = clean_mentions_links(caption).lower() if caption else ""
    unified = f"{caption_clean} {filename.lower()}".strip()

    season = None
    episode = None
    year = None
    tag = "#MOVIE"

    processed_raw = filename
    base_raw = filename

    quality = get_qualities(caption) or get_qualities(filename) or "N/A"
    ott_platform = extract_ott_platform(f"{filename} {caption_clean}")

    lang_keys = {k for k in CAPTION_LANGUAGES if re.search(rf"\b{re.escape(k)}\b", unified)}
    language = ", ".join(sorted({CAPTION_LANGUAGES[k] for k in lang_keys})) if lang_keys else "N/A"

    season, episode = extract_season_episode(filename)
    if season is not None:
        tag = "#SERIES"
        clean_fn = AUDIO_CHANNELS_PATTERN.sub(" ", filename)
        m = (
            BONUS_RANGE_REGEX.search(clean_fn)
            or BONUS_REGEX.search(clean_fn)
            or RANGE_REGEX.search(clean_fn)
            or SINGLE_REGEX.search(clean_fn)
            or NAMED_REGEX.search(clean_fn)
            or X_REGEX.search(clean_fn)
            or DAY_REGEX.search(clean_fn)
            or NO_S_REGEX.search(clean_fn)
            or EP_ONLY_RANGE.search(clean_fn)
            or EP_ONLY_SINGLE.search(clean_fn)
        )
        if m:
            match_str = m.group(0)
            start_idx = clean_fn.lower().find(match_str.lower())
            end_idx = start_idx + len(match_str)
            processed_raw = filename[:end_idx]
            base_raw = filename[:start_idx]
            year_match = YEAR_PATTERN.search(filename.lower()[end_idx:])
            if year_match:
                y = year_match.group(0)
                yi = filename.lower().find(y, end_idx)
                if yi != -1:
                    processed_raw = filename[:yi + 4]
                    base_raw += f" {y}"
    else:
        year_match = YEAR_PATTERN.search(unified)
        if year_match:
            year = year_match.group(0)
            year_idx = filename.lower().find(year.lower())
            if year_idx != -1:
                processed_raw = filename[:year_idx + 4]
                base_raw = processed_raw
        else:
            qual_match = SOURCE_PATTERN.search(unified) or RESOLUTION_PATTERN.search(unified)
            if qual_match:
                qual_str = qual_match.group(0)
                qual_idx = filename.lower().find(qual_str.lower())
                if qual_idx != -1:
                    processed_raw = filename[:qual_idx]
                    base_raw = processed_raw

    base_raw = AUDIO_CHANNELS_PATTERN.sub(" ", base_raw)
    base_name = normalize(remove_ignored_words(normalize(base_raw)))

    if year and year not in base_name:
        base_name += f" {year}"
    if base_name.endswith(")"):
        base_name = re.sub(r"\s+\(\d{4}\)$", "", base_name)
        if year:
            base_name += f" {year}"

    base_name = _strip_season_episode_tokens(base_name)
    base_name = re.sub(r'(\b(?:19|20)\d{2}\b)(?:\s+\1)+', r'\1', base_name).strip()

    if season is not None:
        base_name = f"{base_name} Season {season}"

    if not base_name:
        base_name = normalize(remove_ignored_words(normalize(processed_raw))) or filename

    return {
        "processed": normalize(processed_raw),
        "base_name": base_name,
        "tag": tag,
        "season": season,
        "episode": episode,
        "year": year,
        "quality": quality,
        "ott_platform": ott_platform,
        "language": language
    }

async def is_admin_user(user_id):
    if not user_id:
        return False
    admins_set = {int(a) if str(a).lstrip('-').isdigit() else str(a) for a in ADMINS}
    return (user_id in admins_set) or (str(user_id) in admins_set)

@Client.on_message(filters.command("setdomain"))
async def set_domain_handler(bot, message):
    user_id = message.from_user.id if message.from_user else None
    if not await is_admin_user(user_id):
        return

    if len(message.command) < 2:
        current_url = await get_hdhub_base_url()
        return await message.reply_text(
            f"🌐 **Current HDHub4u URL:** <code>{current_url}</code>\n\n"
            f"💡 **Usage:** <code>/setdomain https://new1.hdhub4u.free</code>"
        )
    raw_url = message.command[1].strip().split("?")[0].rstrip("/")
    if not raw_url.startswith("http"):
        raw_url = f"https://{raw_url}"
    try:
        if hasattr(db, 'db'):
            await db.db.settings.update_one(
                {"_id": "hdhub_base_url"},
                {"$set": {"url": raw_url}},
                upsert=True
            )
            await message.reply_text(f"✅ **HDHub4u base URL successfully updated to:**\n<code>{raw_url}</code>")
        else:
            await message.reply_text("❌ Database not initialized.")
    except Exception as e:
        await message.reply_text(f"❌ Failed to update domain: {e}")

@Client.on_message(filters.chat(CHANNELS) & MEDIA_FILTER)
async def media_handler(bot, message):
    media = next((getattr(message, ft) for ft in ("document", "video", "audio") if getattr(message, ft, None)), None)
    if not media:
        return

    duration_secs = getattr(media, "duration", None) or (message.video.duration if message.video else (message.audio.duration if message.audio else None))
    file_runtime_mins = round(duration_secs / 60) if duration_secs else None

    media.file_type = next(ft for ft in ("document", "video", "audio") if getattr(message, ft, None))
    media.caption = message.caption or ""

    success, info = await save_file(media)
    if not success:
        return

    try:
        if await db.movie_update_status(bot.me.id):
            await process_and_send_update(
                bot,
                media.file_name or message.caption or "Unknown",
                media.caption,
                file_runtime_mins
            )
    except Exception:
        logger.exception("Error processing media")

async def process_and_send_update(bot, filename, caption, file_runtime_mins=None):
    try:
        media_info = extract_media_info(filename, caption)
        base_name = media_info["base_name"]
        processed = media_info["processed"]

        if not hasattr(db, "movie_updates"):
            db.movie_updates = db.db.movie_updates

        clean_title = get_clean_title(base_name)
        existing_doc = await db.movie_updates.find_one({
            "$or": [{"_id": base_name}, {"clean_title": clean_title}]
        })
        if existing_doc:
            base_name = existing_doc["_id"]

        lock = locks[base_name]
        async with lock:
            await _process_with_lock(bot, filename, caption, media_info, base_name, processed, file_runtime_mins)
    except PyMongoError as e:
        logger.error(f"Database error in process_and_send_update: {e}")
    except Exception as e:
        logger.exception(f"Processing failed in process_and_send_update: {e}")

async def _process_with_lock(bot, filename, caption, media_info, base_name, processed, file_runtime_mins=None):
    if not hasattr(db, "movie_updates"):
        db.movie_updates = db.db.movie_updates

    clean_title = get_clean_title(base_name)
    movie_doc = await db.movie_updates.find_one({"_id": base_name})
    if not movie_doc:
        movie_doc = await db.movie_updates.find_one({"clean_title": clean_title})
        if movie_doc:
            base_name = movie_doc["_id"]

    is_series = media_info["tag"] == "#SERIES"
    is_mismatched = False
    if movie_doc:
        stored_title = movie_doc.get("title", "")
        if stored_title and not is_good_title_match(base_name, stored_title):
            is_mismatched = True

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
        if not imdb_details or not is_good_title_match(base_name, imdb_details.get("title", "")):
            imdb_id = hdhub_imdb_id
            official_search_title = base_name
        else:
            official_search_title = imdb_details.get("title", base_name)
            imdb_id = hdhub_imdb_id or imdb_details.get("imdb_id")

        tmdb_query = imdb_id if (imdb_id and imdb_id.startswith("tt")) else official_search_title
        tmdb_details = await fetch_tmdb_safely(tmdb_query, base_name, is_series)

        # OTT ENGINE CALL
        ott_platform = await fetch_online_ott(imdb_details, tmdb_details, filename, caption)
        file_data["ott_platform"] = ott_platform

        # STRICT 16:9 LANDSCAPE BANNER DISCOVERY PIPELINE
        poster_url = ""
        is_backdrop = False

        blogger_poster = await get_blogger_poster_url(base_name, media_info.get("year"))
        if blogger_poster:
            poster_url = blogger_poster
            is_backdrop = True
        elif TMDB_POSTER and tmdb_details.get("backdrop_url"):
            poster_url = tmdb_details.get("backdrop_url")
            is_backdrop = True
        else:
            forced_backdrop = await search_tmdb_backdrop_force(official_search_title, media_info.get("year"), is_series)
            if forced_backdrop:
                poster_url = forced_backdrop
                is_backdrop = True
            elif imdb_details.get("backdrop_url"):
                poster_url = imdb_details.get("backdrop_url")
                is_backdrop = True
            elif tmdb_details.get("poster_url"):
                poster_url = tmdb_details.get("poster_url")
                is_backdrop = False
            else:
                poster_url = imdb_details.get("poster_url", "")
                is_backdrop = False

        imdb_rate = imdb_details.get("rating")
        tmdb_rate = tmdb_details.get("rating")
        if hdhub_rating and hdhub_rating != "N/A" and hdhub_rating != "x/10":
            rating = hdhub_rating
        elif imdb_rate and str(imdb_rate).strip().upper() not in ("N/A", "NONE", "0", "0.0", "-", ""):
            rating = str(imdb_rate).strip()
        elif tmdb_rate and str(tmdb_rate).strip().upper() not in ("N/A", "NONE", "0", "0.0", "-", ""):
            rating = str(tmdb_rate).strip()
        else:
            rating = "6.5"

        imdb_url = hdhub_info_url.strip() if hdhub_info_url else ""
        if not imdb_url:
            final_imdb_id = imdb_details.get("imdb_id") or (tmdb_details.get("imdb_id") if isinstance(tmdb_details, dict) else None) or imdb_id
            if final_imdb_id and str(final_imdb_id).startswith("tt"):
                imdb_url = f"https://www.imdb.com/title/{final_imdb_id}/"
            elif is_series and tmdb_details.get("id"):
                imdb_url = f"https://www.themoviedb.org/tv/{tmdb_details.get('id')}"
            elif tmdb_details.get("id"):
                imdb_url = f"https://www.themoviedb.org/movie/{tmdb_details.get('id')}"

        # RUNTIME: IMDb -> TMDb -> File Runtime Fallback
        imdb_r = imdb_details.get("runtime")
        tmdb_r = tmdb_details.get("episode_run_time") if is_series and tmdb_details.get("episode_run_time") else tmdb_details.get("runtime")
        if isinstance(imdb_r, (list, tuple)) and imdb_r:
            imdb_r = imdb_r[0]
        if isinstance(tmdb_r, (list, tuple)) and tmdb_r:
            tmdb_r = tmdb_r[0]

        if is_series:
            if tmdb_r and str(tmdb_r).strip().upper() not in ("N/A", "NONE", "0", ""):
                runtime = str(tmdb_r).strip()
            elif imdb_r and str(imdb_r).strip().upper() not in ("N/A", "NONE", "0", ""):
                runtime = str(imdb_r).strip()
            elif final_file_runtime != "N/A":
                runtime = final_file_runtime
            else:
                runtime = "N/A"
        else:
            if imdb_r and str(imdb_r).strip().upper() not in ("N/A", "NONE", "0", ""):
                runtime = str(imdb_r).strip()
            elif tmdb_r and str(tmdb_r).strip().upper() not in ("N/A", "NONE", "0", ""):
                runtime = str(tmdb_r).strip()
            elif final_file_runtime != "N/A":
                runtime = final_file_runtime
            else:
                runtime = "N/A"

        certificates = tmdb_details.get("certificates") if tmdb_details.get("certificates") and tmdb_details.get("certificates") != "N/A" else imdb_details.get("certificates", "N/A")

        genre_list = []
        if hdhub_genres and hdhub_genres != "N/A":
            raw_parts = re.split(r'[,|/•]', hdhub_genres)
            for p in raw_parts:
                p_clean = re.sub(r'\b(?:info|trailer)\b', '', p, flags=re.IGNORECASE).strip()
                if p_clean and p_clean != "N/A" and not any(bad in p_clean.lower() for bad in ["dropdown", "menu", "select", "category"]):
                    genre_list.append(p_clean.title())
        if not genre_list:
            raw_genres = imdb_details.get("genres") or tmdb_details.get("genres", "N/A")
            if isinstance(raw_genres, str) and raw_genres != "N/A":
                genre_list = [g.strip().title() for g in raw_genres.split(",") if g.strip()]

        genres = ", ".join(genre_list[:4]) if genre_list else "N/A"
        movie_year = media_info.get("year") or imdb_details.get("year") or tmdb_details.get("year")

        if is_mismatched:
            update_data = {
                "title": official_search_title,
                "clean_title": clean_title,
                "poster_url": poster_url,
                "genres": genres,
                "rating": rating,
                "runtime": runtime,
                "certificates": certificates,
                "imdb_url": imdb_url,
                "year": movie_year,
                "tag": media_info["tag"],
                "ott_platform": ott_platform,
                "is_backdrop": is_backdrop
            }
            await db.movie_updates.update_one({"_id": base_name}, {"$set": update_data, "$push": {"files": file_data}})
            schedule_update(bot, base_name)
            return

        new_doc = {
            "_id": base_name,
            "clean_title": clean_title,
            "title": official_search_title,
            "files": [file_data],
            "poster_url": poster_url,
            "genres": genres,
            "rating": rating,
            "runtime": runtime,
            "certificates": certificates,
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
            movie_doc = await db.movie_updates.find_one({"_id": base_name})
            if not movie_doc or any(f.get("filename") == filename for f in movie_doc.get("files", [])):
                return
            await db.movie_updates.update_one({"_id": base_name}, {"$push": {"files": file_data}})
            schedule_update(bot, base_name)
            return

        await send_movie_update(bot, base_name)
    else:
        if any(f.get("filename") == filename for f in movie_doc.get("files", [])):
            return

        update_fields = {"$push": {"files": file_data}}
        current_db_runtime = movie_doc.get("runtime")
        if (not current_db_runtime or str(current_db_runtime).strip().upper() in ("N/A", "NONE", "0", "")) and final_file_runtime != "N/A":
            update_fields.setdefault("$set", {})["runtime"] = final_file_runtime

        await db.movie_updates.update_one({"_id": base_name}, update_fields)
        schedule_update(bot, base_name)

async def send_movie_update(bot, base_name):
    if base_name in sending_updates:
        return None
    sending_updates.add(base_name)

    try:
        for attempt in range(3):
            try:
                movie_doc = await db.movie_updates.find_one({"_id": base_name})
                if not movie_doc:
                    return None

                if movie_doc.get("message_id"):
                    await update_movie_message(bot, base_name)
                    return None

                text = generate_movie_message(movie_doc, base_name)
                all_tags = {f.get("tag") for f in movie_doc.get("files", []) if f.get("tag")}
                primary_tag = "#SERIES" if "#SERIES" in all_tags else "#MOVIE"

                # Button Style: Movie -> Blue (PRIMARY), Series -> Green (SUCCESS)
                btn_style = enums.ButtonStyle.SUCCESS if primary_tag == "#SERIES" else enums.ButtonStyle.PRIMARY

                match = re.search(r'(.+?)\s+Season\s+(\d+)', base_name, re.IGNORECASE)
                if match:
                    button_query = f"{match.group(1).strip()}-S{int(match.group(2)):02d}"
                else:
                    button_query = base_name

                buttons = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "ɢᴇᴛ ғɪʟᴇs",
                        url=f"https://t.me/{temp.U_NAME}?start=getfile-{button_query.replace(' ', '-')}",
                        style=btn_style
                    )
                ]])

                poster_url = movie_doc.get("poster_url")
                is_backdrop = movie_doc.get("is_backdrop", False)
                is_photo = False
                msg = None

                if poster_url and not LINK_PREVIEW:
                    try:
                        if is_backdrop:
                            size = (2560, 1440)
                            resized_poster = await fetch_image(poster_url, size)
                            photo_to_send = resized_poster or poster_url
                        else:
                            photo_to_send = poster_url

                        msg = await bot.send_photo(
                            chat_id=MOVIE_UPDATE_CHANNEL,
                            photo=photo_to_send,
                            caption=text,
                            reply_markup=buttons,
                            parse_mode=enums.ParseMode.HTML
                        )
                        is_photo = True
                    except Exception:
                        msg = await bot.send_message(
                            chat_id=MOVIE_UPDATE_CHANNEL,
                            text=text,
                            reply_markup=buttons,
                            parse_mode=enums.ParseMode.HTML
                        )
                        is_photo = False
                else:
                    msg = await bot.send_message(
                        chat_id=MOVIE_UPDATE_CHANNEL,
                        text=text,
                        reply_markup=buttons,
                        parse_mode=enums.ParseMode.HTML
                    )
                    is_photo = False

                await db.movie_updates.update_one(
                    {"_id": base_name, "message_id": None},
                    {"$set": {"message_id": msg.id, "is_photo": is_photo}}
                )
                return msg

            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
            except Exception as e:
                logger.error(f"Failed to send movie update: {e}")
                break
        return None
    finally:
        sending_updates.discard(base_name)

async def update_movie_message(bot, base_name):
    try:
        movie_doc = await db.movie_updates.find_one({"_id": base_name})
        if not movie_doc:
            return

        text = generate_movie_message(movie_doc, base_name)
        all_tags = {f.get("tag") for f in movie_doc.get("files", []) if f.get("tag")}
        primary_tag = "#SERIES" if "#SERIES" in all_tags else "#MOVIE"

        # Button Style: Movie -> Blue (PRIMARY), Series -> Green (SUCCESS)
        btn_style = enums.ButtonStyle.SUCCESS if primary_tag == "#SERIES" else enums.ButtonStyle.PRIMARY

        match = re.search(r'(.+?)\s+Season\s+(\d+)', base_name, re.IGNORECASE)
        if match:
            button_query = f"{match.group(1).strip()}-S{int(match.group(2)):02d}"
        else:
            button_query = base_name

        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "ɢᴇᴛ ғɪʟᴇs",
                url=f"https://t.me/{temp.U_NAME}?start=getfile-{button_query.replace(' ', '-')}",
                style=btn_style
            )
        ]])

        message_id = movie_doc.get("message_id")
        is_photo = movie_doc.get("is_photo", False)

        if not message_id:
            await send_movie_update(bot, base_name)
            return

        try:
            if is_photo:
                await bot.edit_message_caption(
                    chat_id=MOVIE_UPDATE_CHANNEL,
                    message_id=message_id,
                    caption=text,
                    reply_markup=buttons,
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                await bot.edit_message_text(
                    chat_id=MOVIE_UPDATE_CHANNEL,
                    message_id=message_id,
                    text=text,
                    reply_markup=buttons,
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=not LINK_PREVIEW
                )
        except MessageNotModified:
            pass
        except MessageIdInvalid:
            await db.movie_updates.update_one({"_id": base_name}, {"$set": {"message_id": None}})
            await send_movie_update(bot, base_name)
        except Exception as e:
            logger.error(f"Error updating movie message: {e}")
    except Exception as e:
        logger.error(f"Failed to update movie message for {base_name}: {e}")

def generate_movie_message(movie_doc, base_name):
    all_raw_qualities = []
    all_languages = set()
    all_ott_platforms = set()
    all_tags = set()
    episodes_by_season = defaultdict(set)
    valid_file_runtimes = []

    for file in movie_doc.get("files", []):
        if file.get("quality") and file.get("quality") != "N/A":
            all_raw_qualities.append(file.get("quality"))

        lang_val = file.get("language")
        if lang_val and lang_val != "N/A":
            for lang in lang_val.split(","):
                clean_l = lang.strip()
                if clean_l and clean_l != "N/A":
                    all_languages.add(CAPTION_LANGUAGES.get(clean_l.lower(), clean_l.title()))

        ott_val = file.get("ott_platform")
        if ott_val and ott_val != "N/A":
            for plat in ott_val.split("|"):
                clean_p = plat.strip()
                if clean_p and clean_p != "N/A":
                    all_ott_platforms.add(OTT_PLATFORMS.get(clean_p.lower(), clean_p))

        if file.get("tag"):
            all_tags.add(file.get("tag"))

        if file.get("season") is not None and file.get("episode"):
            season = file.get("season")
            episode = str(file.get("episode"))
            episodes_by_season[season].add(episode)

        r_val = file.get("runtime")
        if r_val and str(r_val).isdigit() and int(r_val) > 0:
            valid_file_runtimes.append(int(r_val))

    primary_tag = "#SERIES" if "#SERIES" in all_tags else "#MOVIE"
    is_series = (primary_tag == "#SERIES")

    epi_block = ""
    if episodes_by_season:
        episode_lines = []
        for season, episodes in sorted(episodes_by_season.items(), key=lambda x: int(x[0])):
            regular_eps = set()
            for ep in episodes:
                ep_str = str(ep).strip()
                if "-" in ep_str:
                    try:
                        p1, p2 = ep_str.split("-")
                        regular_eps.update(range(int(p1), int(p2) + 1))
                    except ValueError:
                        pass
                elif ep_str.isdigit():
                    regular_eps.add(int(ep_str))

            sorted_nums = sorted(regular_eps)
            if sorted_nums:
                collapsed = []
                start = end = sorted_nums[0]
                for num in sorted_nums[1:]:
                    if num == end + 1:
                        end = num
                    else:
                        collapsed.append(str(start) if start == end else f"{start}-{end}")
                        start = end = num
                collapsed.append(str(start) if start == end else f"{start}-{end}")
                episode_lines.append(f"S{int(season)}: {', '.join(collapsed)}")

        epi_str = "\n".join(episode_lines)
        if epi_str:
            epi_block = f"\n📺 ᴇᴘɪsᴏᴅᴇs : <b>{epi_str}</b>"

    genres = movie_doc.get("genres", "Drama")
    quality_str = format_movie_qualities(all_raw_qualities)
    language_str = ", ".join(sorted(all_languages)) if all_languages else "Hindi"
    ott_str = " | ".join(sorted(all_ott_platforms)) if all_ott_platforms else "N/A"

    raw_rating = str(movie_doc.get("rating", "6.5")).strip()
    if "/" in raw_rating:
        clean_rating = raw_rating.split("/")[0].strip()
    else:
        clean_rating = raw_rating if raw_rating not in ("x/10", "x", "N/A", "0") else "6.5"

    raw_runtime = movie_doc.get("runtime", "N/A")
    if not raw_runtime or str(raw_runtime).strip().upper() in ("N/A", "NONE", "0", "-"):
        if is_series and valid_file_runtimes:
            avg_rt = round(sum(valid_file_runtimes) / len(valid_file_runtimes))
            raw_runtime = f"{avg_rt}"
        elif not is_series and valid_file_runtimes:
            raw_runtime = f"{valid_file_runtimes[0]}"

    runtime = format_runtime(raw_runtime, is_series=is_series)

    stored_title = movie_doc.get("title", base_name)
    stored_title = re.sub(r'[:,]?\s*(?:Episode|Ep)\s*\d+.*', '', stored_title, flags=re.IGNORECASE).strip()
    clean_series_title = re.sub(r'\s+Season\s*\d+', '', stored_title, flags=re.IGNORECASE).strip()
    clean_series_title = re.sub(r'\s+S\d+', '', clean_series_title, flags=re.IGNORECASE).strip(" :,-\"'")

    movie_year = movie_doc.get("year")
    if movie_year and str(movie_year) not in str(clean_series_title) and primary_tag != "#SERIES":
        filename_display = f"{clean_series_title} {movie_year}"
    else:
        filename_display = clean_series_title

    imdb_url = movie_doc.get("imdb_url") or "https://www.imdb.com"

    return script.MOVIE_UPDATE_NOTIFY_TXT.format(
        imdb_url=imdb_url,
        filename=filename_display,
        tag=f"{primary_tag}",
        genres=genres,
        ott=ott_str,
        runtime=runtime,
        quality=quality_str,
        language=language_str,
        episodes=epi_block,
        rating=clean_rating,
        search_link=temp.B_LINK
    ).strip()
