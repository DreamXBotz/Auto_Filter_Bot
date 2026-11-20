import logging
import time
import re
import os
import random
import string
from info import ULTRA_FAST_MODE, MAX_LIST_ELM, BAD_WORDS, LONG_IMDB_DESCRIPTION, IS_VERIFY, MAX_B_TN, TUTORIAL, TUTORIAL_2, TUTORIAL_3, LOG_CHANNEL, TMDB_ON_SEARCH
from imdbkit import IMDBKit # pyrefly: ignore 
import asyncio
from pyrogram.types import Message, InlineKeyboardButton
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid, ChatAdminRequired
from pyrogram import enums
from typing import Union
from Script import script
from database.users_chats_db import db
from shortzy import Shortzy
from plugins.Dreamxfutures.Imdbposter import get_movie_detailsx


logger = logging.getLogger(__name__)

def get_random_mix_id():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=6))


_CLEAN_FILENAME_PREFIXES = ('[', '@', 'www.')
_UNWANTED_BAD_WORDS = {word.lower() for word in BAD_WORDS}
_PHRASES_SPLIT_REGEX = re.compile(r'\s{2,}')
_LANG_REGEX = re.compile(r'\b(hin(di)?|eng(lish)?|mal(ayalam)?|tam(il)?|tel(ugu)?|kan(nada)?|ben(gali)?|mar(athi)?|urdu|guj(arat)?|punj(abi)?)\b', re.IGNORECASE)
_SEASON_REGEX = re.compile(r's(eason)?\s*0*\d+', re.IGNORECASE)
_QUALITY_REGEX = re.compile(r'\b(360p|480p|720p|1080p|1440p|2160p|4k)\b', re.IGNORECASE)
_MULTI_SPACE_REGEX = re.compile(r'\s+')
_REQUEST_UNDERLINE_REGEX = re.compile(r"<u>(.*?)</u>")
_REQUEST_PREFIX_REGEX = re.compile(r"📝 ʀᴇǫᴜᴇꜱᴛ ?: ?(.*?)(?:\n|$)")


imdb = IMDBKit()

class LimitedDict(dict):
    def __init__(self, maxsize=200):
        super().__init__()
        self.maxsize = maxsize

    def __setitem__(self, key, value):
        if len(self) >= self.maxsize:
            self.pop(next(iter(self)), None)
        super().__setitem__(key, value)


class temp(object):   
    BANNED_USERS = set()
    BANNED_CHATS = set()
    ME = None
    CURRENT=int(os.environ.get("SKIP", 2))
    CANCEL = False
    B_USERS_CANCEL = False
    B_GROUPS_CANCEL = False 
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    B_LINK = None
    SETTINGS = LimitedDict(maxsize=300)
    GETALL = LimitedDict(maxsize=200)
    IMDB_CAP = LimitedDict(maxsize=100)
    VERIFICATIONS = LimitedDict(maxsize=300)
    TEMP_INVITE_LINKS = LimitedDict(maxsize=200)
    REQ_LINKS = LimitedDict(maxsize=200)
    FSUB_CACHE = LimitedDict(maxsize=2000)


async def is_req_subscribed(client, user_id, rqfsub_channels):
    btn = []

    async def check_req_channel(ch_id):
        try:
            cid = int(ch_id)
        except Exception:
            cid = ch_id
        cache_key = (int(user_id), cid)
        cached_time = temp.FSUB_CACHE.get(cache_key)
        if cached_time and (time.time() - cached_time) < 300:
            return None
        if await db.has_joined_channel(user_id, ch_id):
            temp.FSUB_CACHE[cache_key] = time.time()
            return None
        try:
            member = await client.get_chat_member(ch_id, user_id)
            if member.status != enums.ChatMemberStatus.BANNED:
                await db.add_join_req(user_id, ch_id)
                temp.FSUB_CACHE[cache_key] = time.time()
                return None
        except UserNotParticipant:
            temp.FSUB_CACHE.pop(cache_key, None)
            pass
        except Exception as e:
            logger.error(f"Error checking membership in {ch_id}: {e}")

        try:
            chat = await client.get_chat(ch_id)
            if ch_id in temp.REQ_LINKS:
                invite_link = temp.REQ_LINKS[ch_id]
            else:
                invite = await client.create_chat_invite_link(
                    ch_id,
                    creates_join_request=True
                )
                invite_link = invite.invite_link
                temp.REQ_LINKS[ch_id] = invite_link

            return [InlineKeyboardButton(f"⛔️ Join {chat.title}", url=invite_link)]
        except ChatAdminRequired:
            logger.warning(f"Bot not admin in {ch_id}")
        except Exception as e:
            logger.warning(f"Invite link error for {ch_id}: {e}")
        return None

    tasks = [check_req_channel(ch_id) for ch_id in rqfsub_channels]
    results = await asyncio.gather(*tasks)

    for res in results:
        if res:
            btn.append(res)

    return btn

async def is_subscribed(client, user_id, fsub_channels):
    btn = []
    
    async def check_channel(channel_id):
        try:
            cid = int(channel_id)
        except Exception:
            cid = channel_id
        cache_key = (int(user_id), cid)
        cached_time = temp.FSUB_CACHE.get(cache_key)
        if cached_time and (time.time() - cached_time) < 300:
            return None
        try:
            # No need to get chat object separately
            await client.get_chat_member(channel_id, user_id)
            temp.FSUB_CACHE[cache_key] = time.time()
        except UserNotParticipant:
            temp.FSUB_CACHE.pop(cache_key, None)
            try:
                chat = await client.get_chat(int(channel_id))
                invite_link = await client.create_chat_invite_link(channel_id)
                return InlineKeyboardButton(f"📢 Join {chat.title}", url=invite_link.invite_link)
            except Exception as e:
                logger.warning(f"Failed to create invite for {channel_id}: {e}")
        except Exception as e:
            logger.exception(f"is_subscribed error for {channel_id}: {e}")
        return None

    tasks = [check_channel(channel_id) for channel_id in fsub_channels]
    results = await asyncio.gather(*tasks)

    for button in results:
        if button:
            btn.append([button])
            
    return btn

async def is_check_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except Exception:
        return False
    
async def users_broadcast(user_id, message, is_pin):
    try:
        m = await message.copy(chat_id=user_id)
        if is_pin:
            await m.pin(both_sides=True)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await users_broadcast(user_id, message, is_pin)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logger.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logger.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logger.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        logger.error(f"[BROADCAST FAIL] user={user_id} | {type(e).__name__}: {e}")
        return False, "Error"


async def groups_broadcast(chat_id, message, is_pin):
    try:
        m = await message.copy(chat_id=chat_id)
        if is_pin:
            try:
                await m.pin()
            except Exception:
                pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await groups_broadcast(chat_id, message, is_pin)
    except Exception:
        await db.delete_chat(chat_id)
        return "Error"

async def junk_group(chat_id, message):
    try:
        kk = await message.copy(chat_id=chat_id)
        await kk.delete(True)
        return True, "Success", 'mm'
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await junk_group(chat_id, message)
    except Exception as e:
        await db.delete_chat(int(chat_id))       
        logger.info(f"{chat_id} - PeerIdInvalid")
        return False, "deleted", f'{e}\n\n'
    

async def clear_junk(user_id, message):
    try:
        key = await message.copy(chat_id=user_id)
        await key.delete(True)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await clear_junk(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logger.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logger.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logger.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception:
        return False, "Error"
     
def listx_to_str(k):
    if k is None or k == "":
        return "N/A"
    
    # Handle non-iterable types first
    if not hasattr(k, '__iter__') or isinstance(k, (str, int, float)):
        return str(k)
    
    result = []
    for elem in k:
        if elem and str(elem).strip():
            result.append(str(elem).strip())
    
    if MAX_LIST_ELM and len(result) > MAX_LIST_ELM:
        result = result[:int(MAX_LIST_ELM)]
    
    return ', '.join(result) if result else "N/A"
    
async def get_poster(query, bulk=False, id=False, file=None):
    if not id:
        query = (query.strip()).lower()
        title = query
        year_val = None
        
        year_list = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
        if year_list:
            year_val = year_list[0]
            title = (query.replace(year_val, "")).strip()
        elif file is not None:
            year_list = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
            if year_list:
                year_val = year_list[0]
        
        search_result = await asyncio.to_thread(imdb.search_movie, title.lower())
        if not search_result or not search_result.titles:
            return None
        
        movie_list = search_result.titles[:MAX_LIST_ELM]
        
        if year_val:
            filtered = [m for m in movie_list if m.year and str(m.year) == str(year_val)]
            if not filtered:
                filtered = movie_list
        else:
            filtered = movie_list
            
        kind_filter = ['movie', 'tv series', 'tvSeries', 'tvMiniSeries', 'tvMovie']
        filtered_kind = [m for m in filtered if m.kind and m.kind in kind_filter]
        
        if not filtered_kind:
            filtered_kind = filtered
        
        if bulk:
            return filtered_kind[:MAX_LIST_ELM]
        if not filtered_kind:
            return None   
        movie_brief = filtered_kind[0]
        movieid_str = movie_brief.imdb_id 
    else:
        movieid_str = query

    movie = await asyncio.to_thread(imdb.get_movie, movieid_str)
    if not movie:
        return None

    if movie.release_date:
        date = movie.release_date
    elif movie.year:
        date = str(movie.year)
    else:
        date = "N/A"
        
    plot = movie.plot[0] if isinstance(movie.plot, list) else movie.plot or ""
    if len(plot) > 800:
        plot = plot[:800] + "..."
    imdb_id = movie.imdb_id
    if not imdb_id.startswith("tt"):
        imdb_id = f"tt{imdb_id}"
    return {
        'title': movie.title,
        'votes': movie.votes,
        "aka": listx_to_str(movie.title_akas),
        "seasons": (
            len(movie.info_series.display_seasons)
            if getattr(movie, "info_series", None)
            and getattr(movie.info_series, "display_seasons", None)
            else "N/A"
        ),
        "box_office": movie.worldwide_gross,
        'localized_title': movie.title_localized,
        'kind': movie.kind,
        "imdb_id": imdb_id,
        "cast": listx_to_str(movie.stars),
        "runtime": listx_to_str(movie.duration),
        "countries": listx_to_str(movie.countries),
        "certificates": listx_to_str(movie.certificates),
        "languages": listx_to_str(movie.languages),
        "director": listx_to_str(movie.directors),
        "writer": listx_to_str([p.name for p in movie.writers]),
        "producer": listx_to_str([p.name for p in movie.producers]),
        "composer": listx_to_str([p.name for p in movie.composers]),
        "cinematographer": listx_to_str([p.name for p in movie.cinematographers]),
        "music_team": listx_to_str([p.name for p in movie.music_team]),
        "distributors": listx_to_str([c.name for c in movie.distributors]),        
        'release_date': date,
        'year': movie.year,
        'genres': listx_to_str(movie.genres),
        'poster': movie.cover_url,
        'plot': plot,
        'rating': str(movie.rating),
        "url": movie.url or f"https://www.imdb.com/title/{imdb_id}"
    }
    
async def get_posterx(query, bulk=False, id=False, file=None):
    """
    Fetches movie details from TMDB using the get_movie_detailsx helper
    and formats the output to be compatible with the original get_poster function.
    """
    if not id:
        # The get_movie_detailsx function handles searching by query string.
        details = await get_movie_detailsx(query, file=file)
    else:
        # Assumes the 'id' is a TMDB ID or IMDb ID that get_movie_detailsx can handle.
        details = await get_movie_detailsx(query, id=True)

    if not details or details.get("error"):
        return None
    
    plot = ""
    if not LONG_IMDB_DESCRIPTION:
        plot = details.get('plot')
        if plot and len(plot) > 0:
            plot = plot[0]
    else:
        plot = details.get('plot outline')
    if plot and len(plot) > 800:
        plot = plot[0:800] + "..."

    # --- Mapping TMDB keys to the original IMDb key format ---

    def list_to_str(val):
        if isinstance(val, list):
            return ", ".join(str(x) for x in val if x)
        return str(val) if val else ""

    return {
        'title': details.get('title'),
        'votes': details.get('votes'),
        "aka": None,  # Not typically provided by TMDB in this format
        "seasons": details.get('seasons'),
        "box_office": details.get('box_office'),
        'localized_title': details.get('localized_title'),
        'kind': 'movie' if 'movie' in details.get('tmdb_url', '') else 'tv series',
        "imdb_id": details.get('imdb_id'),
        "cast": list_to_str(details.get("cast")),
        "runtime": list_to_str(details.get("runtime")),
        "countries": list_to_str(details.get("countries")),
        "certificates": list_to_str(details.get("certificates")),
        "languages": list_to_str(details.get("languages")),
        "director": list_to_str(details.get("director")),
        "writer": list_to_str(details.get("writer")),
        "producer": list_to_str(details.get("producer")),
        "composer": list_to_str(details.get("composer")),
        "cinematographer": list_to_str(details.get("cinematographer")),
        "music_team": None, # Not provided by the TMDB API wrapper
        "distributors": list_to_str(details.get("distributors")),
        'release_date': details.get('release_date'),
        'year': details.get('year'),
        'genres': list_to_str(details.get("genres")),
        'poster': details.get('poster_url'),
        'backdrop' : details.get('backdrop_url'),
        'plot': plot,
        'rating': str(details.get("rating", "N/A")),
        'url': details.get('tmdb_url')
    }
    
async def get_shortlink(link, grp_id, is_second_shortener=False, is_third_shortener=False):
    settings = await get_settings(grp_id)
    if is_third_shortener:             
        api, site = settings['api_three'], settings['shortner_three']
    else:
        if is_second_shortener:
            api, site = settings['api_two'], settings['shortner_two']
        else:
            api, site = settings['api'], settings['shortner']
    shortzy = Shortzy(api, site)
    try:
        link = await shortzy.convert(link)
    except Exception:
        link = await shortzy.get_quick_link(link)
    return link

async def get_settings(group_id):
    try:
        group_id = int(group_id)
    except (ValueError, TypeError):
        group_id = 0
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS[group_id] = settings.copy()
    return settings
    
async def save_group_settings(group_id, key, value):
    group_id = int(group_id)
    current = await get_settings(group_id)
    current = current.copy()
    current.update({key: value})
    temp.SETTINGS[group_id] = current
    await db.update_settings(group_id, current)

async def delete_group_setting(group_id, key):
    group_id = int(group_id)
    current = await get_settings(group_id)
    current = current.copy()
    if key in current:
        current.pop(key)
        temp.SETTINGS[group_id] = current
        await db.update_settings(group_id, current)

def clean_filename(file_name):
    return ' '.join(
        word for word in file_name.split()
        if not (word.startswith(_CLEAN_FILENAME_PREFIXES) or word.lower() in _UNWANTED_BAD_WORDS)
    )

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def extract_request_content(message_text):
    match = _REQUEST_UNDERLINE_REGEX.search(message_text)
    if match:
        return match.group(1).strip()
    match = _REQUEST_PREFIX_REGEX.search(message_text)
    if match:
        return match.group(1).strip()
    return message_text.strip()

def generate_settings_text(settings, title, reset_done=False):
    note = "\n<b>📌 ɴᴏᴛᴇ :- ʀᴇꜱᴇᴛ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ✅</b>" if reset_done else ""
    return f"""<b>⚙️ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ꜰᴏʀ - {title}</b>

✅️ <b><u>1sᴛ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ</u></b>
<b>ɴᴀᴍᴇ</b> - <code>{settings.get("shortner", "N/A")}</code>
<b>ᴀᴘɪ</b> - <code>{settings.get("api", "N/A")}</code>

✅️ <b><u>2ɴᴅ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ</u></b>
<b>ɴᴀᴍᴇ</b> - <code>{settings.get("shortner_two", "N/A")}</code>
<b>ᴀᴘɪ</b> - <code>{settings.get("api_two", "N/A")}</code>

✅️ <b><u>𝟹ʀᴅ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ</u></b>
<b>ɴᴀᴍᴇ</b> - <code>{settings.get("shortner_three", "N/A")}</code>
<b>ᴀᴘɪ</b> - <code>{settings.get("api_three", "N/A")}</code>

⏰ <b>2ɴᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ</b> - <code>{settings.get("verify_time", "N/A")}</code>
⏰ <b>𝟹ʀᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ</b> - <code>{settings.get("third_verify_time", "N/A")}</code>

1️⃣ <b>ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ 1</b> - {settings.get("tutorial", TUTORIAL)}
2️⃣ <b>ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ 2</b> - {settings.get("tutorial_2", TUTORIAL_2)}
3️⃣ <b>ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ 3</b> - {settings.get("tutorial_3", TUTORIAL_3)}

📝 <b>ʟᴏɢ ᴄʜᴀɴɴᴇʟ ɪᴅ</b> - <code>{settings.get("log", "N/A")}</code>
🚫 <b>ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ ɪᴅ</b> - <code>{settings.get("fsub", "N/A")}</code>


🎯 <b>ɪᴍᴅʙ ᴛᴇᴍᴘʟᴀᴛᴇ</b> - <code>{settings.get("template", "N/A")}</code>

📂 <b>ꜰɪʟᴇ ᴄᴀᴘᴛɪᴏɴ</b> - <code>{settings.get("caption", "N/A")}</code>
{note}
"""

async def get_settings_text(grp_id, title):
    settings = await get_settings(grp_id)
    verify_status = settings.get('is_verify', IS_VERIFY)
    verify_text = "ᴏɴ" if verify_status else "ᴏꜰꜰ"
    log_channel = settings.get('log')
    log_text = f"<code>{log_channel}</code>" if log_channel else "ɴᴏᴛ ꜱᴇᴛ"
    fsub_ids = settings.get('fsub')
    if fsub_ids:
        if isinstance(fsub_ids, list):
            fsub_text = ", ".join([f"<code>{id}</code>" for id in fsub_ids])
        else:
            fsub_text = f"<code>{fsub_ids}</code>"
    else:
        fsub_text = "ɴᴏᴛ ꜱᴇᴛ"
    text = (
        f"<b>ᴄʜᴀɴɢᴇ ʏᴏᴜʀ ꜱᴇᴛᴛɪɴɢꜱ ꜰᴏʀ {title} ᴀꜱ ʏᴏᴜ ᴡɪꜱʜ ⚙\n\n"
        f"✅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ : {verify_text}\n"
        f"📝 ʟᴏɢ ᴄʜᴀɴɴᴇʟ : {log_text}\n"
        f"🚫 ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ : {fsub_text}</b>"
    )
    return text

async def group_setting_buttons(grp_id):
    settings = await get_settings(grp_id)
    buttons = [[
                InlineKeyboardButton('ʀᴇꜱᴜʟᴛ ᴘᴀɢᴇ', callback_data=f'setgs#button#{settings.get("button")}#{grp_id}',),
                InlineKeyboardButton('ʙᴜᴛᴛᴏɴ' if settings.get("button") else 'ᴛᴇxᴛ', callback_data=f'setgs#button#{settings.get("button")}#{grp_id}',),
            ],[
                InlineKeyboardButton('ꜰɪʟᴇ ꜱᴇᴄᴜʀᴇ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',),
                InlineKeyboardButton('✔ Oɴ' if settings["file_secure"] else '✘ Oғғ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',),
            ],[
                InlineKeyboardButton('ɪᴍᴅʙ ᴘᴏꜱᴛᴇʀ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',),
                InlineKeyboardButton('✔ Oɴ' if settings["imdb"] else '✘ Oғғ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',),
            ],[
                InlineKeyboardButton('ᴡᴇʟᴄᴏᴍᴇ ᴍꜱɢ', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',),
                InlineKeyboardButton('✔ Oɴ' if settings["welcome"] else '✘ Oғғ', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',),
            ],[
                InlineKeyboardButton('ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',),
                InlineKeyboardButton('✔ Oɴ' if settings["auto_delete"] else '✘ Oғғ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',),
            ],[
                InlineKeyboardButton('ᴍᴀx ʙᴜᴛᴛᴏɴꜱ', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',),
                InlineKeyboardButton('10' if settings["max_btn"] else f'{MAX_B_TN}', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',),
            ],[
                InlineKeyboardButton('ꜱᴘᴇʟʟ ᴄʜᴇᴄᴋ',callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                InlineKeyboardButton('✔ Oɴ' if settings["spell_check"] else '✘ Oғғ',callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
            ],[
                InlineKeyboardButton('Vᴇʀɪғʏ', callback_data=f'setgs#is_verify#{settings.get("is_verify", IS_VERIFY)}#{grp_id}'),
                InlineKeyboardButton('✔ Oɴ' if settings.get("is_verify", IS_VERIFY) else '✘ Oғғ', callback_data=f'setgs#is_verify#{settings.get("is_verify", IS_VERIFY)}#{grp_id}'),
            ],[
                InlineKeyboardButton('ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ', callback_data=f'verification_setgs#{grp_id}'),
                InlineKeyboardButton('ʟᴏɢ ᴄʜᴀɴɴᴇʟ', callback_data=f'log_setgs#{grp_id}'),
            ],[
                InlineKeyboardButton('ꜱᴇᴛ ᴄᴀᴘᴛɪᴏɴ', callback_data=f'caption_setgs#{grp_id}'),
                InlineKeyboardButton('ᴄᴜꜱᴛᴏᴍ ꜰꜱᴜʙ', callback_data=f'fsub_setgs#{grp_id}'),
            ],[
                InlineKeyboardButton("Dᴇʟᴇᴛᴇ Gʀᴏᴜᴘ", callback_data=f"delete_group_check#{grp_id}", style=enums.ButtonStyle.DANGER)
            ],[
                InlineKeyboardButton('⇋ ᴄʟᴏꜱᴇ ꜱᴇᴛᴛɪɴɢꜱ ᴍᴇɴᴜ ⇋', callback_data='close_data', style=enums.ButtonStyle.DANGER)
    ]]
    return buttons

def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj

def extract_user(message: Message) -> Union[int, str]:
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name

    elif len(message.command) > 1:
        if (
            len(message.entities) > 1 and
            message.entities[1].type == enums.MessageEntityType.TEXT_MENTION
        ):
           
            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            # don't want to make a request -_-
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)


def get_time(seconds):
    periods = [(' ᴅᴀʏs', 86400), (' ʜᴏᴜʀ', 3600), (' ᴍɪɴᴜᴛᴇ', 60), (' sᴇᴄᴏɴᴅ', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result
    

def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f'{int(period_value)}{period_name}')
    return ' '.join(result)  

def generate_season_variations(search_raw: str, season_number: int):
    return [
        f"{search_raw} s{season_number:02}",
        f"{search_raw} season {season_number}",
        f"{search_raw} season {season_number:02}",
    ]



async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:].lstrip()
        if value:
            value = int(value)
        return value, unit
    value, unit = extract_value_and_unit(time_string)
    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0
    

def clean_search_text(search_raw: str) -> str:
    search_lower = search_raw.lower()
    phrases = _PHRASES_SPLIT_REGEX.split(search_lower.strip())
    cleaned_phrases = []
    for phrase in phrases:
        phrase = _SEASON_REGEX.sub('', phrase)
        phrase = _LANG_REGEX.sub('', phrase)
        phrase = _QUALITY_REGEX.sub('', phrase)
        phrase = _MULTI_SPACE_REGEX.sub(' ', phrase).strip()
        if phrase:
            cleaned_phrases.append(phrase)
    unique_phrases = []
    seen = set()
    for cp in cleaned_phrases:
        if cp not in seen:
            unique_phrases.append(cp)
            seen.add(cp)
    if unique_phrases:
        return unique_phrases[0].title()
    else:
        return ""

async def get_cap(settings, remaining_seconds, files, query, total_results, search, offset=0):
    try:
        if settings["imdb"]:
            IMDB_CAP = temp.IMDB_CAP.get(query.from_user.id)
            if IMDB_CAP:
                cap = IMDB_CAP
                cap += "\n\n<u>Your Requested Files Are Here</u>\n\n</b>"
                for idx, file in enumerate(files, start=offset + 1):
                        cap += (
                            f"<b>{idx}. "
                            f"<a href='https://telegram.me/{temp.U_NAME}"
                            f"?start=file_{query.message.chat.id}_{file.file_id}'>"
                            f"[{get_size(file.file_size)}] "
                            f"{clean_filename(file.file_name)}\n\n"
                            f"</a></b>"
                        )
            else:
                if settings["imdb"]:
                    imdb = await get_posterx(search, file=(files[0]).file_name) if TMDB_ON_SEARCH else await get_poster(search, file=(files[0]).file_name)
                else:
                    imdb = None
                if imdb:
                    TEMPLATE = script.IMDB_TEMPLATE_TXT
                    cap = TEMPLATE.format(
                        query=search, 
                        title=imdb['title'],
                        votes=imdb['votes'],
                        aka=imdb["aka"],
                        seasons=imdb["seasons"],
                        box_office=imdb['box_office'],
                        localized_title=imdb['localized_title'],
                        kind=imdb['kind'],
                        imdb_id=imdb["imdb_id"],
                        cast=imdb["cast"],
                        runtime=imdb["runtime"],
                        countries=imdb["countries"],
                        certificates=imdb["certificates"],
                        languages=imdb["languages"],
                        director=imdb["director"],
                        writer=imdb["writer"],
                        producer=imdb["producer"],
                        composer=imdb["composer"],
                        cinematographer=imdb["cinematographer"],
                        music_team=imdb["music_team"],
                        distributors=imdb["distributors"],
                        release_date=imdb['release_date'],
                        year=imdb['year'],
                        genres=imdb['genres'],
                        poster=imdb['poster'],
                        plot=imdb['plot'],
                        rating=imdb['rating'],
                        url=imdb['url'],
                        **locals()
                    )
                    
                    for idx, file in enumerate(files, start=offset+1):
                        cap += (
                            f"<b>{idx}. "
                            f"<a href='https://telegram.me/{temp.U_NAME}"
                            f"?start=file_{query.message.chat.id}_{file.file_id}'>"
                            f"[{get_size(file.file_size)}] "
                            f"{clean_filename(file.file_name)}\n\n"
                            f"</a></b>"
                        )
                else:
                    if ULTRA_FAST_MODE:
                        cap = (
                            f"<b>🏷 ᴛɪᴛʟᴇ : <code>{search}</code>\n"
                            f"⏰ ʀᴇsᴜʟᴛ ɪɴ : <code>{remaining_seconds} Sᴇᴄᴏɴᴅs</code>\n\n"
                            f"📝 ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ : {query.from_user.mention}\n"
                            f"⚜️ ᴘᴏᴡᴇʀᴇᴅ ʙʏ :⚡ {query.message.chat.title or temp.B_LINK or 'ᴅʀᴇᴀᴍxʙᴏᴛᴢ'}\n</b>"
                        )
                    else:
                        cap = (
                            f"<b>🏷 ᴛɪᴛʟᴇ : <code>{search}</code>\n"
                            f"🧱 ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ : <code>{total_results}</code>\n"
                            f"⏰ ʀᴇsᴜʟᴛ ɪɴ : <code>{remaining_seconds} Sᴇᴄᴏɴᴅs</code>\n\n"
                            f"📝 ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ : {query.from_user.mention}\n"
                            f"⚜️ ᴘᴏᴡᴇʀᴇᴅ ʙʏ :⚡ {query.message.chat.title or temp.B_LINK or 'ᴅʀᴇᴀᴍxʙᴏᴛᴢ'}\n</b>"
                        )
                    cap += "\n\n<u>Your Requested Files Are Here</u> \n\n</b>"
                    for idx, file in enumerate(files, start=offset + 1):
                        cap += (
                            f"<b>{idx}. "
                            f"<a href='https://telegram.me/{temp.U_NAME}"
                            f"?start=file_{query.message.chat.id}_{file.file_id}'>"
                            f"[{get_size(file.file_size)}] "
                            f"{clean_filename(file.file_name)}\n\n"
                            f"</a></b>"
                        )

        else:
            if ULTRA_FAST_MODE:
                cap = (
                    f"<b>🏷 ᴛɪᴛʟᴇ : <code>{search}</code>\n"
                    f"⏰ ʀᴇsᴜʟᴛ ɪɴ : <code>{remaining_seconds} Sᴇᴄᴏɴᴅs</code>\n\n"
                    f"⚜️ ᴘᴏᴡᴇʀᴇᴅ ʙʏ : ⚡ {query.message.chat.title or temp.B_LINK or 'ᴅʀᴇᴀᴍxʙᴏᴛᴢ'}\n</b>"
                )
            else:
                cap = (
                    f"<b>🏷 ᴛɪᴛʟᴇ : <code>{search}</code>\n"
                    f"🧱 ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ : <code>{total_results}</code>\n"
                    f"⏰ ʀᴇsᴜʟᴛ ɪɴ : <code>{remaining_seconds} Sᴇᴄᴏɴᴅs</code>\n\n"
                    f"📝 ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ : {query.from_user.mention}\n"
                    f"⚜️ ᴘᴏᴡᴇʀᴇᴅ ʙʏ : ⚡ {query.message.chat.title or temp.B_LINK or 'ᴅʀᴇᴀᴍxʙᴏᴛᴢ'}\n</b>"
                )

            cap += "\n\n<u>Your Requested Files Are Here</u>\n\n</b>"
            for idx, file in enumerate(files, start=offset + 1):
                        cap += (
                            f"<b>{idx}. "
                            f"<a href='https://telegram.me/{temp.U_NAME}"
                            f"?start=file_{query.message.chat.id}_{file.file_id}'>"
                            f"[{get_size(file.file_size)}] "
                            f"{clean_filename(file.file_name)}\n\n"
                            f"</a></b>"
                        )
        return cap
    except Exception as e:
        logger.error(f"Error in get_cap: {e}")
        pass


