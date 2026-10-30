"""
Configuration file for Auto Filter & File Indexing Bot.
Defines all environment variables, credentials, database URIs, and operational settings.
"""

import os
import re
from os import environ, getenv
import pytz
from Script import script

# Regex pattern for validating Telegram numeric IDs
id_pattern = re.compile(r'^.\d+$')

def is_enabled(value, default: bool = False) -> bool:
    """Helper function to parse boolean flags from string environment variables."""
    if value is None:
        return default
    value = str(value).strip().lower()
    if value in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value in ["false", "no", "0", "disable", "n"]:
        return False
    return default


# ==============================================================================
# 1. BOT CREDENTIALS & SESSION
# ==============================================================================
# Telegram API credentials from https://my.telegram.org
API_ID = int(environ.get('API_ID', ''))
API_HASH = environ.get('API_HASH', '')

# Bot token obtained from @BotFather
BOT_TOKEN = environ.get('BOT_TOKEN', '')

# Pyrogram session name
SESSION = environ.get('SESSION', 'dreamxbotz_search')
SESSION_NAME = str(environ.get('SESSION_NAME', 'dreamXBotz'))
name = str(environ.get('name', 'DREAMXBOTZ'))


# ==============================================================================
# 2. ADMINS, CHANNELS & PERMISSIONS
# ==============================================================================
# Telegram user IDs of bot administrators (space-separated in .env)
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '634637418').split()]

# Channels to auto-index files from (Bot must be an admin in these channels)
CHANNELS = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('CHANNELS', '-100').split()]

# Logging & Storage Channels
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-100'))            # General activity & error logs
BIN_CHANNEL = int(environ.get('BIN_CHANNEL', '-100'))            # File storage / binary cache channel
PREMIUM_LOGS = int(environ.get('PREMIUM_LOGS', '-100'))          # Premium subscription logs
DELETE_CHANNELS = [int(dch) if id_pattern.search(dch) else dch for dch in environ.get('DELETE_CHANNELS', '-100').split()]

# Support Group & Request Channel
support_chat_id = environ.get('SUPPORT_CHAT_ID', '-100')
SUPPORT_CHAT_ID = int(support_chat_id) if support_chat_id and id_pattern.search(support_chat_id) else None
SUPPORT_CHAT = environ.get('SUPPORT_CHAT', 'https://t.me/')

reqst_channel = environ.get('REQST_CHANNEL_ID', '-100')
REQST_CHANNEL = int(reqst_channel) if reqst_channel and id_pattern.search(reqst_channel) else None
INDEX_REQ_CHANNEL = int(environ.get('INDEX_REQ_CHANNEL', LOG_CHANNEL))

# Force Subscription Channels (Users must join these before using the bot)
auth_req_channels = environ.get("AUTH_REQ_CHANNELS", "-100")
auth_channels = environ.get("AUTH_CHANNELS", "-100")
AUTH_REQ_CHANNELS = [int(ch) for ch in auth_req_channels.split() if ch and id_pattern.match(ch)]
AUTH_CHANNELS = [int(ch) for ch in auth_channels.split() if ch and id_pattern.match(ch)]

# User Access Lists
auth_users = [int(user) if id_pattern.search(user) else user for user in environ.get('AUTH_USERS', '').split()]
AUTH_USERS = (auth_users + ADMINS) if auth_users else []
PREMIUM_USER = [int(user) if id_pattern.search(user) else user for user in environ.get('PREMIUM_USER', '').split()]

# Social & Community Links
GRP_LNK = environ.get('GRP_LNK', 'https://t.me/dreamxbotz')
OWNER_LNK = environ.get('OWNER_LNK', 'https://t.me/dreamxbotz')
UPDATE_CHNL_LNK = environ.get('UPDATE_CHNL_LNK', 'https://t.me/dreamxbotz')


# ==============================================================================
# 3. DATABASE CONFIGURATION (MongoDB)
# ==============================================================================
# Primary MongoDB Connection URI & Database details
DATABASE_URI = environ.get('DATABASE_URI', '')
DATABASE_NAME = environ.get('DATABASE_NAME', 'Cluster0')
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'dreamcinezone_files')

# Secondary MongoDB for multiple DB load balancing
MULTIPLE_DB = is_enabled(os.environ.get('MULTIPLE_DB', "False"), False)
DATABASE_URI2 = environ.get('DATABASE_URI2', '')

# Fallback to primary database if multiple DB mode is disabled
if not MULTIPLE_DB:
    DATABASE_URI2 = DATABASE_URI


# ==============================================================================
# 4. BOT MEDIA & UI ASSETS
# ==============================================================================
# UI Banner & Poster Images
PICS_URL = (environ.get('PICS_URL', 'https://api.aniwallpaper.workers.dev/random?type=girl')).split()
PICS = (environ.get('PICS', 'https://graph.org/file/56b5deb73f3b132e2bb73.jpg https://graph.org/file/5303692652d91d52180c2.jpg https://graph.org/file/425b6f46efc7c6d64105f.jpg https://graph.org/file/876867e761c6c7a29855b.jpg')).split()
NOR_IMG = environ.get("NOR_IMG", "https://graph.org/file/e20b5fdaf217252964202.jpg")
MELCOW_PHOTO = environ.get("MELCOW_PHOTO", "https://graph.org/file/56b5deb73f3b132e2bb73.jpg")
SPELL_IMG = environ.get("SPELL_IMG", "https://graph.org/file/13702ae26fb05df52667c.jpg")
SUBSCRIPTION = environ.get('SUBSCRIPTION', 'https://graph.org/file/242b7f1b52743938d81f1.jpg')
FSUB_PICS = (environ.get('FSUB_PICS', 'https://graph.org/file/7478ff3eac37f4329c3d8.jpg https://graph.org/file/56b5deb73f3b132e2bb73.jpg')).split()

# Timezone settings
TIMEZONE = environ.get('TIMEZONE', 'Asia/Kolkata')
TZ = pytz.timezone(TIMEZONE)


# ==============================================================================
# 5. SEARCH & FILTERING ENGINE SETTINGS
# ==============================================================================
CACHE_TIME = int(environ.get('CACHE_TIME', 300))                 # In-memory cache duration in seconds
DELETE_TIME = int(environ.get("DELETE_TIME", "300"))              # Auto-delete message timer (seconds)
MAX_LIST_ELM = int(environ.get("MAX_LIST_ELM") or 10) or None     # Search list items per page
MAX_B_TN = environ.get("MAX_B_TN", "5")                           # Max buttons per row

# Feature Toggles
AUTO_FFILTER = is_enabled(environ.get('AUTO_FFILTER', "True"), True)
AUTO_DELETE = is_enabled(environ.get('AUTO_DELETE', "True"), True)
USE_CAPTION_FILTER = is_enabled(environ.get('USE_CAPTION_FILTER', "True"), True)
INDEX_CAPTION = is_enabled(environ.get('SAVE_CAPTION', "True"), True)
COVERX = is_enabled(environ.get('COVERX', "True"), True)
PROTECT_CONTENT = is_enabled(environ.get('PROTECT_CONTENT', "False"), False)
PM_SEARCH = is_enabled(environ.get('PM_SEARCH', "True"), True)
EMOJI_MODE = is_enabled(environ.get('EMOJI_MODE', "True"), True)
BUTTON_MODE = is_enabled(environ.get('BUTTON_MODE', "False"), False)
P_TTI_SHOW_OFF = is_enabled(environ.get('P_TTI_SHOW_OFF', "False"), False)
MAX_BTN = is_enabled(environ.get('MAX_BTN', "True"), True)
NO_RESULTS_MSG = is_enabled(environ.get("NO_RESULTS_MSG", "True"), True)
SPELL_CHECK_REPLY = is_enabled(environ.get("SPELL_CHECK_REPLY", "True"), True)
MELCOW_NEW_USERS = is_enabled(environ.get('MELCOW_NEW_USERS', "False"), False)
ULTRA_FAST_MODE = is_enabled(environ.get('ULTRA_FAST_MODE'), False)
MAINTENANCE = is_enabled(environ.get('MAINTENANCE', "False"), False)

# Captions & Alerts
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", f"{script.CAPTION}")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)
IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", f"{script.IMDB_TEMPLATE_TXT}")
MSG_ALRT = environ.get('MSG_ALRT', 'Share & Support Us ♥️')

# IMDB Settings
IMDB = is_enabled(environ.get('IMDB', "True"), False)
LONG_IMDB_DESCRIPTION = is_enabled(environ.get("LONG_IMDB_DESCRIPTION", "False"), False)

# Languages & Media Qualities Seasons
LANGUAGES = {
    "ᴍᴀʟᴀʏᴀʟᴀᴍ": "mal",
    "ᴛᴀᴍɪʟ": "tam",
    "ᴇɴɢʟɪsʜ": "eng",
    "ʜɪɴᴅɪ": "hin",
    "ᴛᴇʟᴜɢᴜ": "tel",
    "ᴋᴀɴɴᴀᴅᴀ": "kan",
    "ɢᴜᴊᴀʀᴀᴛɪ": "guj",
    "ᴍᴀʀᴀᴛʜɪ": "mar",
    "ᴘᴜɴᴊᴀʙɪ": "pun"
}
QUALITIES = ["360P", "480P", "720P", "1080P", "1440P", "2160P", "4K"]

SEASON_COUNT = 12
SEASONS = [f"S{str(i).zfill(2)}" for i in range(1, SEASON_COUNT + 1)]

# Blacklisted words removed from query strings
BAD_WORDS = {
    "PrivateMovieZ", "toonworld4all", "themoviesboss", "1tamilmv",
    "tamilblasters", "1tamilblasters", "skymovieshd", "extraflix",
    "hdm2", "moviesmod", "hdhub4u", "mkvcinemas", "primefix",
    "join", "www", "villa", "tg", "original"
}


# ==============================================================================
# 6. MOVIE UPDATES & POSTER NOTIFICATIONS
# ==============================================================================
MOVIE_UPDATE_NOTIFICATION = is_enabled(environ.get('MOVIE_UPDATE_NOTIFICATION', "False"), False)
MOVIE_UPDATE_CHANNEL = int(environ.get('MOVIE_UPDATE_CHANNEL', '-100'))
DREAMXBOTZ_IMAGE_FETCH = is_enabled(environ.get('DREAMXBOTZ_IMAGE_FETCH', "True"), True)
LINK_PREVIEW = is_enabled(environ.get('LINK_PREVIEW', "False"), False)
ABOVE_PREVIEW = is_enabled(environ.get('ABOVE_PREVIEW', "True"), True)

# The Movie Database (TMDB) API Key
TMDB_API_KEY = environ.get('TMDB_API_KEY', '')
TMDB_POSTER = is_enabled(environ.get('TMDB_POSTER', "True"), True)
TMDB_ON_SEARCH = is_enabled(environ.get('TMDB_ON_SEARCH', "False"), False)
LANDSCAPE_POSTER = is_enabled(environ.get('LANDSCAPE_POSTER', "True"), True)


# ==============================================================================
# 7. SHORTENERS & VERIFICATION SYSTEM
# ==============================================================================
IS_VERIFY = is_enabled(environ.get('IS_VERIFY', 'False'), False)
LOG_VR_CHANNEL = int(environ.get('LOG_VR_CHANNEL', '-100'))
VERIFY_IMG = environ.get("VERIFY_IMG", "https://telegra.ph/file/9ecc5d6e4df5b83424896.jpg")

# Tutorial Links
TUTORIAL = environ.get("TUTORIAL", "https://t.me/dreamxbotz")
TUTORIAL_2 = environ.get("TUTORIAL_2", "https://t.me/dreamxbotz")
TUTORIAL_3 = environ.get("TUTORIAL_3", "https://t.me/dreamxbotz")

# Primary Shortener
SHORTENER_WEBSITE = environ.get("SHORTENER_WEBSITE", "")
SHORTENER_API = environ.get("SHORTENER_API", "")

# Secondary Shortener
SHORTENER_WEBSITE2 = environ.get("SHORTENER_WEBSITE2", "")
SHORTENER_API2 = environ.get("SHORTENER_API2", "")

# Tertiary Shortener
SHORTENER_WEBSITE3 = environ.get("SHORTENER_WEBSITE3", "")
SHORTENER_API3 = environ.get("SHORTENER_API3", "")

# Verification Time Gaps (in seconds)
TWO_VERIFY_GAP = int(environ.get('TWO_VERIFY_GAP', "1200"))       # 20 minutes
THREE_VERIFY_GAP = int(environ.get('THREE_VERIFY_GAP', "54000"))   # 15 hours


# ==============================================================================
# 8. PREMIUM PLANS & PAYMENT CONFIGURATION
# ==============================================================================
QR_CODE = environ.get('QR_CODE', 'https://graph.org/file/e419f801841c2ee3db0fc.jpg')
OWNER_UPI_ID = environ.get('OWNER_UPI_ID', 'ɴᴏ ᴀᴠᴀɪʟᴀʙʟᴇ ʀɪɢʜᴛ ɴᴏᴡ')

# Stars / Premium Pricing Structure {Amount: "Duration"}
STAR_PREMIUM_PLANS = {
    10: "7day",
    20: "15day",
    40: "1month",
    55: "45day",
    75: "60day",
}


# ==============================================================================
# 9. SERVER, STREAMING & WEB SETTINGS
# ==============================================================================
# Streaming Mode (Keep False on Render free tier to conserve bandwidth)
STREAM_MODE = is_enabled(environ.get('STREAM_MODE', "False"), False)
PREMIUM_STREAM_MODE = is_enabled(environ.get('PREMIUM_STREAM_MODE', "False"), False)

# Server Binding & Host Configuration
ON_HEROKU = 'DYNO' in environ
APP_NAME = environ.get('APP_NAME', None) if ON_HEROKU else None
PORT = int(environ.get("PORT", "8080"))
BIND_ADDRESS = getenv('WEB_SERVER_BIND_ADDRESS', '0.0.0.0')

FQDN = (
    environ.get('FQDN', BIND_ADDRESS)
    if not ON_HEROKU or environ.get('FQDN')
    else f"{APP_NAME}.herokuapp.com"
)
FQDN = re.sub(r'^https?://', '', str(FQDN)).rstrip('/')
NO_PORT = is_enabled(environ.get('NO_PORT'), False)
HAS_SSL = is_enabled(getenv('HAS_SSL'), True)

# Public URL construction
if HAS_SSL:
    URL = f"https://{FQDN}/"
else:
    URL = f"http://{FQDN}/" if NO_PORT else f"http://{FQDN}:{PORT}/"

# Operational Performance Parameters
WORKERS = int(environ.get('WORKERS', '4'))
MULTI_CLIENT = False
SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "298"))          # Keep-alive ping interval (seconds)

# Reaction Emojis
REACTIONS = [
    "🤝", "😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩", "😱",
    "🤣", "😘", "👏", "😛", "😈", "🎉", "⚡️", "🫡", "🤓", "😎",
    "🏆", "🔥", "🤭", "🌚", "🆒", "👻", "😁"
]


# ==============================================================================
# 10. BOT COMMANDS REGISTRY
# ==============================================================================
Bot_cmds = {
    "start": "Sᴛᴀʀᴛ Mᴇ Bᴀʙʏ",
    "stats": "Gᴇᴛ Bᴏᴛ Sᴛᴀᴛs",
    "alive": " Cʜᴇᴄᴋ Bᴏᴛ Aʟɪᴠᴇ ᴏʀ Nᴏᴛ ",
    "settings": "ᴄʜᴀɴɢᴇ sᴇᴛᴛɪɴɢs",
    "id": "ɢᴇᴛ ɪᴅ ᴛᴇʟᴇɢʀᴀᴍ ",
    "info": "Gᴇᴛ Usᴇʀ ɪɴғᴏ ",
    "del_msg": "ʀᴇᴍᴏᴠᴇ ғɪʟᴇ ɴᴀᴍᴇ ᴄᴏʟʟᴇᴄᴛɪᴏɴ ɴᴏтɪғɪᴄᴀᴛɪᴏɴ...",
    "movie_update": "ᴏɴ ᴏғғ ᴀᴄᴄᴏʀᴅɪɴɢ ʏᴏᴜʀ ɴᴇᴇᴅᴇᴅ...",
    "pm_search": "ᴘᴍ sᴇᴀʀᴄʜ ᴏɴ ᴏғғ ᴀᴄᴄᴏʀᴅɪɴɢ ʏᴏᴜʀ ɴᴇᴇᴅᴇᴅ...",
    "trendlist": "Gᴇᴛ Tᴏᴘ Tʀᴀɴᴅɪɴɢ Sᴇᴀʀᴄʜ Lɪsᴛ",
    "broadcast": "ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀꜱ.",
    "grp_broadcast": "ʙʀᴏᴀᴅᴄᴀsᴛ ᴀ ᴍᴇssᴀɢᴇ ᴛᴏ ᴀʟʟ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘs",
    "send": "ꜱᴇɴᴅ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴀ ᴘᴀʀᴛɪᴄᴜʟᴀʀ ᴜꜱᴇʀ.",
    "add_premium": "ᴀᴅᴅ ᴀɴʏ ᴜꜱᴇʀ ᴛᴏ ᴘʀᴇᴍɪᴜᴍ.",
    "remove_premium": "ʀᴇᴍᴏᴠᴇ ᴀɴʏ ᴜꜱᴇʀ ꜰʀᴏᴍ ᴘʀᴇᴍɪᴜᴍ.",
    "premium_users": "ɢᴇᴛ ʟɪꜱᴛ ᴏꜰ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ.",
    "restart": "ʀᴇꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ.",
    "group_cmd": "ɢʀᴏᴜᴘ ᴄᴏᴍᴍᴀɴᴅ ʟɪsᴛ",
    "admin_cmd": "ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs ʟɪsᴛ.",
    "reset_group": "Group Setting Default",
    "trial_reset": "User Trial Reset",
    "remove_fsub": "Remove Forced Subscription (group admin only)",
    "maintenance": "Maintenance Mode (Admin Only)",
}


# ==============================================================================
# 11. STARTUP LOG CONFIGURATION SUMMARY
# ==============================================================================
LOG_STR = "Current Customized Configurations are:-\n"
LOG_STR += ("IMDB Results are enabled, Bot will be showing imdb details for your queries.\n" if IMDB else "IMDB Results are disabled.\n")
LOG_STR += ("P_TTI_SHOW_OFF found, Users will be redirected to send /start to Bot PM instead of sending file directly.\n" if P_TTI_SHOW_OFF else "P_TTI_SHOW_OFF is disabled, files will be sent in PM instead of starting the bot.\n")
LOG_STR += ("BUTTON_MODE is found, filename and file size will be shown in a single button instead of two separate buttons.\n" if BUTTON_MODE else "BUTTON_MODE is disabled, filename and file size will be shown as different buttons.\n")
LOG_STR += (f"CUSTOM_FILE_CAPTION enabled with value {CUSTOM_FILE_CAPTION}, your files will be sent along with this customized caption.\n" if CUSTOM_FILE_CAPTION else "No CUSTOM_FILE_CAPTION Found, Default captions of file will be used.\n")
LOG_STR += ("Long IMDB storyline enabled." if LONG_IMDB_DESCRIPTION else "LONG_IMDB_DESCRIPTION is disabled, Plot will be shorter.\n")
LOG_STR += ("Spell Check Mode is enabled, bot will be suggesting related movies if movie name is misspelled.\n" if SPELL_CHECK_REPLY else "Spell Check Mode is disabled.\n")
