import os
import re
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from pyrogram import Client, filters, enums
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import MessageNotModified
from shortzy import Shortzy

from info import (
    SHORTENER_API,
    SHORTENER_WEBSITE,
    UPDATES_CHANNEL_URL if 'UPDATES_CHANNEL_URL' in globals() else 'UPDATE_CHNL_LNK',
    LOG_CHANNEL
)
from utils import temp, get_size, clean_filename
from database.users_chats_db import db
from database.ia_filterdb import get_file_details, get_search_results

logger = logging.getLogger(__name__)

UPDATES_LINK = "https://t.me/+f-k01NScSxEyNzc1"
DELETE_TIME = 300  # 5 minutes auto-delete timer

# ==========================================
# 1. 24-HOURS TOKEN VERIFICATION SYSTEM
# ==========================================
async def is_user_verified_24h(user_id: int):
    user = await db.get_notcopy_user(user_id)
    if not user:
        return False
    
    last_verified = user.get("last_verified")
    if not last_verified:
        return False

    ist_timezone = pytz.timezone('Asia/Kolkata')
    if last_verified.tzinfo is None:
        last_verified = ist_timezone.localize(last_verified)
    else:
        last_verified = last_verified.astimezone(ist_timezone)
        
    current_time = datetime.now(tz=ist_timezone)
    time_diff = (current_time - last_verified).total_seconds()
    
    # 24 Hours = 86400 Seconds
    return time_diff < 86400

async def set_user_verified_24h(user_id: int):
    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(tz=ist_timezone)
    await db.update_notcopy_user(user_id, {"last_verified": current_time})

# ==========================================
# 2. START HANDLER INTERCEPTOR (VERIFICATION + AUTO-DELETE)
# ==========================================
@Client.on_message(filters.command("start") & filters.private, group=-2)
async def fix_start_delivery_interceptor(client: Client, message: Message):
    user_id = message.from_user.id
    command_parts = message.text.split()

    if len(command_parts) > 1:
        param = command_parts[1]
        
        # 1. Handle Verification Return Token
        if param.startswith("verify_"):
            verify_token = param.replace("verify_", "")
            verify_doc = await db.get_verify_id_info(user_id, verify_token)
            if verify_doc:
                await set_user_verified_24h(user_id)
                await message.reply_text(
                    "<b>✅ Vᴇʀɪғɪᴄᴀᴛɪᴏɴ Sᴜᴄᴄᴇssғᴜʟ!</b>\n\n"
                    "Yᴏᴜ ɴᴏᴡ ʜᴀᴠᴇ ᴜɴʟɪᴍɪᴛᴇᴅ ᴀᴄᴄᴇss ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ ғɪʟᴇs ғᴏʀ ᴛʜᴇ ɴᴇxᴛ <b>24 Hᴏᴜʀs</b>! 🍿⚡",
                    quote=True
                )
                return
            else:
                await message.reply_text("<b>❌ Iɴᴠᴀʟɪᴅ ᴏʀ Exᴘɪʀᴇᴅ Vᴇʀɪғɪᴄᴀᴛɪᴏɴ Lɪɴᴋ!</b>", quote=True)
                return

        # 2. Handle File Delivery (Deep Links)
        if param.startswith("file_") or param.startswith("getfile-"):
            # Check 24 Hours Verification Status
            is_verified = await is_user_verified_24h(user_id)
            has_prem = await db.has_premium_access(user_id)
            
            if not is_verified and not has_prem and SHORTENER_API and SHORTENER_WEBSITE:
                token_hash = str(user_id) + "_" + str(int(datetime.now().timestamp()))
                await db.create_verify_id(user_id, token_hash)
                
                bypass_url = f"https://t.me/{temp.U_NAME}?start=verify_{token_hash}"
                try:
                    shortzy = Shortzy(SHORTENER_API, SHORTENER_WEBSITE)
                    short_link = await shortzy.convert(bypass_url)
                except Exception:
                    short_link = bypass_url

                v_btn = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔓 Cʟɪᴄᴋ Hᴇʀᴇ Tᴏ Vᴇʀɪғʏ (24h) 🔓", url=short_link)],
                    [InlineKeyboardButton("❓ Hᴏᴡ Tᴏ Vᴇʀɪғʏ (Tᴜᴛᴏʀɪᴀʟ) ❓", url=UPDATES_LINK)]
                ])
                await message.reply_text(
                    f"👋 Hᴇʏ <b>{message.from_user.mention}</b>,\n\n"
                    f"⚠️ <b>Aᴄᴄᴇss Dᴇɴɪᴇᴅ: Vᴇʀɪғɪᴄᴀᴛɪᴏɴ Rᴇǫᴜɪʀᴇᴅ!</b>\n\n"
                    f"Pʟᴇᴀsᴇ ᴠᴇʀɪғʏ ʏᴏᴜʀ ᴛᴏᴋᴇɴ ᴛᴏ ɢᴇᴛ <b>24 Hᴏᴜʀs Uɴʟɪᴍɪᴛᴇᴅ Fɪʟᴇ Aᴄᴄᴇss</b>. "
                    f"Cʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ 👇",
                    reply_markup=v_btn,
                    quote=True
                )
                message.stop_propagation()
                return

            # Extract File ID
            file_id = param.split("_")[-1] if "_" in param else param.replace("getfile-", "")
            files_ = await get_file_details(file_id)
            if files_:
                file_info = files_[0]
                file_btn = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📌 JOIN UPDATES CHANNEL 📌", url=UPDATES_LINK)]
                ])
                caption = f"📁 <b>FILENAME :</b> {clean_filename(file_info.file_name)}\n\n⚙️ <b>SIZE :</b> {get_size(file_info.file_size)}"
                
                try:
                    sent_msg = await client.send_cached_media(
                        chat_id=user_id,
                        file_id=file_info.file_id,
                        caption=caption,
                        reply_markup=file_btn
                    )
                    
                    # Auto-Delete Warning Banner
                    warn_text = (
                        "⚠️ <b>THIS MOVIE FILE/VIDEO WILL BE DELETED IN 5 MINUTE\n\n"
                        "<i>PLEASE FORWARD THIS FILE TO SOMEWHERE ELSE & START DOWNLOADING THERE</i></b>"
                    )
                    warn_msg = await message.reply_text(warn_text)

                    async def auto_delete_task():
                        await asyncio.sleep(DELETE_TIME)
                        try:
                            await sent_msg.delete()
                            await warn_msg.edit_text("❌ <b>YOUR VIDEO / FILE IS SUCCESSFULLY DELETED TO PROTECT THIS BOT FROM COPYRIGHT TAKEDOWN ✨🎬</b>")
                        except Exception:
                            pass

                    asyncio.create_task(auto_delete_task())
                    message.stop_propagation()
                    return
                except Exception as e:
                    logger.error(f"Send Cached Media Error: {e}")

# ==========================================
# 3. ABOUT, DISCLAIMER & HOME MENU CALLBACKS
# ==========================================
@Client.on_callback_query(filters.regex(r"^(about|about_menu)"), group=-1)
async def fix_about_callback(client: Client, query: CallbackQuery):
    await query.answer("About Details")
    about_text = (
        "╭─────[ <b>Mʏ Dᴇᴛᴀɪʟs</b> 🫧 ]──────⍟\n"
        f"├⍟ <b>Mʏ Nᴀᴍᴇ :</b> <a href='https://t.me/{temp.U_NAME}'>Bᴏᴜʟᴛғʟɪx Mᴏᴠɪᴇs 🫧🫶🏼</a>\n"
        f"├⍟ <b>Dᴇᴠᴇʟᴏᴘᴇʀ :</b> <a href='https://t.me/BoultFlix'>Oᴡɴᴇʀ ⚡</a>\n"
        "├⍟ <b>Lɪʙʀᴀʀʏ :</b> <a href='https://github.com/pyrofork/pyrofork'>Pʏʀᴏɢʀᴀᴍ</a>\n"
        "├⍟ <b>Lᴀɴɢᴜᴀɢᴇ :</b> <a href='https://www.python.org'>Pʏᴛʜᴏɴ 3</a>\n"
        "├⍟ <b>Dᴀᴛᴀʙᴀsᴇ :</b> <a href='https://www.mongodb.com'>Mᴏɴɢᴏ DB</a>\n"
        "├⍟ <b>Bᴏᴛ Sᴇʀᴠᴇʀ :</b> <a href='https://render.com'>Rᴇɴᴅᴇʀ</a>\n"
        "├⍟ <b>Bᴜɪʟᴅ Sᴛᴀᴛᴜs :</b> v1.4 [ Sᴛᴀʙʟᴇ 🚀 ]\n"
        "╰───────────────⍟"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("‼️ Dɪsᴄʟᴀɪᴍᴇʀ ‼️", callback_data="disclaimer_menu")],
        [InlineKeyboardButton("⇋ Bᴀᴄᴋ ⇋", callback_data="home_menu")]
    ])
    try:
        await query.message.edit_caption(caption=about_text, reply_markup=buttons)
    except Exception:
        await query.message.edit_text(text=about_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^disclaimer_menu"), group=-1)
async def fix_disclaimer_callback(client: Client, query: CallbackQuery):
    await query.answer("Disclaimer")
    disclaimer_text = (
        "ᴛʜɪꜱ ɪꜱ ᴀɴ ᴏᴘᴇɴ ꜱᴏᴜʀᴄᴇ ᴘʀᴏᴊᴇᴄᴛ.\n\n"
        "ᴀʟʟ ᴛʜᴇ ꜰɪʟᴇꜱ ɪɴ ᴛʜɪꜱ ʙᴏᴛ ᴀʀᴇ ꜰʀᴇᴇʟʏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴏɴ ᴛʜᴇ ɪɴᴛᴇʀɴᴇᴛ ᴏʀ ᴘᴏꜱᴛᴇᴅ ʙʏ ꜱᴏᴍᴇʙᴏᴅʏ ᴇʟꜱᴇ. "
        "ᴊᴜꜱᴛ ꜰᴏʀ ᴇᴀꜱʏ ꜱᴇᴀʀᴄʜɪɴɢ ᴛʜɪꜱ ʙᴏᴛ ɪꜱ ɪɴᴅᴇxɪɴɢ ꜰɪʟᴇꜱ ᴡʜɪᴄʜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ᴜᴘʟᴏᴀᴅᴇᴅ ᴏɴ ᴛᴇʟᴇɢʀᴀᴍ."
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("⇋ Bᴀᴄᴋ ⇋", callback_data="about")]
    ])
    try:
        await query.message.edit_caption(caption=disclaimer_text, reply_markup=buttons)
    except Exception:
        await query.message.edit_text(text=disclaimer_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^home_menu"), group=-1)
async def fix_home_callback(client: Client, query: CallbackQuery):
    await query.answer("Home Menu")
    caption = (
        f"Hᴇʏ 🍿 <b>{query.from_user.mention}</b> 🥷\n\n"
        f"📍 <b>Wᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴡᴏʀʟᴅ's ᴄᴏᴏʟᴇsᴛ sᴇᴀʀᴄʜ ᴇɴɢɪɴᴇ! ⚡</b>\n\n"
        f"Hᴇʀᴇ ʏᴏᴜ ᴄᴀɴ ʀᴇǫᴜᴇsᴛ ᴍᴏᴠɪᴇs & sᴇʀɪᴇs, ᴊᴜsᴛ sᴇɴᴅ ɴᴀᴍᴇ ᴡɪᴛʜ ᴘʀᴏᴘᴇʀ <b>Gᴏᴏɢʟᴇ sᴘᴇʟʟɪɴɢ</b>..!! 🫧🎬"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔰 Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ 🔰", url=f"https://t.me/{temp.U_NAME}?startgroup=true")],
        [InlineKeyboardButton("📢 Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇﻟ 📢", url=UPDATES_LINK)],
        [InlineKeyboardButton("📑 Hᴇʟᴘ", callback_data="help_menu"), InlineKeyboardButton("ℹ️ Aʙᴏᴜᴛ", callback_data="about")]
    ])
    try:
        await query.message.edit_caption(caption=caption, reply_markup=buttons)
    except Exception:
        await query.message.edit_text(text=caption, reply_markup=buttons)

# ==========================================
# 4. QUALITY, LANGUAGE & SEASON FILTER MENUS
# ==========================================
@Client.on_callback_query(filters.regex(r"^(btn_quality|filter_quality|QUALITY)"), group=-1)
async def fix_quality_buttons(client: Client, query: CallbackQuery):
    await query.answer("Select Quality")
    q_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("360P", callback_data="filter_run#360p"), InlineKeyboardButton("480P", callback_data="filter_run#480p")],
        [InlineKeyboardButton("720P", callback_data="filter_run#720p"), InlineKeyboardButton("1080P", callback_data="filter_run#1080p")],
        [InlineKeyboardButton("1440P", callback_data="filter_run#1440p"), InlineKeyboardButton("2160P", callback_data="filter_run#2160p")],
        [InlineKeyboardButton("4K", callback_data="filter_run#4k")],
        [InlineKeyboardButton("« Bᴀᴄᴋ Tᴏ Fɪʟᴇs »", callback_data="back_to_results")]
    ])
    try:
        await query.message.edit_reply_markup(reply_markup=q_markup)
    except Exception:
        pass

@Client.on_callback_query(filters.regex(r"^(btn_language|filter_language|LANGUAGE)"), group=-1)
async def fix_language_buttons(client: Client, query: CallbackQuery):
    await query.answer("Select Language")
    l_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Mᴀʟᴀʏᴀʟᴀᴍ", callback_data="filter_run#malayalam"), InlineKeyboardButton("Tᴀᴍɪʟ", callback_data="filter_run#tamil")],
        [InlineKeyboardButton("Eɴɢʟɪsʜ", callback_data="filter_run#english"), InlineKeyboardButton("Hɪɴᴅɪ", callback_data="filter_run#hindi")],
        [InlineKeyboardButton("Tᴇʟᴜɢᴜ", callback_data="filter_run#telugu"), InlineKeyboardButton("Kᴀɴɴᴀᴅᴀ", callback_data="filter_run#kannada")],
        [InlineKeyboardButton("Gᴜᴊᴀʀᴀᴛɪ", callback_data="filter_run#gujarati"), InlineKeyboardButton("Mᴀʀᴀᴛʜɪ", callback_data="filter_run#marathi")],
        [InlineKeyboardButton("Pᴜɴᴊᴀʙɪ", callback_data="filter_run#punjabi"), InlineKeyboardButton("Dᴜᴀʟ Aᴜᴅɪᴏ", callback_data="filter_run#dual")],
        [InlineKeyboardButton("« Bᴀᴄᴋ Tᴏ Fɪʟᴇs »", callback_data="back_to_results")]
    ])
    try:
        await query.message.edit_reply_markup(reply_markup=l_markup)
    except Exception:
        pass

@Client.on_callback_query(filters.regex(r"^(btn_season|filter_season|SEASON)"), group=-1)
async def fix_season_buttons(client: Client, query: CallbackQuery):
    await query.answer("Select Season")
    s_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Sᴇᴀsᴏɴ 1", callback_data="filter_run#s01"), InlineKeyboardButton("Sᴇᴀsᴏɴ 2", callback_data="filter_run#s02")],
        [InlineKeyboardButton("Sᴇᴀsᴏɴ 3", callback_data="filter_run#s03"), InlineKeyboardButton("Sᴇᴀsᴏɴ 4", callback_data="filter_run#s04")],
        [InlineKeyboardButton("Sᴇᴀsᴏɴ 5", callback_data="filter_run#s05"), InlineKeyboardButton("Sᴇᴀsᴏɴ 6", callback_data="filter_run#s06")],
        [InlineKeyboardButton("« Bᴀᴄᴋ Tᴏ Fɪʟᴇs »", callback_data="back_to_results")]
    ])
    try:
        await query.message.edit_reply_markup(reply_markup=s_markup)
    except Exception:
        pass

# ==========================================
# 5. BACK TO FILES & FILTER EXECUTION
# ==========================================
@Client.on_callback_query(filters.regex(r"^back_to_results"), group=-1)
async def back_to_files_handler(client: Client, query: CallbackQuery):
    await query.answer("Loading original files list...")
    original_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("REMOVE ADS", callback_data="remove_ads"), InlineKeyboardButton("⚡ SEND ALL", callback_data="send_all")],
        [
            InlineKeyboardButton("QUALITY", callback_data="btn_quality"),
            InlineKeyboardButton("LANGUAGE", callback_data="btn_language"),
            InlineKeyboardButton("SEASON", callback_data="btn_season")
        ],
        [
            InlineKeyboardButton("PAGE", callback_data="ignore"),
            InlineKeyboardButton("1/1", callback_data="ignore"),
            InlineKeyboardButton("NEXT ➢", callback_data="ignore")
        ],
        [InlineKeyboardButton("« NO MORE PAGES AVAILABLE »", callback_data="ignore")]
    ])
    try:
        await query.message.edit_reply_markup(reply_markup=original_markup)
    except Exception:
        pass

@Client.on_callback_query(filters.regex(r"^filter_run#"), group=-1)
async def filter_run_handler(client: Client, query: CallbackQuery):
    tag = query.data.split("#")[1]
    await query.answer(f"Filtering files by: {tag.upper()} 🍿", show_alert=False)
