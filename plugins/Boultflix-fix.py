import logging
from pyrogram import Client, filters, enums
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_size, clean_filename, temp
from database.ia_filterdb import get_search_results

logger = logging.getLogger(__name__)

# ==========================================
# 1. FIX: ABOUT & START MENUS (NO CRASH / UNRESPONSIVE)
# ==========================================
@Client.on_callback_query(filters.regex(r"^about"), group=-1)
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
        [InlineKeyboardButton("📢 Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇﻟ 📢", url="https://t.me/+f-k01NScSxEyNzc1")],
        [InlineKeyboardButton("📑 Hᴇʟᴘ", callback_data="help_menu"), InlineKeyboardButton("ℹ️ Aʙᴏᴜᴛ", callback_data="about")]
    ])
    try:
        await query.message.edit_caption(caption=caption, reply_markup=buttons)
    except Exception:
        await query.message.edit_text(text=caption, reply_markup=buttons)


# ==========================================
# 2. FIX: QUALITY, LANGUAGE & SEASON FILTER BUTTONS
# ==========================================
@Client.on_callback_query(filters.regex(r"^(btn_quality|filter_quality|QUALITY)"), group=-1)
async def fix_quality_buttons(client: Client, query: CallbackQuery):
    await query.answer("Select Quality")
    q_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("360P", callback_data="filter_exec_360p"), InlineKeyboardButton("480P", callback_data="filter_exec_480p")],
        [InlineKeyboardButton("720P", callback_data="filter_exec_720p"), InlineKeyboardButton("1080P", callback_data="filter_exec_1080p")],
        [InlineKeyboardButton("1440P", callback_data="filter_exec_1440p"), InlineKeyboardButton("2160P", callback_data="filter_exec_2160p")],
        [InlineKeyboardButton("4K", callback_data="filter_exec_4k")],
        [InlineKeyboardButton("« Bᴀᴄᴋ Tᴏ Fɪʟᴇs »", callback_data="close_data")]
    ])
    try:
        await query.message.edit_reply_markup(reply_markup=q_markup)
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^(btn_language|filter_language|LANGUAGE)"), group=-1)
async def fix_language_buttons(client: Client, query: CallbackQuery):
    await query.answer("Select Language")
    l_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Mᴀʟᴀʏᴀʟᴀᴍ", callback_data="filter_exec_malayalam"), InlineKeyboardButton("Tᴀᴍɪʟ", callback_data="filter_exec_tamil")],
        [InlineKeyboardButton("Eɴɢʟɪsʜ", callback_data="filter_exec_english"), InlineKeyboardButton("Hɪɴᴅɪ", callback_data="filter_exec_hindi")],
        [InlineKeyboardButton("Tᴇʟᴜɢᴜ", callback_data="filter_exec_telugu"), InlineKeyboardButton("Kᴀɴɴᴀᴅᴀ", callback_data="filter_exec_kannada")],
        [InlineKeyboardButton("Gᴜᴊᴀʀᴀᴛɪ", callback_data="filter_exec_gujarati"), InlineKeyboardButton("Mᴀʀᴀᴛʜɪ", callback_data="filter_exec_marathi")],
        [InlineKeyboardButton("Pᴜɴᴊᴀʙɪ", callback_data="filter_exec_punjabi"), InlineKeyboardButton("Dᴜᴀʟ Aᴜᴅɪᴏ", callback_data="filter_exec_dual")],
        [InlineKeyboardButton("« Bᴀᴄᴋ Tᴏ Fɪʟᴇs »", callback_data="close_data")]
    ])
    try:
        await query.message.edit_reply_markup(reply_markup=l_markup)
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^(btn_season|filter_season|SEASON)"), group=-1)
async def fix_season_buttons(client: Client, query: CallbackQuery):
    await query.answer("Select Season")
    s_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Sᴇᴀsᴏɴ 1", callback_data="filter_exec_s01"), InlineKeyboardButton("Sᴇᴀsᴏɴ 2", callback_data="filter_exec_s02")],
        [InlineKeyboardButton("Sᴇᴀsᴏɴ 3", callback_data="filter_exec_s03"), InlineKeyboardButton("Sᴇᴀsᴏɴ 4", callback_data="filter_exec_s04")],
        [InlineKeyboardButton("Sᴇᴀsᴏɴ 5", callback_data="filter_exec_s05"), InlineKeyboardButton("Sᴇᴀsᴏɴ 6", callback_data="filter_exec_s06")],
        [InlineKeyboardButton("« Bᴀᴄᴋ Tᴏ Fɪʟᴇs »", callback_data="close_data")]
    ])
    try:
        await query.message.edit_reply_markup(reply_markup=s_markup)
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^filter_exec_"), group=-1)
async def handle_filter_execution(client: Client, query: CallbackQuery):
    tag = query.data.replace("filter_exec_", "")
    await query.answer(f"Filtering files with '{tag.upper()}'... 🍿", show_alert=False)
