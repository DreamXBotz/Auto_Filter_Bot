import asyncio
import re
import ast
import math
import logging
import random
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified, FloodWait
from Script import script
from database.ia_filterdb import get_search_results, get_file_details, get_bad_files
from database.users_chats_db import db
from info import ADMINS, PICS, PICS_URL, AUTH_CHANNELS, DELETE_TIME, MAX_B_TN, IS_VERIFY, TUTORIAL, TUTORIAL_2, TUTORIAL_3, LOG_CHANNEL, SUPPORT_CHAT_ID
from utils import get_settings, get_size, is_subscribed, is_req_subscribed, get_shortlink, temp, get_readable_time

logger = logging.getLogger(__name__)
BUTTONS = {}
CAP = {}

# QUALITY AND LANGUAGE MAPS (same font as your bot)
LANGUAGES = ["malayalam", "mal", "tamil", "tam" ,"english", "eng", "hindi", "hin" ,"telugu", "tel" ,"kannada", "kan", "bengali", "ben", "marathi", "mar", "gujarati", "guj", "punjabi", "pun"]
QUALITIES = ["360p", "480p", "720p", "1080p", "1440p", "2160p"]
SEASONS = ["season 1" , "season 2" , "season 3" , "season 4", "season 5" , "season 6" , "season 7" , "season 8" , "season 9" , "season 10"]

@Client.on_message(filters.text & filters.group & filters.incoming & ~filters.command(["start", "help", "about", "id", "settings", "fsub", "post", "delete", "del"]))
async def give_filter(client, message):
    await auto_filter(client, message)

async def auto_filter(client, message):
    if message.text.startswith("/"):
        return
    if re.findall(r"((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
        return
    if 2 < len(message.text) < 100:
        search = message.text
        files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
        if not files:
            if temp.B_LINK:
                return
            # try with spell check - simplified
            return
        else:
            settings = await get_settings(message.chat.id)
            # req = requester id - THIS IS THE FIX for quality/language/session
            req = message.from_user.id if message.from_user else 0
            temp.GETALL[search] = files
            # store req for later use
            if not hasattr(temp, 'REQ_CACHE'):
                temp.REQ_CACHE = {}
            temp.REQ_CACHE[search] = req
            
            # create buttons
            btn = []
            # group setting buttons - qualities, languages, seasons
            btn.append([
                InlineKeyboardButton("ǫᴜᴀʟɪᴛɪᴇs", callback_data=f"qualities#{search}#{req}"),
                InlineKeyboardButton("ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{search}#{req}"),
                InlineKeyboardButton("sᴇᴀsᴏɴs", callback_data=f"seasons#{search}#{req}")
            ])
            btn.append([
                InlineKeyboardButton("sᴇɴᴅ ᴀʟʟ ғɪʟᴇs", callback_data=f"sendall#{search}#{req}")
            ])
            for file in files:
                f_name = file.file_name
                f_size = get_size(file.file_size)
                file_id = file.file_id
                btn.append([
                    InlineKeyboardButton(f"[{f_size}] {f_name[:40]}", callback_data=f"file#{file_id}#{req}")
                ])
            if offset != "":
                btn.append([
                    InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"next_{req}_{search}_{offset}")
                ])
            else:
                btn.append([
                    InlineKeyboardButton("ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs", callback_data="pages")
                ])
            
            # fix: try pics url then pics
            try:
                pic_url = random.choice(PICS_URL) if PICS_URL else random.choice(PICS)
            except:
                try:
                    pic_url = random.choice(PICS)
                except:
                    pic_url = None
            
            imdb = await get_poster(search, file=(files[0].file_name if files else None))
            if imdb and imdb.get('poster'):
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
            else:
                cap = f"<b>Here is what I found for your query {search} :</b>"
            
            BUTTONS[search] = cap
            CAP[search] = cap
            
            try:
                if pic_url:
                    sent = await message.reply_photo(photo=pic_url, caption=cap, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
                else:
                    sent = await message.reply_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
                # auto delete
                try:
                    if settings.get('auto_delete'):
                        await asyncio.sleep(DELETE_TIME)
                        await sent.delete()
                        await message.delete()
                except Exception:
                    pass
            except Exception as e:
                logger.exception(e)


async def get_poster(query, bulk=False, id=False, file=None):
    # import here to avoid circular
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
        # check req
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
        btn.append([
            InlineKeyboardButton("sᴇɴᴅ ᴀʟʟ ғɪʟᴇs", callback_data=f"sendall#{search}#{req}")
        ])
        for file in files:
            f_name = file.file_name
            f_size = get_size(file.file_size)
            file_id = file.file_id
            btn.append([
                InlineKeyboardButton(f"[{f_size}] {f_name[:40]}", callback_data=f"file#{file_id}#{req}")
            ])
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
        # create quality buttons
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
        for lang in LANGUAGES[:12]:
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
        # filter by quality
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
            # also check S01 etc
            num = ''.join(filter(str.isdigit, seas))
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
        req = int(req)
        # allow anyone to get file, but req check optional
        # if req !=0 and query.from_user.id != req:
        #    return await query.answer("This is not for you!", show_alert=True)
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer("No such file exist.", show_alert=True)
        # channel check
        settings = await get_settings(query.message.chat.id)
        # for private file send
        try:
            await bot.send_cached_media(
                chat_id=query.from_user.id,
                file_id=file_id,
                caption=files_.file_name
            )
            await query.answer("Check PM, I have sent files in PM", show_alert=False)
        except Exception as e:
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
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.B_NAME),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="start"),
                 InlineKeyboardButton("🔐 ᴄʟᴏsᴇ", callback_data="close_data")]
            ]),
            disable_web_page_preview=True
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
            text=script.HELP_TXT.format(temp.B_NAME),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 ʜᴏᴍᴇ", callback_data="start"),
                 InlineKeyboardButton("🔐 ᴄʟᴏsᴇ", callback_data="close_data")]
            ]),
            disable_web_page_preview=True
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
        buttons = [[
            InlineKeyboardButton('🔰 ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ 🔰', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ],[
            InlineKeyboardButton(' ʜᴇʟᴘ 📢', callback_data='help'),
            InlineKeyboardButton(' ᴀʙᴏᴜᴛ 📖', callback_data='about')
        ],[
            InlineKeyboardButton('ᴛᴏᴘ sᴇᴀʀᴄʜɪɴɢ ⭐', callback_data="topsearch"),
            InlineKeyboardButton('ᴜᴘɢʀᴀᴅᴇ 🎟', callback_data="premium_info"),
        ]]
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
    except MessageNotModified:
        pass

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
            except Exception:
                pass
    except Exception as e:
        logger.exception(e)
