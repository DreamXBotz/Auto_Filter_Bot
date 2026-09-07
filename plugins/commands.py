import os
import re
import base64
import logging
import random
import asyncio
import string
import sys
import pytz
from .pmfilter import auto_filter 
from Script import script
from datetime import datetime, timedelta
from database.refer import referdb
from database.config_db import mdb
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup
from pyrogram import Client, filters, enums, StopPropagation
from pyrogram.errors import FloodWait, UserNotParticipant , ChannelInvalid, PeerIdInvalid
from database.ia_filterdb import Media, Media2, get_file_details, unpack_new_file_id, get_bad_files, save_file
from database.users_chats_db import db
from info import (
    LOG_CHANNEL, IMDB_TEMPLATE, IS_VERIFY, TUTORIAL, TUTORIAL_2, TUTORIAL_3, EMOJI_MODE, REACTIONS,
    VERIFY_IMG, TWO_VERIFY_GAP, UPDATE_CHNL_LNK, PICS, PICS_URL, ADMINS, SUBSCRIPTION, OWNER_LNK , 
    OWNER_UPI_ID, QR_CODE, AUTH_CHANNELS, AUTH_REQ_CHANNELS, FSUB_PICS, THREE_VERIFY_GAP, CUSTOM_FILE_CAPTION,
    COVERX, PROTECT_CONTENT, DELETE_TIME, PREMIUM_STREAM_MODE, STREAM_MODE, SUPPORT_CHAT_ID, REQST_CHANNEL,
    LOG_CHANNEL, SHORTENER_API, SHORTENER_API2, SHORTENER_API3, SHORTENER_WEBSITE, SHORTENER_WEBSITE2, SHORTENER_WEBSITE3,
    
)
from utils import get_settings, save_group_settings, is_subscribed, is_req_subscribed, get_size, get_shortlink, is_check_admin, temp, get_readable_time, get_time, generate_settings_text, log_error, clean_filename, get_random_mix_id

logger = logging.getLogger(__name__)

TIMEZONE = "Asia/Kolkata"
BATCH_FILES = {}
REQUEST_INVITE_LINK_CACHE: dict[int, str] = {}


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    try:
        if EMOJI_MODE:
            try:
                asyncio.create_task(message.react(emoji=random.choice(REACTIONS), big=True))
            except Exception:
                asyncio.create_task(message.react(emoji="⚡️"))
                pass
        m = message
        if len(m.command) == 2 and m.command[1].startswith(('notcopy', 'sendall')):
            _, userid, verify_id, file_id = m.command[1].split("_", 3)
            user_id = int(userid)
            grp_id = temp.VERIFICATIONS.get(user_id, 0)
            settings = await get_settings(grp_id)         
            verify_id_info = await db.get_verify_id_info(user_id, verify_id)
            if not verify_id_info or verify_id_info["verified"]:
                return await message.reply(script.LINK_EXPIRED_TXT)  

            ist_timezone = pytz.timezone('Asia/Kolkata')
            if await db.user_verified(user_id):
                key = "third_time_verified"
            else:
                key = "second_time_verified" if await db.is_user_verified(user_id) else "last_verified"
            current_time = datetime.now(tz=ist_timezone)
            await db.update_notcopy_user(user_id, {key:current_time})
            await db.update_verify_id_info(user_id, verify_id, {"verified":True})
            if key == "third_time_verified": 
                num = 3 
            else: 
                num =  2 if key == "second_time_verified" else 1 
            if key == "third_time_verified": 
                msg = script.THIRDT_VERIFY_COMPLETE_TEXT
            else:
                msg = script.SECOND_VERIFY_COMPLETE_TEXT if key == "second_time_verified" else script.VERIFY_COMPLETE_TEXT
            if message.command[1].startswith('sendall'):
                verifiedfiles = f"https://telegram.me/{temp.U_NAME}?start=allfiles_{grp_id}_{file_id}"
            else:
                verifiedfiles = f"https://telegram.me/{temp.U_NAME}?start=file_{grp_id}_{file_id}"
            await client.send_message(settings['log'], script.VERIFIED_LOG_TEXT.format(m.from_user.mention, user_id, datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d %B %Y'), num))
            btn = [[
                InlineKeyboardButton("✅ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ɢᴇᴛ ꜰɪʟᴇ ✅", url=verifiedfiles),
            ]]
            reply_markup=InlineKeyboardMarkup(btn)
            dlt=await m.reply_photo(
                photo=(VERIFY_IMG),
                caption=msg.format(message.from_user.mention, get_readable_time(TWO_VERIFY_GAP)),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )

            await asyncio.sleep(300)
            await dlt.delete()
            return         
        if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            buttons = [[
                        InlineKeyboardButton('❤️ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ❤️', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
                    ],[
                        InlineKeyboardButton('🍁 Update Channel 🍁', url=UPDATE_CHNL_LNK)
                      ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply(script.GSTART_TXT.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup, disable_web_page_preview=True)

            await asyncio.sleep(2) 
            if not await db.get_chat(message.chat.id):
                total=await client.get_chat_members_count(message.chat.id)
                await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))       
                await db.add_chat(message.chat.id, message.chat.title)
            return 
        if not await db.is_user_exist(message.from_user.id):
            await db.add_user(message.from_user.id, message.from_user.first_name)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
        if len(message.command) != 2:
            buttons = [[
                        InlineKeyboardButton('🔰 ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ 🔰', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
                    ],[
                        InlineKeyboardButton(' ʜᴇʟᴘ 📢', callback_data='help'),
                        InlineKeyboardButton(' ᴀʙᴏᴜᴛ 📖', callback_data='about')
                    ],[
                        InlineKeyboardButton('ᴛᴏᴘ sᴇᴀʀᴄʜɪɴɢ ⭐', callback_data="topsearch"),
                        InlineKeyboardButton('ᴜᴘɢʀᴀᴅᴇ 🎟', callback_data="premium_info"),
                    ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            current_time = datetime.now(pytz.timezone(TIMEZONE))
            curr_time = current_time.hour        
            if curr_time < 12:
                gtxt = "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞" 
            elif curr_time < 17:
                gtxt = "ɢᴏᴏᴅ ᴀғᴛᴇʀɴᴏᴏɴ 🌓" 
            elif curr_time < 21:
                gtxt = "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"
            else:
                gtxt = "ɢᴏᴏᴅ ɴɪɢʜᴛ 🌑"
            if len(PICS) == 1:
                PIC = PICS[0]
            else:
                try:      
                    PIC = f"{random.choice(PICS_URL)}?r={get_random_mix_id()}"
                except Exception:
                    PIC = random.choice(PICS)
            await message.reply_photo(
                photo=PIC,
                caption=script.START_TXT.format(message.from_user.mention, gtxt, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return

        if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
            buttons = [[
                        InlineKeyboardButton('🔰 ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ 🔰', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
                    ],[
                        InlineKeyboardButton(' ʜᴇʟᴘ 📢', callback_data='help'),
                        InlineKeyboardButton(' ᴀʙᴏᴜᴛ 📖', callback_data='about')
                    ],[
                        InlineKeyboardButton('ᴛᴏᴘ sᴇᴀʀᴄʜɪɴɢ ⭐', callback_data="topsearch"),
                        InlineKeyboardButton('ᴜᴘɢʀᴀᴅᴇ 🎟', callback_data="premium_info"),
                    ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            current_time = datetime.now(pytz.timezone(TIMEZONE))
            curr_time = current_time.hour        
            if curr_time < 12:
                gtxt = "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞" 
            elif curr_time < 17:
                gtxt = "ɢᴏᴏᴅ ᴀғᴛᴇʀɴᴏᴏɴ 🌓" 
            elif curr_time < 21:
                gtxt = "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"
            else:
                gtxt = "ɢᴏᴏᴅ ɴɪɢʜᴛ 🌑"
            if len(PICS) == 1:
                PIC = PICS[0]
            else:
                try:
                    PIC = f"{random.choice(PICS_URL)}?r={get_random_mix_id()}"
                except Exception:
                    PIC = random.choice(PICS)
            await message.reply_photo(
                photo=PIC,
                caption=script.START_TXT.format(message.from_user.mention, gtxt, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return
        if message.command[1].startswith("reff_"):
            try:
                user_id = int(message.command[1].split("_")[1])
            except ValueError:
                await message.reply_text("<b>‼️ ɪɴᴠᴀʟɪᴅ ʀᴇꜰᴇʀ!</b>")
                return
            if user_id == message.from_user.id:
                await message.reply_text(script.REFER_SELF_ALRT)
                return
            if referdb.is_user_in_list(message.from_user.id):
                await message.reply_text(script.REFER_ALREADY_ALRT)
                return
            if await db.is_user_exist(message.from_user.id): 
                await message.reply_text(script.REFER_ALREADY_JOINED_ALRT)
                return 
            try:
                uss = await client.get_users(user_id)
            except Exception:
                return 	    
            referdb.add_user(message.from_user.id)
            fromuse = referdb.get_refer_points(user_id) + 10
            if fromuse == 100:
                referdb.add_refer_points(user_id, 0) 
                await message.reply_text(script.REFER_INVITED_ALRT.format(uss.mention))		    
                await client.send_message(chat_id=user_id, text=script.REFER_CONGRATS_ALRT.format(message.from_user.mention)) 	
                seconds = 2592000
                if seconds > 0:
                    expiry_time = datetime.now() + timedelta(seconds=seconds)
                    user_data = {"id": user_id, "expiry_time": expiry_time}  # Using "id" instead of "user_id"  
                    await db.update_user(user_data)  # Use the update_user method to update or insert user data		    
                    await client.send_message(
                        chat_id=user_id,
                        text=f"<b>Hᴇʏ {uss.mention}\n\nYᴏᴜ ɢᴏᴛ 1 ᴍᴏɴᴛʜ ᴘʀᴇᴍɪᴜᴍ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʙʏ ɪɴᴠɪᴛɪɴɢ 10 ᴜsᴇʀs ❗</b>",
                        disable_web_page_preview=True              
                    )
                for admin in ADMINS:
                    await client.send_message(chat_id=admin, text=f"Sᴜᴄᴄᴇss ғᴜʟʟʏ ᴛᴀsᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ʙʏ ᴛʜɪs ᴜsᴇʀ:\n\nuser Nᴀᴍᴇ: {uss.mention}\n\nUsᴇʀ ɪᴅ: {uss.id}!")	
            else:
                referdb.add_refer_points(user_id, fromuse)
                await message.reply_text(script.REFER_INVITED_ALRT.format(uss.mention))
                await client.send_message(user_id, script.REFER_CONGRATS_ALRT.format(message.from_user.mention))
            return

        if len(message.command) == 2 and message.command[1] in ["premium"]:
            buttons = [[
                        InlineKeyboardButton('📲 ꜱᴇɴᴅ ᴘᴀʏᴍᴇɴᴛ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ', url=OWNER_LNK)
                      ],[
                        InlineKeyboardButton('UPI ID Copy Karein ??', copy_text=OWNER_UPI_ID, style=enums.ButtonStyle.PRIMARY)
                      ],[
                        InlineKeyboardButton('❌ ᴄʟᴏꜱᴇ ❌', callback_data='close_data', style=enums.ButtonStyle.DANGER)
                      ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply_photo(
                photo=(SUBSCRIPTION),
                caption=script.PREPLANS_TXT.format(message.from_user.mention, OWNER_UPI_ID, QR_CODE),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return  

        if len(message.command) == 2 and message.command[1].startswith('getfile'):
            movies = message.command[1].split("-", 1)[1] 
            movie = movies.replace('-',' ')
            message.text = movie 
            await auto_filter(client, message)
            raise StopPropagation

        data = message.command[1]
        try:
            _, grp_id, file_id = data.split("_", 2)
            grp_id = int(grp_id)
        except Exception:
            grp_id = 0
            file_id = data

        decoded_file_id = file_id
        if not data.startswith("allfiles"):
            try:
                raw = base64.urlsafe_b64decode(file_id + "=" * (-len(file_id) % 4))
                sep = raw.find(b"_")
                if sep != -1:
                    decoded_file_id = raw[sep + 1:].decode("latin1")
            except Exception:
                pass

        file_details_task = asyncio.create_task(get_file_details(decoded_file_id))
        if not await db.has_premium_access(message.from_user.id): 
            try:
                btn = []
                chat = grp_id
                settings      = await get_settings(chat)
                fsub_channels = list(dict.fromkeys((settings.get('fsub', []) if settings else [])+ AUTH_CHANNELS)) 

                if fsub_channels:
                    btn += await is_subscribed(client, message.from_user.id, fsub_channels)
                if AUTH_REQ_CHANNELS:
                    btn += await is_req_subscribed(client, message.from_user.id, AUTH_REQ_CHANNELS)
                if btn:
                    if len(message.command) > 1 and "_" in message.command[1]:
                        kk, file_id = message.command[1].split("_", 1)
                        btn.append([
                            InlineKeyboardButton("♻️ ᴛʀʏ ᴀɢᴀɪɴ ♻️", callback_data=f"checksub#{kk}#{file_id}")
                        ])
                        reply_markup = InlineKeyboardMarkup(btn)
                    photo = random.choice(FSUB_PICS) if FSUB_PICS else "https://graph.org/file/7478ff3eac37f4329c3d8.jpg"
                    caption = script.FORCESUB_TXT.format(message.from_user.mention)
                    await message.reply_photo(
                        photo=photo,
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode=enums.ParseMode.HTML
                    )
                    return

            except Exception as e:
                await log_error(client, f"❗️ Force Sub Error:\n\n{repr(e)}")
                logger.error(f"❗️ Force Sub Error:\n\n{repr(e)}")

        user_id = m.from_user.id
        if not await db.has_premium_access(user_id):
            try:
                grp_id = int(grp_id)
                user_verified = await db.is_user_verified(user_id)
                settings = await get_settings(grp_id)
                is_second_shortener = await db.use_second_shortener(user_id, settings.get('verify_time', TWO_VERIFY_GAP)) 
                is_third_shortener = await db.use_third_shortener(user_id, settings.get('third_verify_time', THREE_VERIFY_GAP))
                if settings.get("is_verify", IS_VERIFY) and (not user_verified or is_second_shortener or is_third_shortener):
                    verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                    await db.create_verify_id(user_id, verify_id)
                    temp.VERIFICATIONS[user_id] = grp_id
                    if message.command[1].startswith('allfiles'):
                        verify = await get_shortlink(f"https://telegram.me/{temp.U_NAME}?start=sendall_{user_id}_{verify_id}_{file_id}", grp_id, is_second_shortener, is_third_shortener)
                    else:
                        verify = await get_shortlink(f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}_{file_id}", grp_id, is_second_shortener, is_third_shortener)
                    if is_third_shortener:
                        howtodownload = settings.get('tutorial_3', TUTORIAL_3)
                    else:
                        howtodownload = settings.get('tutorial_2', TUTORIAL_2) if is_second_shortener else settings.get('tutorial', TUTORIAL)
                    buttons = [[
                        InlineKeyboardButton(text="♻️ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴠᴇʀɪꜰʏ ♻️", url=verify)
                    ],[
                        InlineKeyboardButton(text="⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪꜰʏ ⁉️", url=howtodownload)
                    ]]
                    reply_markup=InlineKeyboardMarkup(buttons)
                    if await db.user_verified(user_id): 
                        msg = script.THIRDT_VERIFICATION_TEXT
                    else:            
                        msg = script.SECOND_VERIFICATION_TEXT if is_second_shortener else script.VERIFICATION_TEXT
                    n=await m.reply_text(
                        text=msg.format(message.from_user.mention),
                        protect_content = True,
                        reply_markup=reply_markup,
                        parse_mode=enums.ParseMode.HTML
                    )
                    await asyncio.sleep(300) 
                    await n.delete()
                    await m.delete()
                    return
            except Exception as e:
                logger.error("Error In Verification: %s", e)
                pass

        files_ = await file_details_task
        if data.startswith("allfiles"):
            try:
                files = temp.GETALL.get(file_id)
                if not files:
                    return await message.reply('<b><i>ɴᴏ ꜱᴜᴄʜ ꜰɪʟᴇ ᴇxɪꜱᴛꜱ !</b></i>')
                filesarr = []
                cover = None
                for file in files:
                    file_id = file.file_id
                    files_ = await get_file_details(file_id)
                    files1 = files_[0]
                    title = clean_filename(files1.file_name)
                    cover = files1.cover
                    size = get_size(files1.file_size)
                    f_caption = files1.caption
                    settings = await get_settings(int(grp_id))
                    DREAMX_CAPTION = settings.get('caption', CUSTOM_FILE_CAPTION)
                    if DREAMX_CAPTION:
                        try:
                            f_caption=DREAMX_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                        except Exception as e:
                            logger.exception(e)
                            f_caption = f_caption
                    if f_caption is None:
                        f_caption = f"{clean_filename(files1.file_name)}"
                    btn = await stream_buttons(message.from_user.id, file_id)
                    msg = await client.send_cached_media(
                        chat_id=message.from_user.id,
                        cover=cover,
                        file_id=file_id,
                        caption=f_caption,
                        protect_content=settings.get('file_secure', PROTECT_CONTENT),
                        reply_markup=InlineKeyboardMarkup(btn)
                    )
                    filesarr.append(msg)
                k = await client.send_message(chat_id=message.from_user.id, text=script.DEL_MSG.format(get_time(DELETE_TIME)), parse_mode=enums.ParseMode.HTML)

                await asyncio.sleep(DELETE_TIME)
                for x in filesarr:
                    await x.delete()
                await k.edit_text("<b>ʏᴏᴜʀ ᴀʟʟ ᴠɪᴅᴇᴏꜱ/ꜰɪʟᴇꜱ ᴀʀᴇ ᴅᴇʟᴇᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ !\nᴋɪɴᴅʟʏ ꜱᴇᴀʀᴄʜ ᴀɢᴀɪɴ</b>")
                return
            except Exception as e:
                logger.exception(e)
                return

        settings = await get_settings(int(grp_id))
        if not files_:
            raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
            sep = raw.find(b"_")
            if sep == -1:
                raise ValueError("Invalid encoded data")
            file_id = raw[sep + 1:].decode("latin1")
            try:
                cover = None
                if COVERX:
                    details = await get_file_details(file_id)
                    cover = details[0].cover if details and details[0].cover else None
                btn = await stream_buttons(message.from_user.id, file_id)
                msg = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    cover=cover,
                    file_id=file_id,
                    protect_content=settings.get('file_secure', PROTECT_CONTENT),
                    reply_markup=InlineKeyboardMarkup(btn))

                filetype = msg.media
                file = getattr(msg, filetype.value)
                title = clean_filename(file.file_name)
                size=get_size(file.file_size)
                f_caption = f"<code>{title}</code>"
                settings = await get_settings(int(grp_id))
                DREAMX_CAPTION = settings.get('caption', CUSTOM_FILE_CAPTION)
                if DREAMX_CAPTION:
                    try:
                        f_caption=DREAMX_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='')
                    except Exception:
                        return
                await msg.edit_caption(f_caption, reply_markup=InlineKeyboardMarkup(btn))
                k = await msg.reply(script.DEL_MSG.format(get_time(DELETE_TIME)), quote=True, parse_mode=enums.ParseMode.HTML)
                await asyncio.sleep(DELETE_TIME)
                await msg.delete()
                await k.edit_text("<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!</b>")
                return
            except Exception as e:
                logger.exception(e)
                pass
            return await message.reply('ɴᴏ ꜱᴜᴄʜ ꜰɪʟᴇ ᴇxɪꜱᴛꜱ !')

        files = files_[0]
        title = clean_filename(files.file_name)
        size = get_size(files.file_size)
        cover = files.cover if files.cover else None
        f_caption = files.caption
        settings = await get_settings(int(grp_id))            
        DREAMX_CAPTION = settings.get('caption', CUSTOM_FILE_CAPTION)
        if DREAMX_CAPTION:
            try:
                f_caption=DREAMX_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption

        if f_caption is None:
            f_caption = clean_filename(files.file_name)
        btn = await stream_buttons(message.from_user.id, file_id)
        msg = await client.send_cached_media(
            chat_id=message.from_user.id,
            file_id=file_id,
            cover=cover,
            caption=f_caption,
            protect_content=settings.get('file_secure', PROTECT_CONTENT),
            reply_markup=InlineKeyboardMarkup(btn)
        )
        
        k = await msg.reply(script.DEL_MSG.format(get_time(DELETE_TIME)), quote=True, parse_mode=enums.ParseMode.HTML)
        await asyncio.sleep(DELETE_TIME)
        await msg.delete()
        await k.edit_text("<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!</b>")
        return
    except StopPropagation:
        raise
    except Exception as e:
        logger.exception(f"Error In /start command - {e}")
        pass

async def stream_buttons(user_id: int, file_id: str):
    if STREAM_MODE and not PREMIUM_STREAM_MODE:
        return [
            [InlineKeyboardButton('🚀 ꜰᴀꜱᴛ ᴅᴏᴡɴʟᴏᴀᴅ / ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ 🖥️', callback_data=f'generate_stream_link:{file_id}')],
            [InlineKeyboardButton('ℹ️ ᴠɪᴇᴡ ᴀᴜᴅɪᴏ & ꜱᴜʙꜱ ɪɴꜰᴏ ℹ️', callback_data=f'extract_data:{file_id}')],
            [InlineKeyboardButton('📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ 📌', url=UPDATE_CHNL_LNK)]
        ]
    elif STREAM_MODE and PREMIUM_STREAM_MODE:
        if not await db.has_premium_access(user_id):
            return [
                [InlineKeyboardButton('🚀 ꜰᴀꜱᴛ ᴅᴏᴡɴʟᴏᴀᴅ / ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ 🖥️', callback_data='prestream')],
                [InlineKeyboardButton('ℹ️ ᴠɪᴇᴡ ᴀᴜᴅɪᴏ & ꜱᴜʙꜱ ɪɴꜰᴏ ℹ️', callback_data='prestream')],
                [InlineKeyboardButton('📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ 📌', url=UPDATE_CHNL_LNK)]
            ]
        else:
            return [
                [InlineKeyboardButton('🚀 ꜰᴀꜱᴛ ᴅᴏᴡɴʟᴏᴀᴅ / ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ 🖥️', callback_data=f'generate_stream_link:{file_id}')],
                [InlineKeyboardButton('ℹ️ ᴠɪᴇᴡ ᴀᴜᴅɪᴏ & ꜱᴜʙꜱ ɪɴꜰᴏ ℹ️', callback_data=f'extract_data:{file_id}')],
                [InlineKeyboardButton('📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ 📌', url=UPDATE_CHNL_LNK)]
            ]
    else:
        return [[InlineKeyboardButton('📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ 📌', url=UPDATE_CHNL_LNK)]]
    
@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('DreamXlogs.txt', caption="📑 **ʟᴏɢꜱ**")
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('save') & filters.user(ADMINS))
async def save_file_handler(bot, message):
    """Save file to database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Pʀᴏᴄᴇssɪɴɢ...⏳", quote=True)
    else:
        await message.reply('Rᴇᴘʟʏ ᴛᴏ ғɪʟᴇ ᴡɪᴛʜ /save ᴡʜɪᴄʜ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴀᴠᴇ', quote=True)
        return

    try:
        for file_type in ("document", "video", "audio"):
            media = getattr(reply, file_type, None)
            if media is not None:
                break
        else:
            await msg.edit('Tʜɪs ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ғɪʟᴇ ғᴏʀᴍᴀᴛ')
            return
        
        file_id, file_ref = unpack_new_file_id(media.file_id)
        media.file_type = file_type
        media.caption = reply.caption
        success, status = await save_file(media)
        if success:
            await msg.edit('Fɪʟᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ sᴀᴠᴇᴅ ᴛᴏ ᴅᴀᴛᴀʙᴀsᴇ ✅')
        elif status == 0:
            await msg.edit('Fɪʟᴇ ᴀʟʀᴇᴀᴅʏ ᴇxɪsᴛs ɪɴ ᴅᴀᴛᴀʙᴀsᴇ ⚠️')
        elif status == 2:
            await msg.edit('Eʀʀᴏʀ: Fɪʟᴇ ᴠᴀʟɪᴅᴀᴛɪᴏɴ ғᴀɪʟᴇᴅ ❌')
        else:
            await msg.edit('Eʀʀᴏʀ: Fᴀɪʟᴇᴅ ᴛᴏ sᴀᴠᴇ ғɪʟᴇ ❌')
    except Exception as e:
        logger.exception(e)
        await msg.edit(f'Aɴ ᴜɴᴇxᴘᴇᴄᴛᴇᴅ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e} ❌')


@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Pʀᴏᴄᴇssɪɴɢ...⏳", quote=True)
    else:
        await message.reply('Rᴇᴘʟʏ ᴛᴏ ғɪʟᴇ ᴡɪᴛʜ /delete ᴡʜɪᴄʜ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴇʟᴇᴛᴇ', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('Tʜɪs ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ғɪʟᴇ ғᴏʀᴍᴀᴛ')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)
    if await Media.count_documents({'file_id': file_id}):
        result = await Media.collection.delete_one({
            '_id': file_id,
        })
    else:
        result = await Media2.collection.delete_one({
            '_id': file_id,
        })
    if result.deleted_count:
        await msg.edit('Fɪʟᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ ✅')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if result.deleted_count:
            await msg.edit('Fɪʟᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ ✅')
        else:
            result = await Media2.collection.delete_many({
                'file_name': file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await msg.edit('Fɪʟᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ')
            else:
                result = await Media.collection.delete_many({
                    'file_name': media.file_name,
                    'file_size': media.file_size,
                    'mime_type': media.mime_type
                })
                if result.deleted_count:
                    await msg.edit('Fɪʟᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ ✅')
                else:
                    result = await Media2.collection.delete_many({
                        'file_name': media.file_name,
                        'file_size': media.file_size,
                        'mime_type': media.mime_type
                    })
                    if result.deleted_count:
                        await msg.edit('Fɪʟᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ ✅')
                    else:
                        await msg.edit('Fɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ ❌')


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'ᴛʜɪꜱ ᴡɪʟʟ ᴅᴇʟᴇᴛᴇ ᴀʟʟ ʏᴏᴜʀ ɪɴᴅᴇxᴇᴅ ꜰɪʟᴇꜱ !\nᴅᴏ ʏᴏᴜ ꜱᴛɪʟʟ ᴡᴀɴᴛ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ?',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="⚠️ ʏᴇꜱ ⚠️", callback_data="autofilter_delete", style=enums.ButtonStyle.DANGER
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ ɴᴏ ❌", callback_data="close_data"
                    )
                ],
            ]
        ),
        quote=True,
    )

@Client.on_message(filters.command('settings'))
async def settings(client, message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply("ʏᴏᴜ'ʀᴇ ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ.")
    chat_type = message.chat.type
    if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        if not await is_check_admin(client, grp_id, message.from_user.id):
            return await message.reply_text(script.NT_ADMIN_ALRT_TXT)
        await db.connect_group(grp_id, user_id)
        btn = [[
                InlineKeyboardButton("👤 ᴏᴘᴇɴ ɪɴ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ 👤", callback_data=f"opnsetpm#{grp_id}")
              ],[
                InlineKeyboardButton("👥 ᴏᴘᴇɴ ʜᴇʀᴇ 👥", callback_data=f"opnsetgrp#{grp_id}")
              ]]
        await message.reply_text(
                text="<b>ᴡʜᴇʀᴇ ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴏᴘᴇɴ ꜱᴇᴛᴛɪɴɢꜱ ᴍᴇɴᴜ ? ⚙️</b>",
                reply_markup=InlineKeyboardMarkup(btn),
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=message.id
        )
    elif chat_type == enums.ChatType.PRIVATE:
        connected_groups = await db.get_connected_grps(user_id)
        if not connected_groups:
            return await message.reply_text("Nᴏ Cᴏɴɴᴇᴄᴛᴇᴅ Gʀᴏᴜᴘs Fᴏᴜɴᴅ .")
        group_list = []
        for group in connected_groups:
            try:
                Chat = await client.get_chat(group)
                group_list.append([ InlineKeyboardButton(text=Chat.title, callback_data=f"grp_pm#{Chat.id}") ])
            except Exception:
                pass
        await message.reply_text(
                    "⚠️ ꜱᴇʟᴇᴄᴛ ᴛʜᴇ ɢʀᴏᴜᴘ ᴡʜᴏꜱᴇ ꜱᴇᴛᴛɪɴɢꜱ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ.\n\n"
                    "ɪꜰ ʏᴏᴜʀ ɢʀᴏᴜᴘ ɪꜱ ɴᴏᴛ ꜱʜᴏᴡɪɴɢ ʜᴇʀᴇ,\n"
                    "ᴜꜱᴇ /reload ɪɴ ᴛʜᴀᴛ ɢʀᴏᴜᴘ ᴀɴᴅ ɪᴛ ᴡɪʟʟ ᴀᴘᴘᴇᴀʀ ʜᴇʀᴇ.",
                    reply_markup=InlineKeyboardMarkup(group_list)
                )

@Client.on_message(filters.command('reload'))
async def connect_group(client, message):
    user_id = message.from_user.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        await db.connect_group(message.chat.id, user_id)
        await message.reply_text("Gʀᴏᴜᴘ Rᴇʟᴏᴀᴅᴇᴅ ✅ Nᴏᴡ Yᴏᴜ Cᴀɴ Mᴀɴᴀɢᴇ Tʜɪs Gʀᴏᴜᴘ Fʀᴏᴍ PM.")
    elif message.chat.type == enums.ChatType.PRIVATE:
        if len(message.command) < 2:
            await message.reply_text("Example: /reload 123456789")
            return
        try:
            group_id = int(message.command[1])
            if not await is_check_admin(client, group_id, user_id):
                await message.reply_text(script.NT_ADMIN_ALRT_TXT)
                return
            chat = await client.get_chat(group_id)
            await db.connect_group(group_id, user_id)
            await message.reply_text(f"Lɪɴᴋᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ✅ {chat.title} ᴛᴏ PM.")
        except Exception:
            await message.reply_text("Invalid group ID or error occurred.")

@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    sts = await message.reply("ᴄʜᴇᴄᴋɪɴɢ ᴛᴇᴍᴘʟᴀᴛᴇ...")
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return await message.reply("ʏᴏᴜ'ʀᴇ ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ.")

    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await sts.edit("⚠️ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴀ ɢʀᴏᴜᴘ ᴄʜᴀᴛ.")

    group_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, group_id, user_id):
        await message.reply_text(script.NT_ADMIN_ALRT_TXT)
        return
    if len(message.command) < 2:
        return await sts.edit("⚠️ ɴᴏ ᴛᴇᴍᴘʟᴀᴛᴇ ᴘʀᴏᴠɪᴅᴇᴅ!")

    template = message.text.split(" ", 1)[1]
    await save_group_settings(group_id, 'template', template)
    await sts.edit(
        f"✅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴇᴍᴘʟᴀᴛᴇ ꜰᴏʀ <code>{title}</code> ᴛᴏ:\n\n{template}"
    )


# Must add REQST_CHANNEL and SUPPORT_CHAT_ID to use this feature
@Client.on_message((filters.command("request") | filters.regex(r"(?i)#request")) & filters.group)
async def requests(bot, message):
    if message.chat.id != SUPPORT_CHAT_ID:
        return
    if not message.from_user:
        return await message.reply_text("<b>⚠️ ᴜɴᴀʙʟᴇ ᴛᴏ ɪᴅᴇɴᴛɪꜰʏ ʏᴏᴜ.</b>")
    
    reporter = str(message.from_user.id)
    mention = message.from_user.mention

    if message.reply_to_message:
        target_msg = message.reply_to_message
        content = target_msg.text or target_msg.caption or ""
        msg_link = target_msg.link
    else:
        content = message.text or message.caption or ""
        content = re.sub(r"(?i)[#/]?request", "", content).strip()
        msg_link = message.link

    content = content.strip()
    if len(content) < 3:
        return await message.reply_text("<b>ʏᴏᴜ ᴍᴜꜱᴛ ᴛʏᴘᴇ ᴀʙᴏᴜᴛ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ [ᴍɪɴɪᴍᴜᴍ 3 ᴄʜᴀʀᴀᴄᴛᴇʀꜱ]. ʀᴇǫᴜᴇꜱᴛꜱ ᴄᴀɴ'ᴛ ʙᴇ ᴇᴍᴘᴛʏ.</b>")
    
    reported_post: Message | None = None
    try:
        btn = [[
            InlineKeyboardButton('ᴠɪᴇᴡ ʀᴇǫᴜᴇꜱᴛ', url=msg_link),
            InlineKeyboardButton('ꜱʜᴏᴡ ᴏᴘᴛɪᴏɴꜱ', callback_data=f'show_option#{reporter}')
        ]]
        req_text = f"<b>📝 ʀᴇǫᴜᴇꜱᴛ : <u>{content}</u>\n\n📚 ʀᴇᴘᴏʀᴛᴇᴅ ʙʏ : {mention}\n📖 ʀᴇᴘᴏʀᴛᴇʀ ɪᴅ : {reporter}\n\n</b>"
        warning_text = "<b>⚠️ ʀᴇǫᴜᴇꜱᴛ ᴄʜᴀɴɴᴇʟ ɪꜱ ɴᴏᴛ ꜱᴇᴛ.</b>"
        if REQST_CHANNEL is not None:
            try:
                reported_post = await bot.send_message(chat_id=REQST_CHANNEL, text=req_text, reply_markup=InlineKeyboardMarkup(btn))
            except Exception:
                for admin in ADMINS:
                    await bot.send_message(chat_id=admin, text=warning_text)
                    reported_post = await bot.send_message(chat_id=admin, text=req_text, reply_markup=InlineKeyboardMarkup(btn))
        else:
            for admin in ADMINS:
                await bot.send_message(chat_id=admin, text=warning_text)
                reported_post = await bot.send_message(chat_id=admin, text=req_text, reply_markup=InlineKeyboardMarkup(btn))
    except Exception:
        logger.exception("Request failed")
        return await message.reply_text( "<b>⚠️ ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ. ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.</b>")

    if reported_post and REQST_CHANNEL is not None:
        try:
            invite_link = REQUEST_INVITE_LINK_CACHE.get(REQST_CHANNEL)
            if not invite_link:
                try:
                    link = await bot.create_chat_invite_link(int(REQST_CHANNEL))
                    invite_link = link.invite_link
                    REQUEST_INVITE_LINK_CACHE[REQST_CHANNEL] = invite_link
                except Exception:
                    logger.exception("Failed to create invite link")
                    invite_link = None
            if invite_link:
                btn = [[
                    InlineKeyboardButton('ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ', url=invite_link),
                    InlineKeyboardButton('ᴠɪᴇᴡ ʀᴇǫᴜᴇꜱᴛ', url=reported_post.link)
                ]]
                await message.reply_text("<b>ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ʜᴀꜱ ʙᴇᴇɴ ᴀᴅᴅᴇᴅ! ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ꜰᴏʀ ꜱᴏᴍᴇ ᴛɪᴍᴇ.\n\nᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ ꜰɪʀꜱᴛ & ᴠɪᴇᴡ ʀᴇǫᴜᴇꜱᴛ.</b>", reply_markup=InlineKeyboardMarkup(btn))
            else:
                await message.reply_text("<b>ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛ ʜᴀꜱ ʙᴇᴇɴ ᴀᴅᴅᴇᴅ! ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ꜰᴏʀ ꜱᴏᴍᴇ ᴛɪᴍᴇ.</b>")
        except Exception:
            logger.exception("Failed to send request confirmation")
            await message.reply_text("<b>⚠️ ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ. ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.</b>")

@Client.on_message(filters.command("send") & filters.user(ADMINS))
async def send_msg(bot, message):
    if message.reply_to_message:
        target_id = message.text.split(" ", 1)[1]
        out = "Users Saved In DB Are:\n\n"
        success = False
        try:
            user = await bot.get_users(target_id)
            users = await db.get_all_users()
            async for usr in users:
                out += f"{usr['id']}"
                out += '\n'
            if str(user.id) in str(out):
                await message.reply_to_message.copy(int(user.id))
                success = True
            else:
                success = False
            if success:
                await message.reply_text(f"<b>ʏᴏᴜʀ ᴍᴇꜱꜱᴀɢᴇ ʜᴀꜱ ʙᴇᴇɴ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇɴᴛ ᴛᴏ {user.mention}.</b>")
            else:
                await message.reply_text("<b>ᴛʜɪꜱ ᴜꜱᴇʀ ᴅɪᴅɴ'ᴛ ꜱᴛᴀʀᴛᴇᴅ ᴛʜɪꜱ ʙᴏᴛ ʏᴇᴛ !</b>")
        except Exception as e:
            await message.reply_text(f"<b>Error: {e}</b>")
    else:
        await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴀꜱ ᴀ ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴍᴇꜱꜱᴀɢᴇ ᴜꜱɪɴɢ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴄʜᴀᴛ ɪᴅ. ꜰᴏʀ ᴇɢ:  /send ᴜꜱᴇʀɪᴅ</b>")

@Client.on_message(filters.command("deletefiles") & filters.user(ADMINS))
async def deletemultiplefiles(bot, message):
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, This command won't work in groups. It only works on my PM !</b>")

    try:
        keyword = message.text.split(" ", 1)[1]
    except Exception:
        return await message.reply_text(f"<b>Hey {message.from_user.mention}, Give me a keyword along with the command to delete files.</b>")
    k = await bot.send_message(chat_id=message.chat.id, text=f"<b>Fetching Files for your query {keyword} on DB... Please wait...</b>")
    files, total = await get_bad_files(keyword)
    total = len(files)
    if total == 0:
        await k.edit_text(f"<b>No files found for your query {keyword} !</b>")
        await asyncio.sleep(DELETE_TIME)
        await k.delete()
        return
    await k.delete()
    btn = [[
       InlineKeyboardButton("⚠️ Yes, Continue ! ⚠️", callback_data=f"killfilesdq#{keyword}")
       ],[
       InlineKeyboardButton("❌ No, Abort operation ! ❌", callback_data="close_data", style=enums.ButtonStyle.DANGER)
    ]]
    await message.reply_text(
        text=f"<b>Found {total} files for your query {keyword} !\n\nDo you want to delete?</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_callback_query(filters.regex("topsearch"))
async def topsearch_callback(client, callback_query):
    def is_alphanumeric(string):
        return bool(re.match('^[a-zA-Z0-9 ]*$', string))

    limit = 20
    top_messages = await mdb.get_top_messages(limit)
    seen_messages = set()
    truncated_messages = []
    for msg in top_messages:
        msg_lower = msg.lower()
        if msg_lower not in seen_messages and is_alphanumeric(msg):
            seen_messages.add(msg_lower)
            if len(msg) > 35:
                truncated_messages.append(msg[:32] + "...")
            else:
                truncated_messages.append(msg)
    keyboard = [truncated_messages[i:i+2] for i in range(0, len(truncated_messages), 2)]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        one_time_keyboard=True,
        resize_keyboard=True,
        placeholder="Most searches of the day"
    )
    await callback_query.message.reply_text(
        "<b>Tᴏᴘ Sᴇᴀʀᴄʜᴇs Oғ Tʜᴇ Dᴀʏ 👇</b>",
        reply_markup=reply_markup
    )
    await callback_query.answer()

@Client.on_message(filters.command('top_search'))
async def top(_, message):
    def is_alphanumeric(string):
        return bool(re.match('^[a-zA-Z0-9 ]*$', string))
    try:
        limit = int(message.command[1])
    except (IndexError, ValueError):
        limit = 20
    top_messages = await mdb.get_top_messages(limit)
    seen_messages = set()
    truncated_messages = []
    for msg in top_messages:
        msg_lower = msg.lower()
        if msg_lower not in seen_messages and is_alphanumeric(msg):
            seen_messages.add(msg_lower)
            if len(msg) > 35:
                truncated_messages.append(msg[:32] + "...")
            else:
                truncated_messages.append(msg)
    keyboard = [truncated_messages[i:i+2] for i in range(0, len(truncated_messages), 2)]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        one_time_keyboard=True,
        resize_keyboard=True,
        placeholder="Most searches of the day"
    )
    await message.reply_text(
        "<b>Tᴏᴘ Sᴇᴀʀᴄʜᴇs Oғ Tʜᴇ Dᴀʏ 👇</b>",
        reply_markup=reply_markup
    )

@Client.on_message(filters.command('trendlist'))
async def trendlist(client, message):
    def is_alphanumeric(string):
        return bool(re.match('^[a-zA-Z0-9 ]*$', string))
    limit = 31
    if len(message.command) > 1:
        try:
            limit = int(message.command[1])
        except ValueError:
            await message.reply_text(
                "Invalid number format.\nPlease provide a valid number after the /trendlist command."
            )
            return
    try:
        top_messages = await mdb.get_top_messages(limit)
    except Exception as e:
        await message.reply_text(f"Error retrieving messages: {str(e)}")
        return

    if not top_messages:
        await message.reply_text("No top messages found.")
        return
    seen_messages = set()
    truncated_messages = []

    for msg in top_messages:
        msg_lower = msg.lower()
        if msg_lower not in seen_messages and is_alphanumeric(msg):
            seen_messages.add(msg_lower)
            truncated_messages.append(msg[:32] + '...' if len(msg) > 35 else msg)

    if not truncated_messages:
        await message.reply_text("No valid top messages found.")
        return
    formatted_list = "\n".join([f"{i+1}. <b>{msg}</b>" for i, msg in enumerate(truncated_messages)])
    additional_message = (
        "⚡️ 𝑨𝒍𝒍 𝒕𝒉𝒆 𝒓𝒆𝒔𝒖𝒍𝒕𝒔 𝒂𝒃𝒐𝒗𝒆 𝒄𝒐𝒎𝒆 𝒇𝒓𝒐𝒎 𝒘𝒉𝒂𝒕 𝒖𝒔𝒆𝒓𝒔 𝒉𝒂𝒗𝒆 𝒔𝒆𝒂𝒓𝒄𝒉𝒆𝒅 𝒇𝒐𝒓. "
        "𝑻𝒉𝒆𝒚'𝒓𝒆 𝒔𝒉𝒐𝒘𝒏 𝒕𝒐 𝒚𝒐𝒖 𝒆𝒙𝒂𝒄𝒕𝒍𝒚 𝒂𝒔 𝒕𝒉𝒆𝒚 𝒘𝒆𝒓𝒆 𝒔𝒆𝒂𝒓𝒄𝒉𝒆𝒅, "
        "𝒘𝒊𝒕𝒉𝒐𝒖𝒕 𝒂𝒏𝒚 𝒄𝒉𝒂𝒏𝒈𝒆𝒔 𝒃𝒚 𝒕𝒉𝒆 𝒐𝒘𝒏𝒆𝒓."
    )
    formatted_list += f"\n\n{additional_message}"
    reply_text = f"<b>Top {len(truncated_messages)} Tʀᴀɴᴅɪɴɢ ᴏғ ᴛʜᴇ ᴅᴀʏ 👇:</b>\n\n{formatted_list}"
    await message.reply_text(reply_text)

@Client.on_message(filters.private & filters.command("pm_search") & filters.user(ADMINS))
async def set_pm_search(client, message):
    bot_id = client.me.id
    try:
        option = message.text.split(" ", 1)[1].strip().lower()
        enable_status = option in ['on', 'true']
    except (IndexError, ValueError):
        await message.reply_text("<b>💔 Invalid option. Please send 'on' or 'off' after the command..</b>")
        return
    try:
        await db.update_pm_search_status(bot_id, enable_status)
        response_text = (
            "<b> ᴘᴍ ꜱᴇᴀʀᴄʜ ᴇɴᴀʙʟᴇᴅ ✅</b>" if enable_status
            else "<b> ᴘᴍ ꜱᴇᴀʀᴄʜ ᴅɪꜱᴀʙʟᴇᴅ ❌</b>"
        )
        await message.reply_text(response_text)
    except Exception as e:
        logger.error(f"Error in set_pm_search: {e}")
        await message.reply_text(f"<b>❗ An error occurred: {e}</b>")

@Client.on_message(filters.private & filters.command("movie_update") & filters.user(ADMINS))
async def set_movie_update_notification(client, message):
    bot_id = client.me.id
    try:
        option = message.text.split(" ", 1)[1].strip().lower()
        enable_status = option in ['on', 'true']
    except (IndexError, ValueError):
        await message.reply_text("<b>💔 Invalid option. Please send 'on' or 'off' after the command.</b>")
        return
    try:
        await db.update_movie_update_status(bot_id, enable_status)
        response_text = (
            "<b>ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴ ᴇɴᴀʙʟᴇᴅ ✅</b>" if enable_status
            else "<b>ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴ ᴅɪꜱᴀʙʟᴇᴅ ❌</b>"
        )
        await message.reply_text(response_text)
    except Exception as e:
        logger.error(f"Error in set_movie_update_notification: {e}")
        await message.reply_text(f"<b>❗ An error occurred: {e}</b>")

@Client.on_message(filters.command("restart") & filters.user(ADMINS))
async def stop_button(bot, message):
    msg = await bot.send_message(text="<b><i>ʙᴏᴛ ɪꜱ ʀᴇꜱᴛᴀʀᴛɪɴɢ</i></b>", chat_id=message.chat.id)
    await asyncio.sleep(3)
    await msg.edit("<b><i><u>ʙᴏᴛ ɪꜱ ʀᴇꜱᴛᴀʀᴛᴇᴅ</u> ✅</i></b>")
    os.execl(sys.executable, sys.executable, *sys.argv)

@Client.on_message(filters.command("del_msg") & filters.user(ADMINS))
async def del_msg(client, message):
    confirm_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("Yes", callback_data="confirm_del_yes"),
        InlineKeyboardButton("No", callback_data="confirm_del_no")
    ]])
    sent_message = await message.reply_text(
        "⚠️ Aʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʟᴇᴀʀ ᴛʜᴇ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ʟɪsᴛ ?\n\n ᴅᴏ ʏᴏᴜ ꜱᴛɪʟʟ ᴡᴀɴᴛ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ?",
        reply_markup=confirm_markup
    )
    await asyncio.sleep(60)
    try:
        await sent_message.delete()
    except Exception as e:
        logger.error("Error deleting the message: %s", e)

@Client.on_callback_query(filters.regex('^confirm_del_'))
async def confirmation_handler(client, callback_query):
    action = callback_query.data.split("_")[-1]
    if action == "yes":
        await db.delete_all_msg()
        await callback_query.message.edit_text('🧹 ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ ʟɪsᴛ ʜᴀs ʙᴇᴇɴ ᴄʟᴇᴀʀᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ✅')
    elif action == "no":
        await callback_query.message.delete()
    await callback_query.answer()

@Client.on_message(filters.command('set_caption'))
async def save_caption(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text(script.NT_ADMIN_ALRT_TXT)
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    try:
        caption = message.text.split(" ", 1)[1]
    except Exception:
        return await message.reply_text("<code>ɢɪᴠᴇ ᴍᴇ ᴀ ᴄᴀᴘᴛɪᴏɴ ᴀʟᴏɴɢ ᴡɪᴛʜ ɪᴛ.\n\nᴇxᴀᴍᴘʟᴇ -\n\nꜰᴏʀ ꜰɪʟᴇ ɴᴀᴍᴇ ꜱᴇɴᴅ <code>{file_name}</code>\nꜰᴏʀ ꜰɪʟᴇ ꜱɪᴢᴇ ꜱᴇɴᴅ <code>{file_size}</code>\n\n<code>/set_caption {file_name}</code></code>")
    await save_group_settings(grp_id, 'caption', caption)
    await message.reply_text(f"ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴄʜᴀɴɢᴇᴅ ᴄᴀᴘᴛɪᴏɴ ꜰᴏʀ {title}\n\nᴄᴀᴘᴛɪᴏɴ - {caption}", disable_web_page_preview=True)
    await client.send_message(LOG_CHANNEL, f"#Set_Caption\n\nɢʀᴏᴜᴘ ɴᴀᴍᴇ : {title}\n\nɢʀᴏᴜᴘ ɪᴅ: {grp_id}\nɪɴᴠɪᴛᴇ ʟɪɴᴋ : {invite_link}\n\nᴜᴘᴅᴀᴛᴇᴅ ʙʏ : {message.from_user.username}")


@Client.on_message(filters.command(["set_tutorial", "set_tutorial_2", "set_tutorial_3"]))
async def set_tutorial(client, message: Message):
    grp_id = message.chat.id
    title = message.chat.title
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text(
            f"<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...\n\nGroup Name: {title}\nGroup ID: {grp_id}</b>"
        )
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text(script.NT_ADMIN_ALRT_TXT)

    try:
        tutorial_link = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply_text(
            f"<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ !!\n\nᴜꜱᴇ ʟɪᴋᴇ ᴛʜɪꜱ -</b>\n\n"
            f"<code>/{message.command[0]} https://t.me/dreamxbotz</code>"
        )
    if message.command[0] == "set_tutorial":
        tutorial_key = "tutorial"
    else:
        tutorial_key = f"tutorial_{message.command[0].split('_', 2)[2]}"

    await save_group_settings(grp_id, tutorial_key, tutorial_link)
    invite_link = await client.export_chat_invite_link(grp_id)
    await message.reply_text(
        f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴄʜᴀɴɢᴇᴅ {tutorial_key.replace('_', ' ').title()} ꜰᴏʀ {title}</b>\n\n"
        f"ʟɪɴᴋ - {tutorial_link}",
        disable_web_page_preview=True
    )
    await client.send_message(
        LOG_CHANNEL,
        f"#Set_{tutorial_key.title()}_Video\n\n"
        f"ɢʀᴏᴜᴘ ɴᴀᴍᴇ : {title}\n"
        f"ɢʀᴏᴜᴘ ɪᴅ : {grp_id}\n"
        f"ɪɴᴠɪᴛᴇ ʟɪɴᴋ : {invite_link}\n"
        f"ᴜᴘᴅᴀᴛᴇᴅ ʙʏ : {message.from_user.mention()}"
    )


async def handle_shortner_command(c, m, shortner_key, api_key, log_prefix, fallback_url, fallback_api):
    grp_id = m.chat.id
    if not await is_check_admin(c, grp_id, m.from_user.id):
        return await m.reply_text(script.NT_ADMIN_ALRT_TXT)
    if len(m.command) != 3:
        return await m.reply(
            f"<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʟɪᴋᴇ -\n\n`/{m.command[0]} your-shortener-domain.com your_api_key_here`</b>"
        )
    sts = await m.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    if m.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    custom_flag = 'custom_shortner' if shortner_key == 'shortner' else f'custom_{shortner_key}'
    try:
        URL = m.command[1]
        API = m.command[2]
        await save_group_settings(grp_id, shortner_key, URL)
        await save_group_settings(grp_id, api_key, API)
        await save_group_settings(grp_id, custom_flag, True)
        await m.reply_text(f"<b><u>✅ sʜᴏʀᴛɴᴇʀ ᴀᴅᴅᴇᴅ</u>\n\nꜱɪᴛᴇ - `{URL}`\nᴀᴘɪ - `{API}`</b>")
        user_id = m.from_user.id
        user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = (
            f"#{log_prefix}\n\nɴᴀᴍᴇ - {user_info}\n\nɪᴅ - `{user_id}`"
            f"\n\nꜱɪᴛᴇ - {URL}\n\nᴀᴘɪ - `{API}`"
            f"\n\nɢʀᴏᴜᴘ - {grp_link}\nɢʀᴏᴜᴘ ɪᴅ - `{grp_id}`"
        )
        await c.send_message(LOG_CHANNEL, log_message, disable_web_page_preview=True)
    except Exception as e:
        await save_group_settings(grp_id, shortner_key, fallback_url)
        await save_group_settings(grp_id, api_key, fallback_api)
        await save_group_settings(grp_id, custom_flag, False)
        await m.reply_text(
            f"<b><u>💢 ᴇʀʀᴏʀ ᴏᴄᴄᴜʀᴇᴅ!</u>\n\n"
            f"ᴅᴇꜰᴀᴜʟᴛ ꜱʜᴏʀᴛɴᴇʀ ᴀᴘᴘʟɪᴇᴅ\n"
            f"ɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ ᴛʀʏ ᴀ ᴠᴀʟɪᴅ ꜱɪᴛᴇ ᴀɴᴅ ᴀᴘɪ ᴋᴇʏ.\n\n"
            f"ʟɪᴋᴇ:\n\n`/{m.command[0]} your-shortener-domain.com your_api_key_here`\n\n"
            f"💔 ᴇʀʀᴏʀ - <code>{e}</code></b>"
        )

@Client.on_message(filters.command('set_shortner'))
async def set_shortner(c, m):
    await handle_shortner_command(c, m, 'shortner', 'api', 'New_Shortner_Set_For_1st_Verify', SHORTENER_WEBSITE, SHORTENER_API)

@Client.on_message(filters.command('set_shortner_2'))
async def set_shortner_2(c, m):
    await handle_shortner_command(c, m, 'shortner_two', 'api_two', 'New_Shortner_Set_For_2nd_Verify', SHORTENER_WEBSITE2, SHORTENER_API2)

@Client.on_message(filters.command('set_shortner_3'))
async def set_shortner_3(c, m):
    await handle_shortner_command(c, m, 'shortner_three', 'api_three', 'New_Shortner_Set_For_3rd_Verify', SHORTENER_WEBSITE3, SHORTENER_API3)

@Client.on_message(filters.command('set_log_channel'))
async def set_log(client, message):
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text(script.NT_ADMIN_ALRT_TXT)
    if len(message.text.split()) == 1:
        await message.reply("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʟɪᴋᴇ ᴛʜɪꜱ - \n\n`/set_log_channel -100******`</b>")
        return
    sts = await message.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    try:
        log = int(message.text.split(" ", 1)[1])
    except IndexError:
        return await message.reply_text("<b><u>ɪɴᴠᴀɪʟᴅ ꜰᴏʀᴍᴀᴛ!!</u>\n\nᴜsᴇ ʟɪᴋᴇ ᴛʜɪs - `/set_log_channel -100xxxxxxxx`</b>")
    except ValueError:
        return await message.reply_text('<b>ᴍᴀᴋᴇ sᴜʀᴇ ɪᴅ ɪs ɪɴᴛᴇɢᴇʀ...</b>')
    try:
        t = await client.send_message(chat_id=log, text="<b>ʜᴇʏ ᴡʜᴀᴛ's ᴜᴘ!!</b>")
        await asyncio.sleep(3)
        await t.delete()
    except Exception as e:
        return await message.reply_text(f'<b><u>😐 ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜɪs ʙᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ...</u>\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>')
    await save_group_settings(grp_id, 'log', log)
    await message.reply_text(f"<b>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴇᴛ ʏᴏᴜʀ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ꜰᴏʀ {title}\n\nɪᴅ - `{log}`</b>", disable_web_page_preview=True)
    user_id = message.from_user.id
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"{message.from_user.mention}"
    link = (await client.get_chat(message.chat.id)).invite_link
    grp_link = f"[{message.chat.title}]({link})"
    log_message = f"#New_Log_Channel_Set\n\nɴᴀᴍᴇ - {user_info}\n\nɪᴅ - `{user_id}`\n\nʟᴏɢ ᴄʜᴀɴɴᴇʟ ɪᴅ - `{log}`\nɢʀᴏᴜᴘ ʟɪɴᴋ - `{grp_link}`\n\nɢʀᴏᴜᴘ ɪᴅ : `{grp_id}`"
    await client.send_message(LOG_CHANNEL, log_message, disable_web_page_preview=True) 


@Client.on_message(filters.command('set_time'))
async def set_time(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")       
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text(script.NT_ADMIN_ALRT_TXT)
    try:
        time = int(message.text.split(" ", 1)[1])
    except Exception:
        return await message.reply_text("<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ\n\nᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʟɪᴋᴇ ᴛʜɪꜱ - <code>/set_time 600</code> [ ᴛɪᴍᴇ ᴍᴜꜱᴛ ʙᴇ ɪɴ ꜱᴇᴄᴏɴᴅꜱ ]</b>")   
    await save_group_settings(grp_id, 'verify_time', time)
    await message.reply_text(f"<b>✅️ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇᴛ 2ɴᴅ ᴠᴇʀɪꜰʏ ᴛɪᴍᴇ ꜰᴏʀ {title}\n\nᴛɪᴍᴇ - <code>{time}</code></b>")
    await client.send_message(LOG_CHANNEL, f"#Set_2nd_Verify_Time\n\nɢʀᴏᴜᴘ ɴᴀᴍᴇ : {title}\n\nɢʀᴏᴜᴘ ɪᴅ : {grp_id}\n\nɪɴᴠɪᴛᴇ ʟɪɴᴋ : {invite_link}\n\nᴜᴘᴅᴀᴛᴇᴅ ʙʏ : {message.from_user.username}")
@Client.on_message(filters.command('set_time_2'))
async def set_time_2(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")       
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text(script.NT_ADMIN_ALRT_TXT)
    try:
        time = int(message.text.split(" ", 1)[1])
    except Exception:
        return await message.reply_text("<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ\n\nᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʟɪᴋᴇ ᴛʜɪꜱ - <code>/set_time 3600</code> [ ᴛɪᴍᴇ ᴍᴜꜱᴛ ʙᴇ ɪɴ ꜱᴇᴄᴏɴᴅꜱ ]</b>")   
    await save_group_settings(grp_id, 'third_verify_time', time)
    await message.reply_text(f"<b>✅️ ꜱᴜᴄᴄESꜱꜰᴜʟʟʏ ꜱᴇᴛ 3ʀᴅ ᴠᴇʀɪꜰʏ ᴛɪᴍᴇ ꜰᴏʀ {title}\n\nᴛɪᴍᴇ - <code>{time}</code></b>")
    await client.send_message(LOG_CHANNEL, f"#Set_3rd_Verify_Time\n\nɢʀᴏᴜᴘ ɴᴀᴍᴇ : {title}\n\nɢʀᴏᴜᴘ ɪᴅ : {grp_id}\n\nɪɴᴠɪᴛᴇ ʟɪɴᴋ : {invite_link}\n\nᴜᴘᴅᴀᴛᴇᴅ ʙʏ : {message.from_user.username}")


@Client.on_message(filters.command('details'))
async def all_settings(client, message):
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text(script.NT_ADMIN_ALRT_TXT)
    try:
        settings = await get_settings(grp_id)
    except Exception as e:
        return await message.reply_text(f"<b>⚠️ ᴇʀʀᴏʀ ꜰᴇᴛᴄʜɪɴɢ ꜱᴇᴛᴛɪɴɢꜱ:</b>\n<code>{e}</code>")
    text = generate_settings_text(settings, title)
    btn = [
        [InlineKeyboardButton("♻️ ʀᴇꜱᴇᴛ ꜱᴇᴛᴛɪɴɢꜱ", callback_data=f"reset_group_{grp_id}")],
        [InlineKeyboardButton("🚫 ᴄʟᴏꜱᴇ", callback_data="close_data", style=enums.ButtonStyle.DANGER)]
    ]
    dlt = await message.reply_text(text, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    await asyncio.sleep(300)
    await dlt.delete()

@Client.on_callback_query(filters.regex(r"^reset_group_(\-\d+)$"))
async def reset_group_callback(client, callback_query):
    grp_id = int(callback_query.matches[0].group(1))
    user_id = callback_query.from_user.id
    if not await is_check_admin(client, grp_id, user_id):
        return await callback_query.answer(script.NT_ADMIN_ALRT_TXT, show_alert=True)
    await callback_query.answer("♻️ ʀᴇꜱᴇᴛᴛɪɴɢ ꜱᴇᴛᴛɪɴɢꜱ...")
    defaults = {
        'shortner': SHORTENER_WEBSITE,
        'api': SHORTENER_API,
        'shortner_two': SHORTENER_WEBSITE2,
        'api_two': SHORTENER_API2,
        'shortner_three': SHORTENER_WEBSITE3,
        'api_three': SHORTENER_API3,
        'custom_shortner': False,
        'custom_shortner_two': False,
        'custom_shortner_three': False,
        'verify_time': TWO_VERIFY_GAP,
        'third_verify_time': THREE_VERIFY_GAP,
        'template': IMDB_TEMPLATE,
        'tutorial': TUTORIAL,
        'tutorial_2': TUTORIAL_2,
        'tutorial_3': TUTORIAL_3,
        'caption': CUSTOM_FILE_CAPTION,
        'log': LOG_CHANNEL,
        'is_verify': IS_VERIFY,
        'fsub': AUTH_CHANNELS
    }
    current = await get_settings(grp_id)
    if current == defaults:
        return await callback_query.answer("✅ ꜱᴇᴛᴛɪɴɢꜱ ᴀʟʀᴇᴀᴅʏ ᴅᴇꜰᴀᴜʟᴛ.", show_alert=True)
    for key, value in defaults.items():
        await save_group_settings(grp_id, key, value)
    updated = await get_settings(grp_id)
    title = callback_query.message.chat.title
    text = generate_settings_text(updated, title, reset_done=True)
    buttons = [
        [InlineKeyboardButton("♻️ ʀᴇꜱᴇᴛ ꜱᴇᴛᴛɪɴɢꜱ", callback_data=f"reset_group_{grp_id}")],
        [InlineKeyboardButton("🚫 ᴄʟᴏꜱᴇ", callback_data="close_data", style=enums.ButtonStyle.DANGER)]
    ]
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

@Client.on_message(filters.command("verify") & filters.user(ADMINS))
async def verify(bot, message):
    try:
        chat_type = message.chat.type
        if chat_type == enums.ChatType.PRIVATE:
            return await message.reply_text("ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴡᴏʀᴋs ᴏɴʟʏ ɪɴ ɢʀᴏᴜᴘs!")
        if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grpid = message.chat.id
            command_text = message.text.split(' ')[1] if len(message.text.split(' ')) > 1 else None
            if command_text == "off":
                await save_group_settings(grpid, 'is_verify', False)
                return await message.reply_text("✓ ᴠᴇʀɪꜰʏ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅɪsᴀʙʟᴇᴅ.")
            elif command_text == "on":
                await save_group_settings(grpid, 'is_verify', True)
                return await message.reply_text("✗ ᴠᴇʀɪꜰʏ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴇɴᴀʙʟᴇᴅ.")
            else:
                return await message.reply_text("ʜɪ, ᴛᴏ ᴇɴᴀʙʟᴇ ᴠᴇʀɪꜰʏ, ᴜsᴇ <code>/verify on</code> ᴀɴᴅ ᴛᴏ ᴅɪsᴀʙʟᴇ ᴠᴇʀɪꜰʏ, ᴜsᴇ <code>/verify off</code>.")
    except Exception as e:
        logger.error("Error: %s", e)
        await message.reply_text(f"Error: {e}")

@Client.on_message(filters.command('set_fsub'))
async def set_fsub(client, message):
    try:
        userid = message.from_user.id if message.from_user else None
        if not userid:
            return await message.reply("<b>You are Anonymous admin you can't use this command !</b>")
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            return await message.reply_text("ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴄᴀɴ ᴏɴʟʏ ʙᴇ ᴜsᴇᴅ ɪɴ ɢʀᴏᴜᴘs")
        grp_id = message.chat.id
        title = message.chat.title
        if not await is_check_admin(client, grp_id, userid):
            return await message.reply_text(script.NT_ADMIN_ALRT_TXT)
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return await message.reply_text(
                "ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ!\n\n"
                "ᴄᴀɴ ᴀᴅᴅ ᴍᴜʟᴛɪᴘʟᴇ ᴄʜᴀɴɴᴇʟs sᴇᴘᴀʀᴀᴛᴇᴅ ʙʏ sᴘᴀᴄᴇs. ʟɪᴋᴇ: /sᴇᴛ_ғsᴜʙ ɪᴅ1 ɪᴅ2 ɪᴅ3\n"
            )
        option = args[1].strip()
        try:
            fsub_ids = [int(x) for x in option.split()]
        except ValueError:
            return await message.reply_text('ᴍᴀᴋᴇ sᴜʀᴇ ᴀʟʟ ɪᴅs ᴀʀᴇ ɪɴᴛᴇɢᴇʀs.')
        if len(fsub_ids) > 5:
            return await message.reply_text("ᴍᴀxɪᴍᴜᴍ 5 ᴄʜᴀɴɴᴇʟs ᴀʟʟᴏᴡᴇᴅ.")
        channels = "ᴄʜᴀɴɴᴇʟs:\n"
        channel_titles = []
        for id in fsub_ids:
            try:
                chat = await client.get_chat(id)
            except Exception as e:
                return await message.reply_text(
                    f"{id} ɪs ɪɴᴠᴀʟɪᴅ!\nᴍᴀᴋᴇ sᴜʀᴇ ᴛʜɪs ʙᴏᴛ ɪs ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ.\n\nError - {e}"
                )
            if chat.type != enums.ChatType.CHANNEL:
                return await message.reply_text(f"{id} ɪs ɴᴏᴛ ᴀ ᴄʜᴀɴɴᴇʟ.")
            channel_titles.append(f"{chat.title} (`{id}`)")
            channels += f'{chat.title}\n'
        await save_group_settings(grp_id, 'fsub', fsub_ids)
        await message.reply_text(f"sᴜᴄᴄᴇssғᴜʟʟʏ sᴇᴛ ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ(ꜱ) ғᴏʀ {title} ᴛᴏ\n\n{channels}")
        mention = message.from_user.mention if message.from_user else "Unknown"
        await client.send_message(
            LOG_CHANNEL,
            f"#Fsub_Channel_set\n\n"
            f"ᴜꜱᴇʀ - {mention} ꜱᴇᴛ ᴛʜᴇ ꜰᴏʀᴄᴇ ᴄʜᴀɴɴᴇʟ(ꜱ) ꜰᴏʀ {title}:\n\n"
            f"ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ(ꜱ):\n" + '\n'.join(channel_titles)
        )
    except Exception as e:
        err_text = f"⚠️ Error in set_fSub :\n{e}"
        logger.error(err_text)
        await client.send_message(LOG_CHANNEL, err_text)

@Client.on_message(filters.private & filters.command("resetallgroup") & filters.user(ADMINS))
async def reset_all_settings(client, message):
    try:
        reset_count = await db.dreamx_reset_settings()
        await message.reply_text(
            f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ꜱᴇᴛᴛɪɴɢꜱ ꜰᴏʀ  <code>{reset_count}</code> ɢʀᴏᴜᴘꜱ. ᴅᴇꜰᴀᴜʟᴛ ᴠᴀʟᴜᴇꜱ ᴡɪʟʟ ʙᴇ ᴜꜱᴇᴅ ✅</b>",
            quote=True
        )
    except Exception as e:
        logger.error("reset_all_settings: %s", e)
        await message.reply_text(
            "<b>🚫 An error occurred while resetting group settings.\nPlease try again later.</b>",
            quote=True
        )

@Client.on_message(filters.command("trial_reset"))
async def reset_trial(client, message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.reply("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀɴʏ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ.")
        return
    try:
        if len(message.command) > 1:
            target_user_id = int(message.command[1])
            updated_count = await db.reset_free_trial(target_user_id)
            message_text = f"ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ʀᴇꜱᴇᴛ ꜰʀᴇᴇ ᴛʀᴀɪʟ ꜰᴏʀ ᴜꜱᴇʀꜱ {target_user_id}." if updated_count else f"ᴜꜱᴇʀ {target_user_id} ɴᴏᴛ ꜰᴏᴜɴᴅ ᴏʀ ᴅᴏɴ'ᴛ ᴄʟᴀɪᴍ ꜰʀᴇᴇ ᴛʀᴀɪʟ ʏᴇᴛ."
        else:
            updated_count = await db.reset_free_trial()
            message_text = f"ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ʀᴇꜱᴇᴛ ꜰʀᴇᴇ ᴛʀᴀɪʟ ꜰᴏʀ {updated_count} ᴜꜱᴇʀꜱ."
        await message.reply_text(message_text)
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")


@Client.on_message(filters.command('remove_fsub'))
async def remove_fsub(client, message):
    try:
        user = message.from_user
        if not user:
            return await message.reply("ʏᴏᴜ ᴀʀᴇ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ — ʏᴏᴜ ᴄᴀɴ'ᴛ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ!")
        if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            return await message.reply_text("ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴄᴀɴ ᴏɴʟʏ ʙᴇ ᴜsᴇᴅ ɪɴ ɢʀᴏᴜᴘs.")
        grp_id = message.chat.id
        title = message.chat.title
        if not await is_check_admin(client, grp_id, user.id):
            return await message.reply_text(script.NT_ADMIN_ALRT_TXT)
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return await message.reply_text(
                "ᴜsᴀɢᴇ:\n"
                "• /remove_fsub ᴀʟʟ → ʀᴇᴍᴏᴠᴇ ᴀʟʟ ғsᴜʙ ᴄʜᴀɴɴᴇʟs\n"
                "• /remove_fsub ɪᴅ1 ɪᴅ2 ... → ʀᴇᴍᴏᴠᴇ sᴘᴇᴄɪғɪᴄ ᴄʜᴀɴɴᴇʟ ɪᴅs"
            )
        option = args[1].strip()
        settings = await get_settings(grp_id)
        cr_fsubs = settings.get("fsub", []) if settings else []
        if not cr_fsubs:
            return await message.reply_text("ɴᴏ ғsᴜʙ ᴄʜᴀɴɴᴇʟs ᴀʀᴇ sᴇᴛ ғᴏʀ ᴛʜɪs ɢʀᴏᴜᴘ.")
        if option.lower() == "all":
            await save_group_settings(grp_id, 'fsub', [])
            await message.reply_text(f"✅ ᴀʟʟ ғsᴜʙ ᴄʜᴀɴɴᴇʟs ʀᴇᴍᴏᴠᴇᴅ ғᴏʀ {title}")
            return await client.send_message(
                LOG_CHANNEL,
                f"#ғsᴜʙ_ʀᴇᴍᴏᴠᴇᴅ\n\n👤 {user.mention} ʀᴇᴍᴏᴠᴇᴅ ᴀʟʟ ғsᴜʙ ᴄʜᴀɴɴᴇʟs ғᴏʀ {title}."
            )
        try:
            remove_ids = [int(x) for x in option.split()]
        except ValueError:
            return await message.reply_text("ᴍᴀᴋᴇ sᴜʀᴇ ᴀʟʟ ɪᴅs ᴀʀᴇ ᴠᴀʟɪᴅ ɪɴᴛᴇɢᴇʀs.")

        new_fsubs = [cid for cid in cr_fsubs if cid not in remove_ids]
        r_id = [cid for cid in cr_fsubs if cid in remove_ids]
        if not r_id:
            return await message.reply_text("ɴᴏɴᴇ ᴏғ ᴛʜᴇ ɢɪᴠᴇɴ ɪᴅs ᴡᴇʀᴇ ғᴏᴜɴᴅ ɪɴ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ғsᴜʙ ʟɪsᴛ.")
        await save_group_settings(grp_id, 'fsub', new_fsubs)
        r_t = []
        for cid in r_id:
            try:
                chat = await client.get_chat(cid)
                r_t.append(f"• {chat.title} ({cid})")
            except Exception:
                r_t.append(f"• ᴜɴᴋɴᴏᴡɴ ({cid})")

        await message.reply_text(
            f"✅ ʀᴇᴍᴏᴠᴇᴅ {len(r_id)} ғsᴜʙ ᴄʜᴀɴɴᴇʟ(s) ғʀᴏᴍ {title}:\n" +
            "\n".join(r_t)
        )
        await client.send_message(
            LOG_CHANNEL,
            f"#ғsᴜʙ_ᴄʜᴀɴɴᴇʟ_ʀᴇᴍᴏᴠᴇᴅ\n\n👤 {user.mention} ʀᴇᴍᴏᴠᴇᴅ ғsᴜʙ ᴄʜᴀɴɴᴇʟ(s) ғʀᴏᴍ {title}:\n" +
            "\n".join(r_t)
        )
    except Exception as e:
        logger.error("remove_fsub: %s", e)
        await message.reply_text(f"⚠️ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")

@Client.on_message(filters.command('clean_groups') & filters.user(ADMINS))
async def clean_groups_handler(client, message):
    msg = await message.reply('Cleaning groups... This may take a while.', quote=True)
    deleted_count = 0
    total_groups = await db.total_chat_count()
    processed = 0
    batch_size = 100
    chats = await db.get_all_chats()
    async for chat in chats:
        try:
            processed += 1
            chat_id = chat['id']
            try:
                await client.get_chat_member(chat_id, client.me.id)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await client.get_chat_member(chat_id, client.me.id)
                except (UserNotParticipant, PeerIdInvalid, ChannelInvalid):
                    await db.delete_chat(chat_id)
                    deleted_count += 1
                except Exception:
                    pass
            except (UserNotParticipant, PeerIdInvalid, ChannelInvalid):
                await db.delete_chat(chat_id)
                deleted_count += 1
            except Exception as e:
                logger.error("Error checking chat %s: %s", chat_id, e)
                pass
            if processed % batch_size == 0:
                try:
                    await msg.edit(f'Progress: {processed}/{total_groups}\nDeleted: {deleted_count}')
                    await asyncio.sleep(2)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    await msg.edit(f'Progress: {processed}/{total_groups}\nDeleted: {deleted_count}')
        except Exception as e:
            logger.error("Error in clean_groups loop: %s", e)
    await msg.edit(f'**Clean Groups Complete**\n\nTotal Processed: {processed}\nDeleted: {deleted_count}')
