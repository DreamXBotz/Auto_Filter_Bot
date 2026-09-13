import asyncio
import re
import math
import logging
import random
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified, FloodWait
from Script import script
from database.ia_filterdb import get_search_results, get_file_details
from database.users_chats_db import db
from info import PICS, PICS_URL, DELETE_TIME
from utils import get_settings, get_size, temp

logger = logging.getLogger(__name__)
BUTTONS = {}
CAP = {}

LANGUAGES = ["hindi", "english", "tamil", "telugu", "kannada", "malayalam", "bengali", "marathi", "gujarati", "punjabi"]
QUALITIES = ["360p", "480p", "720p", "1080p", "1440p", "2160p"]
SEASONS = ["season 1", "season 2", "season 3", "season 4", "season 5", "season 6", "season 7", "season 8", "season 9", "season 10"]

@Client.on_message((filters.text & filters.group & filters.incoming & ~filters.command(["start", "help", "about", "id", "settings", "fsub", "post", "delete", "del"])) | (filters.text & filters.private & filters.incoming & ~filters.command(["start", "help", "about", "id", "settings", "fsub", "post", "delete", "del"])))
async def give_filter(client, message):
    await auto_filter(client, message)

async def auto_filter(client, message):
    try:
        if message.text.startswith("/"):
            return
        if re.findall(r"((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if len(message.text) < 2:
            return
        search = message.text.strip()
        if len(search) > 100:
            search = search[:100]

        files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
        if not files:
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=False)
        if not files:
            logger.info(f"No files for {search}")
            return

        try:
            settings = await get_settings(message.chat.id)
        except:
            settings = {'auto_delete': False}

        req = message.from_user.id if message.from_user else 0
        temp.GETALL[search] = files

        btn = []
        btn.append([
            InlineKeyboardButton("ǫᴜᴀʟɪᴛɪᴇs", callback_data=f"qualities#{search}#{req}"),
            InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{search}#{req}"),
            InlineKeyboardButton("sᴇᴀsᴏɴs", callback_data=f"seasons#{search}#{req}")
        ])
        btn.append([InlineKeyboardButton("sᴇɴᴅ ᴀʟʟ ғɪʟᴇs", callback_data=f"sendall#{search}#{req}")])
        for file in files:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            file_id = file.file_id
            btn.append([InlineKeyboardButton(f"[{f_size}] {f_name[:40]}", callback_data=f"file#{file_id}#{req}")])
        if offset != "":
            btn.append([InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"next_{req}_{search}_{offset}")])
        else:
            btn.append([InlineKeyboardButton("ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs", callback_data="pages")])

        try:
            pic_url = random.choice(PICS_URL) if PICS_URL else random.choice(PICS)
        except:
            try:
                pic_url = random.choice(PICS)
            except:
                pic_url = None

        imdb = await get_poster(search, file=(files[0].file_name if files else None))
        if imdb and imdb.get('poster'):
            try:
                cap = script.IMDB_TEMPLATE.format(
                    qurey=search,
                    title=imdb.get('title'),
                    votes=imdb.get('votes'),
                    aka=imdb.get("aka"),
                    seasons=imdb.get("seasons"),
                    box_office=imdb.get('box_office'),
                    localized_title=imdb.get('localized_title'),
                    kind=imdb.get('kind'),
                    imdb_id=imdb.get("imdb_id"),
                    cast=imdb.get("cast"),
                    runtime=imdb.get("runtime"),
                    countries=imdb.get("countries"),
                    certificates=imdb.get("certificates"),
                    languages=imdb.get("languages"),
                    director=imdb.get("director"),
                    writer=imdb.get("writer"),
                    producer=imdb.get("producer"),
                    composer=imdb.get("composer"),
                    cinematographer=imdb.get("cinematographer"),
                    music_team=imdb.get("music_team"),
                    distributors=imdb.get("distributors"),
                    release_date=imdb.get('release_date'),
                    year=imdb.get('year'),
                    genres=imdb.get('genres'),
                    poster=imdb.get('poster'),
                    plot=imdb.get('plot'),
                    rating=imdb.get('rating'),
                    url=imdb.get('url'),
                )
            except Exception as e:
                logger.exception(e)
                cap = f"<b>Here is what I found for your query {search} :</b>"
        else:
            cap = f"<b>Here is what I found for your query {search} :</b>"

        try:
            if pic_url:
                sent = await message.reply_photo(photo=pic_url, caption=cap, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
            else:
                sent = await message.reply_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
            try:
                if settings.get('auto_delete'):
                    await asyncio.sleep(DELETE_TIME)
                    await sent.delete()
                    await message.delete()
            except:
                pass
        except Exception as e:
            logger.exception(f"send error: {e}")
    except Exception as e:
        logger.exception(f"auto_filter error for {message.text}: {e}")

async def get_poster(query, bulk=False, id=False, file=None):
    from utils import get_poster as _get_poster, get_posterx
    try:
        return await _get_poster(query, bulk, id, file)
    except:
        try:
            return await get_posterx(query, bulk, id, file)
        except:
            return None

@Client.on_callback_query(filters.regex(r"^next_"))
async def next_page(bot, query):
    try:
        _, req, key, offset = query.data.split("_")
        req = int(req)
        if req != 0 and query.from_user.id != req:
            return await query.answer("This is not for you!", show_alert=True)
        search = key
        offset = int(offset)
        files, n_offset, total = await get_search_results(search.lower(), offset=offset, filter=True)
        if not files:
            return
        btn = []
        btn.append([
            InlineKeyboardButton("ǫᴜᴀʟɪᴛɪᴇs", callback_data=f"qualities#{search}#{req}"),
            InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{search}#{req}"),
            InlineKeyboardButton("sᴇᴀsᴏɴs", callback_data=f"seasons#{search}#{req}")
        ])
        btn.append([InlineKeyboardButton("sᴇɴᴅ ᴀʟʟ ғɪʟᴇs", callback_data=f"sendall#{search}#{req}")])
        for file in files:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            file_id = file.file_id
            btn.append([InlineKeyboardButton(f"[{f_size}] {f_name[:40]}", callback_data=f"file#{file_id}#{req}")])
        if n_offset != "":
            btn.append([
                InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"next_{req}_{search}_{offset-10}" if offset-10 >=0 else f"next_{req}_{search}_0"),
                InlineKeyboardButton(f"{math.ceil(offset/10)+1}/{math.ceil(total/10)}", callback_data="pages"),
                InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"next_{req}_{search}_{n_offset}")
            ])
        else:
            btn.append([
                InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"next_{req}_{search}_{offset-10}"),
                InlineKeyboardButton(f"{math.ceil(offset/10)+1}/{math.ceil(total/10)}", callback_data="pages")
            ])
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        except MessageNotModified:
            pass
        await query.answer()
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^qualities#"))
async def qualities_cb(bot, query):
    try:
        _, key, req = query.data.split("#")
        req = int(req)
        if req != 0 and query.from_user.id != req:
            return await query.answer("This is not for you!", show_alert=True)
        btn = []
        for qual in QUALITIES:
            btn.append([InlineKeyboardButton(qual, callback_data=f"q_filter#{qual}#{key}#{req}")])
        btn.append([InlineKeyboardButton("⇋ ʙᴀᴄᴋ ⇋", callback_data=f"filter_back#{key}#{req}")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        await query.answer()
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^languages#"))
async def languages_cb(bot, query):
    try:
        _, key, req = query.data.split("#")
        req = int(req)
        if req != 0 and query.from_user.id != req:
            return await query.answer("This is not for you!", show_alert=True)
        btn = []
        for lang in LANGUAGES:
            btn.append([InlineKeyboardButton(lang, callback_data=f"l_filter#{lang}#{key}#{req}")])
        btn.append([InlineKeyboardButton("⇋ ʙᴀᴄᴋ ⇋", callback_data=f"filter_back#{key}#{req}")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        await query.answer()
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^seasons#"))
async def seasons_cb(bot, query):
    try:
        _, key, req = query.data.split("#")
        req = int(req)
        if req != 0 and query.from_user.id != req:
            return await query.answer("This is not for you!", show_alert=True)
        btn = []
        for seas in SEASONS:
            btn.append([InlineKeyboardButton(seas, callback_data=f"s_filter#{seas}#{key}#{req}")])
        btn.append([InlineKeyboardButton("⇋ ʙᴀᴄᴋ ⇋", callback_data=f"filter_back#{key}#{req}")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        await query.answer()
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^q_filter#"))
async def q_filter_cb(bot, query):
    try:
        _, qual, key, req = query.data.split("#")
        req = int(req)
        if req != 0 and query.from_user.id != req:
            return await query.answer("This is not for you!", show_alert=True)
        files = temp.GETALL.get(key)
        if not files:
            return await query.answer("No files found!", show_alert=True)
        filtered = [f for f in files if qual.lower() in f.file_name.lower()]
        if not filtered:
            return await query.answer(f"No files found for quality {qual}", show_alert=True)
        btn = []
        btn.append([InlineKeyboardButton(f"Filtered by {qual}", callback_data="pages")])
        for file in filtered[:10]:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            file_id = file.file_id
            btn.append([InlineKeyboardButton(f"[{f_size}] {f_name[:40]}", callback_data=f"file#{file_id}#{req}")])
        btn.append([InlineKeyboardButton("⇋ ʙᴀᴄᴋ ⇋", callback_data=f"filter_back#{key}#{req}")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        await query.answer()
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^l_filter#"))
async def l_filter_cb(bot, query):
    try:
        _, lang, key, req = query.data.split("#")
        req = int(req)
        if req != 0 and query.from_user.id != req:
            return await query.answer("This is not for you!", show_alert=True)
        files = temp.GETALL.get(key)
        if not files:
            return await query.answer("No files found!", show_alert=True)
        filtered = [f for f in files if lang.lower() in f.file_name.lower()]
        if not filtered:
            return await query.answer(f"No files found for language {lang}", show_alert=True)
        btn = []
        btn.append([InlineKeyboardButton(f"Filtered by {lang}", callback_data="pages")])
        for file in filtered[:10]:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            file_id = file.file_id
            btn.append([InlineKeyboardButton(f"[{f_size}] {f_name[:40]}", callback_data=f"file#{file_id}#{req}")])
        btn.append([InlineKeyboardButton("⇋ ʙᴀᴄᴋ ⇋", callback_data=f"filter_back#{key}#{req}")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        await query.answer()
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^s_filter#"))
async def s_filter_cb(bot, query):
    try:
        _, seas, key, req = query.data.split("#")
        req = int(req)
        if req != 0 and query.from_user.id != req:
            return await query.answer("This is not for you!", show_alert=True)
        files = temp.GETALL.get(key)
        if not files:
            return await query.answer("No files found!", show_alert=True)
        filtered = [f for f in files if seas.lower() in f.file_name.lower()]
        if not filtered:
            num = ''.join(filter(str.isdigit, seas))
            if num:
                filtered = [f for f in files if f"S{int(num):02d}" in f.file_name or f"S{num}" in f.file_name]
        if not filtered:
            return await query.answer(f"No files found for {seas}", show_alert=True)
        btn = []
        btn.append([InlineKeyboardButton(f"Filtered by {seas}", callback_data="pages")])
        for file in filtered[:10]:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            file_id = file.file_id
            btn.append([InlineKeyboardButton(f"[{f_size}] {f_name[:40]}", callback_data=f"file#{file_id}#{req}")])
        btn.append([InlineKeyboardButton("⇋ ʙᴀᴄᴋ ⇋", callback_data=f"filter_back#{key}#{req}")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        await query.answer()
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^filter_back#"))
async def filter_back_cb(bot, query):
    try:
        _, key, req = query.data.split("#")
        req = int(req)
        if req != 0 and query.from_user.id != req:
            return await query.answer("This is not for you!", show_alert=True)
        files = temp.GETALL.get(key, [])
        btn = []
        btn.append([
            InlineKeyboardButton("ǫᴜᴀʟɪᴛɪᴇs", callback_data=f"qualities#{key}#{req}"),
            InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#{req}"),
            InlineKeyboardButton("sᴇᴀsᴏɴs", callback_data=f"seasons#{key}#{req}")
        ])
        btn.append([InlineKeyboardButton("sᴇɴᴅ ᴀʟʟ ғɪʟᴇs", callback_data=f"sendall#{key}#{req}")])
        for file in files[:10]:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            file_id = file.file_id
            btn.append([InlineKeyboardButton(f"[{f_size}] {f_name[:40]}", callback_data=f"file#{file_id}#{req}")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        await query.answer()
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^file#"))
async def file_cb(bot, query):
    try:
        _, file_id, req = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer("No such file exist.", show_alert=True)
        try:
            await bot.send_cached_media(chat_id=query.from_user.id, file_id=file_id, caption=files_.file_name)
            await query.answer("Check PM, I have sent files in PM", show_alert=False)
        except Exception:
            await query.answer("Failed to send in PM, make sure you started me in PM", show_alert=True)
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^about"))
async def about_cb(bot, query):
    try:
        await query.answer()
    except:
        pass
    try:
        b_name = getattr(temp, 'B_NAME', 'Boultflix') or 'Boultflix'
        u_name = getattr(temp, 'U_NAME', 'Boultflix') or 'Boultflix'
        about_text = script.ABOUT_TXT
        # fix bracket issue - replace {} with actual names
        try:
            about_text = about_text.format(b_name, u_name)
        except:
            about_text = about_text.replace("{}", b_name).replace("{0}", b_name).replace("{1}", u_name).replace("{2}", b_name)
        await query.message.edit_text(
            text=about_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="start"),
                 InlineKeyboardButton("🔐 ᴄʟᴏsᴇ", callback_data="close_data")]
            ])
        )
    except MessageNotModified:
        pass
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^help"))
async def help_cb(bot, query):
    try:
        await query.answer()
    except:
        pass
    try:
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="start"),
                 InlineKeyboardButton("🔐 ᴄʟᴏsᴇ", callback_data="close_data")]
            ])
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r"^start"))
async def start_cb(bot, query):
    try:
        await query.answer()
    except:
        pass
    try:
        b_name = getattr(temp, 'B_NAME', 'Boultflix') or 'Boultflix'
        u_name = getattr(temp, 'U_NAME', 'Boultflix') or 'Boultflix'
        mention = query.from_user.mention if query.from_user else "User"
        try:
            start_text = script.START_TXT.format(mention, u_name, b_name)
        except:
            try:
                start_text = script.START_TXT.format(mention, b_name)
            except:
                start_text = script.START_TXT
                start_text = start_text.replace("{0}", mention).replace("{1}", u_name).replace("{2}", b_name)
                # replace leftover {} sequentially
                if "{}" in start_text:
                    start_text = start_text.replace("{}", mention, 1)
                if "{}" in start_text:
                    start_text = start_text.replace("{}", b_name)
        buttons = [[
            InlineKeyboardButton('🔰 ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ 🔰', url=f'http://t.me/{u_name}?startgroup=true')
        ],[
            InlineKeyboardButton(' ʜᴇʟᴘ 📢', callback_data='help'),
            InlineKeyboardButton(' ᴀʙᴏᴜᴛ 📖', callback_data='about')
        ],[
            InlineKeyboardButton('ᴛᴏᴘ sᴇᴀʀᴄʜɪɴɢ ⭐', callback_data="topsearch"),
            InlineKeyboardButton('ᴜᴘɢʀᴀᴅᴇ 🎟', callback_data="premium_info"),
        ]]
        await query.message.edit_text(text=start_text, reply_markup=InlineKeyboardMarkup(buttons))
    except MessageNotModified:
        pass
    except Exception as e:
        logger.exception(e)

@Client.on_callback_query(filters.regex(r"^close_data"))
async def close_cb(bot, query):
    try:
        await query.message.delete()
    except:
        try:
            await query.message.edit_text("Closed")
        except:
            pass
    try:
        await query.answer()
    except:
        pass

@Client.on_callback_query(filters.regex(r"^pages"))
async def pages_cb(bot, query):
    await query.answer()

@Client.on_callback_query(filters.regex(r"^sendall#"))
async def sendall_cb(bot, query):
    try:
        _, key, req = query.data.split("#")
        req = int(req)
        if req != 0 and query.from_user.id != req:
            return await query.answer("This is not for you!", show_alert=True)
        files = temp.GETALL.get(key)
        if not files:
            return await query.answer("No files found", show_alert=True)
        await query.answer("Sending all files in PM...", show_alert=False)
        for file in files[:10]:
            try:
                await bot.send_cached_media(chat_id=query.from_user.id, file_id=file.file_id, caption=file.file_name)
                await asyncio.sleep(1)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except:
                pass
    except Exception as e:
        logger.exception(e)
