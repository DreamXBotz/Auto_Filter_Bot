import re
import logging
import asyncio
import aiohttp
from datetime import datetime
from collections import defaultdict
from bs4 import BeautifulSoup
from plugins.Dreamxfutures.Imdbposter import get_movie_detailsx, fetch_image, get_movie_details, get_blogger_poster_url, get_posterflix_poster, get_hdhub4u_data
from database.users_chats_db import db
from pyrogram import Client, filters, enums
from info import CHANNELS, MOVIE_UPDATE_CHANNEL, LINK_PREVIEW, ABOVE_PREVIEW, BAD_WORDS, LANDSCAPE_POSTER, TMDB_POSTER
from Script import script
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
try:
    from pyrogram.types import KeyboardButtonStyle
    HAS_STYLED = True
except ImportError:
    KeyboardButtonStyle = None
    HAS_STYLED = False
from utils import temp
from pymongo.errors import PyMongoError, DuplicateKeyError
from pyrogram.errors import MessageIdInvalid, MessageNotModified, FloodWait
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# === ORIGINAL IGNORE WORDS (kept exactly) ===
IGNORE_WORDS_ORIG = {
    "rarbg", "dub", "sub", "sample", "mkv", "aac", "combined",
    "action", "adventure", "animation", "biography", "comedy", "crime", 
    "documentary", "drama", "fantasy", "film-noir", "history", 
    "horror", "music", "musical", "mystery", "romance", "sci-fi", "sport", 
    "thriller", "war", "western", "hdcam", "hdtc", "camrip", "ts", "tc", 
    "telesync", "dvdscr", "dvdrip", "predvd", "webrip", "web-dl", "tvrip", 
    "hdtv", "web dl", "webdl", "bluray", "brrip", "bdrip", "360p", "480p", 
    "720p", "1080p", "2160p", "4k", "1440p", "540p", "240p", "140p", "hevc", 
    "hdrip", "hin", "hindi", "tam", "tamil", "kan", "kannada", "tel", "telugu", 
    "mal", "malayalam", "eng", "english", "pun", "punjabi", "ben", "bengali", 
    "mar", "marathi", "guj", "gujarati", "urd", "urdu", "kor", "korean", "jpn", 
    "japanese", "nf", "netflix", "sonyliv", "sony", "sliv", "amzn", "prime", 
    "primevideo", "hotstar", "zee5", "jio", "jhs", "aha", "hbo", "paramount", 
    "apple", "hoichoi", "sunnxt", "viki"
}|BAD_WORDS

# === EXTRA IGNORE WORDS FROM RPEDITZ (added, no font change) ===
EXTRA_IGNORE = {
    "x264", "x265", "h264", "h265", "10bit", "8bit", "10-bit", "8-bit",
    "hdhub4u", "hdhub", "hub4u", "hdhub4", "4uhd", "hdhubforu", "hdhubforu",
    "esub", "msub", "esubs", "msubs", "subs", "sub", "aac", "ac3", "dts", "mp3",
    "remux", "proper", "repack", "extended", "unrated", "directors", "cut",
    "brrip", "bdrip", "webrip", "web-dl", "webdl", "hdrip", "hdcam", "hdtc", "camrip",
    "cam", "hdts", "hq", "hq-hdrip", "hq-hdtc", "hq-cam", "hq-ts", "hq-predvd",
    "dual", "multi", "audio", "v1", "v2", "v3", "v4", "v5", "version", "ver", "cleaned", "clean",
    "atv", "atvp", "appletv", "cr", "crunchyroll", "hulu", "disney", "dnp", "lionsgate", "peacock", "max", "alt", "altt",
    "shemaroo", "chaupal", "stage", "planetmarathi", "manorama", "tubi",
    "5.1", "7.1", "2.0", "dd5.1", "ddp5.1", "dd", "ddp", "rs", "m", "ms", "mp4", "avi"
}

IGNORE_WORDS = IGNORE_WORDS_ORIG | EXTRA_IGNORE
IGNORE_WORDS_LOWER = {w.lower() for w in IGNORE_WORDS}

DEFAULT_HDHUB_DOMAIN = "https://new6.hdhub4u.cl"

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
}

OTT_PLATFORMS = {
    "nf": "Netflix", "netflix": "Netflix",
    "sonyliv": "SonyLiv", "sony": "SonyLiv", "sliv": "SonyLiv",
    "amzn": "Amazon Prime Video", "prime": "Amazon Prime Video", "primevideo": "Amazon Prime Video",
    "hotstar": "Disney+ Hotstar", "zee5": "Zee5",
    "jio": "JioHotstar", "jhs": "JioHotstar",
    "aha": "Aha", "hbo": "HBO Max", "paramount": "Paramount+",
    "apple": "Apple TV+", "hoichoi": "Hoichoi", "sunnxt": "Sun NXT", "viki": "Viki"
}

STANDARD_GENRES = {
    'Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 'Crime', 'Documentary',
    'Drama', 'Family', 'Fantasy', 'Film-Noir', 'History', 'Horror', 'Music',
    'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Sport', 'Thriller', 'War', 'Western'
}

CLEAN_PATTERN = re.compile(r'@[^ \n\r\t\.,:;!?()\[\]{}<>\\/"\'=_%]+|\bwww\.[^\s\]\)]+|\([\@^]+\)|\[[\@^]+\]')
NORMALIZE_PATTERN = re.compile(r"[._]+|[()\[\]{}:;'–!,.?_]")
QUALITY_PATTERN = re.compile(
    r"\b(?:HDCam|HDTC|CamRip|TS|TC|TeleSync|DVDScr|DVDRip|PreDVD|"
    r"WEBRip|WEB-DL|TVRip|HDTV|WEB DL|WebDl|BluRay|BRRip|BDRip|"
    r"360p|480p|720p|1080p|2160p|4K|1440p|540p|240p|140p|HEVC|HDRip|x264|x265|h264|h265|10bit|8bit|10-bit|BluRay|Bluray|HEVC)\b", 
    re.IGNORECASE
)
YEAR_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:19|20)\d{2}(?![A-Za-z0-9])")
RANGE_REGEX = re.compile(r'\bS(\d{1,2})[^\w\n\r]*E(?:p(?:isode)?)?0*(\d{1,2})\s*(?:to|-)\s*(?:E(?:p(?:isode)?)?)?0*(\d{1,2})',re.IGNORECASE)
SINGLE_REGEX = re.compile(r'\bS(\d{1,2})[^\w\n\r]*E(?:p(?:isode)?)?0*(\d{1,3})', re.IGNORECASE)
NAMED_REGEX = re.compile(r'Season\s*0*(\d{1,2})[\s\-,:]*Ep(?:isode)?\s*0*(\d{1,3})', re.IGNORECASE)
EP_ONLY_RANGE = re.compile(r'\b(?:EP|Episode)0*(\d{1,3})\s*-\s*0*(\d{1,3})\b',re.IGNORECASE)
LOOSE_SEASON_EP = re.compile(r'\b(\d{1,2})\s+(\d{1,2})\b')

MEDIA_FILTER = filters.document | filters.video | filters.audio
locks = defaultdict(asyncio.Lock)
pending_updates = {}
sending_updates = set()
error_tmdb = False

def clean_mentions_links(text: str) -> str:
    return CLEAN_PATTERN.sub("", text or "").strip()

def normalize(s: str) -> str:
    s = NORMALIZE_PATTERN.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()

def remove_ignored_words(text: str) -> str:
    return " ".join(word for word in text.split() if word.lower() not in IGNORE_WORDS_LOWER)

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
        return [w for w in s.split() if w]
    q_words = clean_words(q_raw)
    f_words = clean_words(f_raw)
    if not q_words or not f_words:
        return False
    if q_words == f_words:
        return True
    if all(qw in f_words for qw in q_words):
        return True
    return False

def get_qualities(text: str) -> str:
    if not text:
        return "N/A"
    quals = re.findall(r'(?:480p|720p|1080p|2160p|4K|WEB-DL|WEBRip|BluRay|HDRip)', text, re.IGNORECASE)
    seen = set()
    result = []
    for q in quals:
        q_up = q.upper()
        # Normalize
        if q_up == "WEBRIP":
            q_up = "WEBRip"
        if q_up == "WEB-DL":
            q_up = "WEB-DL"
        if q_up.lower() not in seen:
            seen.add(q_up.lower())
            result.append(q_up)
    order = {"480P":0, "720P":1, "1080P":2, "2160P":3, "4K":4, "WEB-DL":5, "WEBRIP":6, "BLURAY":7, "HDRIP":8}
    result.sort(key=lambda x: order.get(x.upper(), 99))
    return ", ".join(result) if result else "N/A"

def extract_ott_platform(text: str) -> str:
    text = text.lower()
    platforms = {plat for key, plat in OTT_PLATFORMS.items() if key in text}
    return " | ".join(platforms) if platforms else "N/A"

def extract_season_episode(filename: str) -> Tuple[Optional[int], Optional[str]]:
    if m := EP_ONLY_RANGE.search(filename):
        return 1, f"{int(m.group(1))}-{int(m.group(2))}"
    for pattern in (RANGE_REGEX, SINGLE_REGEX, NAMED_REGEX):
        if m := pattern.search(filename):
            season = int(m.group(1))
            if pattern == RANGE_REGEX:
                ep = f"{m.group(2)}-{m.group(3)}"
            else:
                ep = m.group(2)
            return season, ep
    if m := LOOSE_SEASON_EP.search(filename):
        s, e = int(m.group(1)), int(m.group(2))
        if 1 <= s <= 30 and 1 <= e <= 100:
            return s, str(e)
    return None, None

def schedule_update(bot, base_name, delay=5):
    if handle := pending_updates.get(base_name):
        if not handle.cancelled():
            handle.cancel()
    loop = asyncio.get_event_loop()
    pending_updates[base_name] = loop.call_later(
        delay,
        lambda: asyncio.create_task(update_movie_message(bot, base_name))
    )

def extract_media_info(filename: str, caption: str):
    filename_orig = filename
    filename = normalize(clean_mentions_links(filename).title())
    caption_clean = clean_mentions_links(caption).lower() if caption else ""
    unified = f"{caption_clean} {filename.lower()}".strip()

    season = episode = year = None
    tag = "#MOVIE"
    processed_raw = base_raw = filename
    quality = get_qualities(caption_clean) or get_qualities(filename.lower()) or "N/A"
    ott_platform = extract_ott_platform(f"{filename} {caption_clean}")

    lang_keys = {k for k in CAPTION_LANGUAGES if k in caption_clean or k in filename.lower()}
    language = ", ".join(sorted({CAPTION_LANGUAGES[k] for k in lang_keys})) if lang_keys else "N/A"

    season, episode = extract_season_episode(filename_orig)
    if season is not None:
        tag = "#SERIES"
        if m := (RANGE_REGEX.search(filename) or SINGLE_REGEX.search(filename) or NAMED_REGEX.search(filename) or EP_ONLY_RANGE.search(filename) or LOOSE_SEASON_EP.search(filename)):
            match_str = m.group(0)
            start_idx = filename.lower().find(match_str.lower())
            end_idx = start_idx + len(match_str)
            if start_idx != -1:
                processed_raw = filename[:end_idx]
                base_raw = filename[:start_idx]
                if year_match := YEAR_PATTERN.search(filename.lower()[end_idx:]):
                    y = year_match.group(0)
                    yi = filename.lower().find(y, end_idx)
                    if yi != -1:
                        processed_raw = filename[:yi+4]
                        base_raw += f" {y}"
    else:
        if year_match := YEAR_PATTERN.search(unified):
            year = year_match.group(0)
            year_idx = filename.lower().find(year.lower())
            if year_idx != -1:
                processed_raw = filename[:year_idx + 4]
                base_raw = processed_raw
        else:
            if qual_match := QUALITY_PATTERN.search(unified):
                qual_str = qual_match.group(0)
                qual_idx = filename.lower().find(qual_str.lower())
                if qual_idx != -1:
                    processed_raw = filename[:qual_idx]
                    base_raw = processed_raw

    # Enhanced cleaning for HdHub4U type files
    base_raw = re.sub(r'\b(?:HdHub4U|Hub4U|Hdhub|hdhub4u|x264-hdhub4u|x265-hdhub4u|HdHubForU|Rs|M|Ms)\b', ' ', base_raw, flags=re.IGNORECASE)
    base_raw = re.sub(r'\b[A-Z0-9]+-HdHub4U\b', ' ', base_raw, flags=re.IGNORECASE)
    base_raw = re.sub(r'\b\d+Bit\b', ' ', base_raw, flags=re.IGNORECASE)
    base_raw = re.sub(r'\bX\d{3,4}\b', ' ', base_raw, flags=re.IGNORECASE)

    base_name = normalize(remove_ignored_words(normalize(base_raw)))
    
    # Strip season/episode tokens from final base_name
    def _strip_season_episode_tokens(name: str) -> str:
        if not name:
            return name
        year_match = re.search(r'\(?\b(19|20)\d{2}\b\)?\s*$', name)
        year_part = ""
        if year_match:
            year_part = year_match.group(0)
            name = name[:year_match.start()].strip()
        patterns = [
            r'\bS\d{1,2}E\d{1,2}\b',
            r'\bS\d{1,2}\b',
            r'\bE\d{1,2}\b',
            r'\b\d{1,2}x\d{1,2}\b',
            r'\bSeason\s*\d{1,2}\b',
            r'\bEp(?:isode)?\.?\s*\d{1,3}\b',
            r'\bEpisode\s*\d{1,3}\b',
            r'\bPart\s*\d{1,2}\b'
        ]
        for p in patterns:
            name = re.sub(p, ' ', name, flags=re.IGNORECASE)
        name = re.sub(r'[_\.\-]+', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        if year_part:
            y = re.search(r'(19|20)\d{2}', year_part)
            if y:
                name = f"{name} {y.group(0)}"
        return name.strip()

    base_name = _strip_season_episode_tokens(base_name)
    if not base_name:
        base_name = normalize(remove_ignored_words(normalize(processed_raw))) or filename

    # Grouping ID: same movie different quality = same ID, different episode = different ID
    grouping_id = base_name
    if season:
        if episode and "-" not in str(episode):
            try:
                ep_num = int(episode)
                grouping_id = f"{base_name} S{season:02d}E{ep_num:02d}"
            except:
                grouping_id = f"{base_name} S{season:02d}E{episode}"
        else:
            grouping_id = f"{base_name} S{season:02d}"

    return {
        "processed": normalize(processed_raw),
        "base_name": base_name,
        "grouping_id": grouping_id,
        "tag": tag,
        "season": season,
        "episode": episode,
        "year": year,
        "quality": quality,
        "ott_platform": ott_platform,
        "language": language
    }

@Client.on_message(filters.chat(CHANNELS) & (filters.document | filters.video | filters.audio))
async def media_handler(bot, message):
    success = False
    file_name = ""
    try:
        media = message.document or message.video or message.audio
        if not media:
            return
        file_id = media.file_id
        file_name = getattr(media, "file_name", "")
        media.file_type = next((ft for ft in ("document", "video", "audio") if getattr(message, ft, None)), None)
        media.caption = message.caption or ""
        lock = locks[file_id]
        async with lock:
            success, info = await save_file(media)
            if success:
                print("File saved")
    except DuplicateKeyError:
        pass
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except PyMongoError as e:
        logger.error(f"MongoDB Error in media_handler: {e}")
    except Exception as e:
        logger.exception(f"Error processing media: {e}")

    if success:
        try:
            if await db.movie_update_status(temp.ME):
                await process_and_send_update(bot, file_name, message.caption)
        except Exception as e:
            logger.exception("Error in movie update")

async def process_and_send_update(bot, filename, caption):
    try:
        media_info = extract_media_info(filename, caption)
        base_name = media_info["base_name"]
        grouping_id = media_info["grouping_id"]
        processed = media_info["processed"]
        lock = locks[grouping_id]
        async with lock:
            await _process_with_lock(bot, filename, caption, media_info, base_name, grouping_id, processed)
    except PyMongoError as e:
        logger.error(f"Database error in process_and_send_update: {e}")
    except Exception as e:
        logger.exception(f"Processing failed in process_and_send_update: {e}")

async def _process_with_lock(bot, filename, caption, media_info, base_name, grouping_id, processed):
    if not hasattr(db, 'movie_updates'):
        db.movie_updates = db.db.movie_updates
    movie_doc = await db.movie_updates.find_one({"_id": grouping_id})
    error_tmdb=False
    file_data = {
        "filename": filename,
        "processed": processed,
        "quality": media_info["quality"],
        "language": media_info["language"],
        "ott_platform": media_info["ott_platform"],
        "timestamp": datetime.now(),
        "tag": media_info["tag"],
        "season": media_info["season"],
        "episode": media_info["episode"]
    }
    if not movie_doc:
        if TMDB_POSTER:
            details = await get_movie_detailsx(base_name)
            if not details or details.get("error") or (not details.get("poster_url") and not details.get("backdrop_url")):
                error_tmdb=True
                logger.info("TMDB error switching to IMDB + Blogger + PosterFlix")
                details = await get_movie_details(base_name) or {}
                # Fallback chain for poster
                if not details.get("poster_url"):
                    blog_poster = await get_blogger_poster_url(base_name, year=media_info.get("year"))
                    if blog_poster:
                        details["poster_url"] = blog_poster
                    else:
                        pf_poster = await get_posterflix_poster(base_name, year=media_info.get("year"))
                        if pf_poster:
                            details["poster_url"] = pf_poster
        else:
            details = await get_movie_details(base_name) or {}
            if not details.get("poster_url"):
                blog_poster = await get_blogger_poster_url(base_name)
                if blog_poster:
                    details["poster_url"] = blog_poster
                else:
                    pf_poster = await get_posterflix_poster(base_name)
                    if pf_poster:
                        details["poster_url"] = pf_poster

        raw_genres = details.get("genres", "N/A")
        if isinstance(raw_genres, str):
            genre_list = [g.strip() for g in raw_genres.split(",")]
            genres = ", ".join(g for g in genre_list if g in STANDARD_GENRES) or "N/A"
        else:
            genres = ", ".join(g for g in raw_genres if g in STANDARD_GENRES) or "N/A"
        runtime_raw = details.get("runtime", "N/A")
        if isinstance(runtime_raw, list):
            runtime_raw = ", ".join(str(x) for x in runtime_raw)
        runtime_formatted = format_runtime(runtime_raw)
        movie_doc = {
            "_id": grouping_id,
            "base_name": base_name,
            "files": [file_data],
            "poster_url": details.get("backdrop_url") if LANDSCAPE_POSTER and TMDB_POSTER and details.get("backdrop_url") and not error_tmdb else details.get("poster_url"),
            "genres": genres,
            "rating": details.get("rating", "N/A"),
            "runtime": runtime_formatted,
            "imdb_url": details.get("url", "")if not TMDB_POSTER or error_tmdb else details.get("tmdb_url"),
            "year": details.get("year") or media_info["year"],
            "tag": media_info["tag"],
            "ott_platform": media_info["ott_platform"],
            "message_id": None,
            "is_photo": False,
            "error_tmdb": error_tmdb,
            "is_backdrop": details.get("backdrop_url")
        }
        try:
            await db.movie_updates.insert_one(movie_doc)
            await send_movie_update(bot, grouping_id)
            movie_doc = await db.movie_updates.find_one({"_id": grouping_id})
        except DuplicateKeyError:
            movie_doc = await db.movie_updates.find_one({"_id": grouping_id})
            if movie_doc:
                if any(f["filename"] == filename for f in movie_doc["files"]):
                    return
                await db.movie_updates.update_one(
                    {"_id": grouping_id},
                    {"$push": {"files": file_data}}
                )
                movie_doc["files"].append(file_data)
                schedule_update(bot, grouping_id)
    else:
        if any(f["filename"] == filename for f in movie_doc["files"]):
            return
        await db.movie_updates.update_one(
            {"_id": grouping_id},
            {"$push": {"files": file_data}}
        )
        movie_doc["files"].append(file_data)
        schedule_update(bot, grouping_id)

def format_runtime(runtime_input):
    if not runtime_input or runtime_input == "N/A":
        return "N/A"
    runtime_str = str(runtime_input).strip()
    if "h" in runtime_str.lower() and "m" in runtime_str.lower():
        return runtime_str
    try:
        if "min" in runtime_str.lower():
            mins = int(re.search(r'\d+', runtime_str).group())
        else:
            nums = re.findall(r'\d+', runtime_str)
            if nums:
                mins = int(nums[0])
                if mins < 10:
                    return runtime_str
            else:
                return runtime_str
        h = mins // 60
        m = mins % 60
        if h > 0:
            return f"{h}h {m}m" if m else f"{h}h"
        else:
            return f"{m}m"
    except:
        return runtime_str

async def send_movie_update(bot, grouping_id):
    if grouping_id in sending_updates:
        logger.warning(f"Duplicate send prevented: {grouping_id}")
        return None
    sending_updates.add(grouping_id)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            movie_doc = await db.movie_updates.find_one({"_id": grouping_id})
            if not movie_doc:
                sending_updates.discard(grouping_id)
                return None
            text = generate_movie_message(movie_doc, grouping_id)
            is_series = movie_doc.get("tag") == "#SERIES" or any(f.get("season") for f in movie_doc.get("files", []))
            btn_text = "ɢᴇᴛ ғɪʟᴇs"
            if HAS_STYLED and KeyboardButtonStyle:
                bstyle = KeyboardButtonStyle(bg_primary=True) if is_series else KeyboardButtonStyle(bg_success=True)
                buttons = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=f"https://t.me/{temp.U_NAME}?start=getfile-{grouping_id.replace(' ', '-')}", style=bstyle)]])
            else:
                buttons = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=f"https://t.me/{temp.U_NAME}?start=getfile-{grouping_id.replace(' ', '-')}")]])
            size=(2560, 1440) if LANDSCAPE_POSTER else (1280, 1920)
            if movie_doc.get("poster_url") and not LINK_PREVIEW:
                resized_poster = await fetch_image(movie_doc["poster_url"], size)
                if resized_poster:
                    msg = await bot.send_photo(
                        chat_id=MOVIE_UPDATE_CHANNEL,
                        photo=resized_poster,
                        caption=text,
                        reply_markup=buttons,
                        parse_mode=enums.ParseMode.HTML
                    )
                    is_photo = True
                else:
                    msg = await bot.send_message(
                        chat_id=MOVIE_UPDATE_CHANNEL,
                        text=text,
                        reply_markup=buttons,
                        parse_mode=enums.ParseMode.HTML
                    )
                    is_photo = False
            else:
                send_params = {
                    "chat_id": MOVIE_UPDATE_CHANNEL,
                    "text": text,
                    "reply_markup": buttons,
                    "parse_mode": enums.ParseMode.HTML
                }
                if movie_doc.get("poster_url") and LINK_PREVIEW:
                    send_params["link_preview_options"] = LinkPreviewOptions(is_disabled=False, show_above_text=ABOVE_PREVIEW)
                else:
                    send_params["link_preview_options"] = LinkPreviewOptions(is_disabled=not LINK_PREVIEW)
                msg = await bot.send_message(**send_params)
                is_photo = False
            await db.movie_updates.update_one(
                {"_id": grouping_id},
                {"$set": {"message_id": msg.id, "is_photo": is_photo}}
            )
            sending_updates.discard(grouping_id)
            return msg
        except FloodWait as e:
            await asyncio.sleep(e.value + 2)
        except Exception as e:
            logger.error(f"Failed to send movie update: {e}")
            break
    sending_updates.discard(grouping_id)
    return None

async def update_movie_message(bot, grouping_id):
    try:
        movie_doc = await db.movie_updates.find_one({"_id": grouping_id})
        if not movie_doc:
            return
        text = generate_movie_message(movie_doc, grouping_id)
        is_series = movie_doc.get("tag") == "#SERIES" or any(f.get("season") for f in movie_doc.get("files", []))
        btn_text = "ɢᴇᴛ ғɪʟᴇs"
        if HAS_STYLED and KeyboardButtonStyle:
            bstyle = KeyboardButtonStyle(bg_primary=True) if is_series else KeyboardButtonStyle(bg_success=True)
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=f"https://t.me/{temp.U_NAME}?start=getfile-{grouping_id.replace(' ', '-')}", style=bstyle)]])
        else:
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=f"https://t.me/{temp.U_NAME}?start=getfile-{grouping_id.replace(' ', '-')}")]])
        message_id = movie_doc.get("message_id")
        is_photo = movie_doc.get("is_photo", False)
        if not message_id:
            await send_movie_update(bot, grouping_id)
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
                    link_preview_options=LinkPreviewOptions(is_disabled=not LINK_PREVIEW, show_above_text=ABOVE_PREVIEW)
                )
            return
        except MessageNotModified:
            pass
        except MessageIdInvalid as e:
            logger.warning(f"Message update skipped due to error: {e}")
            pass
        except Exception:
            try:
                await bot.delete_messages(
                    chat_id=MOVIE_UPDATE_CHANNEL,
                    message_ids=message_id
                )
                await db.movie_updates.update_one(
                    {"_id": grouping_id},
                    {"$set": {"message_id": None, "is_photo": False}}
                )
            except Exception as e:
                logger.error(f"Error during message deletion/update in recovery: {e}")
                pass
            await send_movie_update(bot, grouping_id)
    except Exception as e:
        logger.error(f"Failed to update movie message for {grouping_id}: {e}")

def generate_movie_message(movie_doc, grouping_id):
    from collections import defaultdict
    all_qualities = set()
    all_languages = set()
    all_ott_platforms = set()
    all_tags = set()
    episodes_by_season = defaultdict(set)
    for file in movie_doc["files"]:
        if file["quality"] != "N/A":
            quals = [q.strip().upper() for q in file["quality"].split(",") if q.strip()]
            all_qualities.update(quals)
        if file["language"] != "N/A":
            all_languages.update(lang.strip() for lang in file["language"].split(",") if lang.strip())
        if file["ott_platform"] != "N/A":
            platforms = [p.strip() for p in file["ott_platform"].split("|") if p.strip()]
            all_ott_platforms.update(platforms)
        if file["tag"]:
            all_tags.add(file["tag"])
        if file.get("season") and file.get("episode"):
            episodes_by_season[file["season"]].add(file["episode"])
    primary_tag = "#SERIES" if "#SERIES" in all_tags else "#MOVIE"
    epi_block = ""
    if episodes_by_season:
        episode_lines = []
        for season, episodes in sorted(episodes_by_season.items(), key=lambda x: int(x[0])):
            singles = []
            ranges = []
            for ep in episodes:
                if "-" in ep:
                    ranges.append(ep)
                else:
                    try:
                        singles.append(int(ep))
                    except ValueError:
                        ranges.append(ep)
            singles.sort()
            collapsed = []
            start = end = None
            for num in singles:
                if start is None:
                    start = end = num
                elif num == end + 1:
                    end = num
                else:
                    collapsed.append(str(start) if start == end else f"{start}-{end}")
                    start = end = num
            if start is not None:
                collapsed.append(str(start) if start == end else f"{start}-{end}")
            all_ep_parts = collapsed + sorted(ranges, key=lambda s: int(s.split("-")[0]))
            episode_lines.append(f"S{int(season)}: {', '.join(all_ep_parts)}")
        epi_str = "\n".join(episode_lines)
        if epi_str:
            epi_block = f"📺 ᴇᴘɪsᴏᴅᴇs : <b>{epi_str}</b>"
    genres = movie_doc.get("genres", "N/A")
    quality_str = ", ".join(sorted(all_qualities)) if all_qualities else "N/A"
    language_str = ", ".join(sorted(all_languages)) if all_languages else "N/A"
    ott_str = ", ".join(sorted(all_ott_platforms)) if all_ott_platforms else "N/A"
    rating=movie_doc.get("rating", "-")
    try:
        r = float(rating)
    except (TypeError, ValueError):
        r = 0.0
    rating_text = "-" if r == 0.0 else str(rating)
    runtime = movie_doc.get("runtime", "N/A")
    year_val = str(movie_doc.get("year") or "")
    filename_display = movie_doc.get("base_name", grouping_id)
    if year_val and filename_display.strip().endswith(year_val):
        filename_display = filename_display.strip()[:-len(year_val)].strip()
    return script.MOVIE_UPDATE_NOTIFY_TXT.format(
        poster_url=movie_doc.get("poster_url", ""),
        imdb_url=movie_doc.get("imdb_url", ""),
        filename=filename_display,
        tag=primary_tag,
        year=year_val,
        genres=genres,
        ott=ott_str,
        runtime=runtime,
        quality=quality_str,
        language=language_str,
        episodes=epi_block,
        rating=rating_text,
        search_link=temp.B_LINK
    )

# --- Domain setter (from Rpeditz) ---
@Client.on_message(filters.command("setdomain"))
async def set_domain_handler(bot, message):
    if len(message.command) < 2:
        try:
            from database.users_chats_db import db
            setting = await db.db.settings.find_one({"_id": "hdhub_base_url"})
            current_url = setting.get("url") if setting else DEFAULT_HDHUB_DOMAIN
        except:
            current_url = DEFAULT_HDHUB_DOMAIN
        return await message.reply_text(
            f"🌐 <b>Current HDHub4u URL:</b> <code>{current_url}</code>\n\n"
            f"💡 <b>Usage:</b> <code>/setdomain https://newdomain.com</code>"
        )
    new_url = message.command[1].strip()
    if not new_url.startswith("http"):
        return await message.reply_text("❌ Invalid URL. Must start with http:// or https://")
    try:
        from database.users_chats_db import db
        await db.db.settings.update_one(
            {"_id": "hdhub_base_url"},
            {"$set": {"url": new_url}},
            upsert=True
        )
        await message.reply_text(f"✅ <b>HDHub4u base URL updated to:</b>\n<code>{new_url}</code>")
    except Exception as e:
        await message.reply_text(f"❌ Failed to update domain: {e}")
