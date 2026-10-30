import logging
from pyrogram import Client, filters, enums, StopPropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified
from info import ADMINS, SUPPORT_CHAT_ID
from database.users_chats_db import db
from Script import script
from utils import temp

logger = logging.getLogger(__name__)


def build_maintenance_panel(bot_mention: str, is_maintenance: bool):
    """Generate aesthetic UI text and inline keyboard for Maintenance Mode panel."""
    status_badge = "🟢 <b>ᴏɴ (ᴇɴᴀʙʟᴇᴅ)</b>" if is_maintenance else "🔴 <b>ᴏғғ (ᴅɪꜱᴀʙʟᴇᴅ)</b>"
    
    text = (
        "<b>╭────────[ 🛠️ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴘᴀɴᴇʟ ]────────⍟</b>\n"
        f"<b>├⍟ ʙᴏᴛ :</b> {bot_mention}\n"
        f"<b>├⍟ ꜱᴛᴀᴛᴜꜱ :</b> {status_badge}\n"
        "<b>╰─────────────────────────────────────⍟</b>\n\n"
        "<blockquote>⚙️ <i>ᴡʜᴇɴ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ ɪꜱ <b>ᴏɴ</b>, ɴᴏʀᴍᴀʟ ᴜꜱᴇʀꜱ ᴡɪʟʟ ʙᴇ ʙʟᴏᴄᴋᴇᴅ ᴡɪᴛʜ ᴀɴ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪᴄᴇ. ᴀᴅᴍɪɴꜱ ᴄᴀɴ ꜱᴛɪʟʟ ᴀᴄᴄᴇꜱꜱ ᴀʟʟ ꜰᴇᴀᴛᴜʀᴇꜱ.</i></blockquote>\n\n"
        "<b>👇 ᴜꜱᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ ᴛᴏɢɢʟᴇ :</b>"
    )

    toggle_btn = (
        InlineKeyboardButton("🔴 ᴛᴜʀɴ ᴏғғ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ", callback_data="maintenance_off")
        if is_maintenance
        else InlineKeyboardButton("🟢 ᴛᴜʀɴ ᴏɴ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ", callback_data="maintenance_on")
    )

    buttons = [
        [toggle_btn],
        [
            InlineKeyboardButton("🔄 ʀᴇꜰʀᴇꜱʜ", callback_data="maintenance_refresh"),
            InlineKeyboardButton("🚫 ᴄʟᴏꜱᴇ", callback_data="close_data")
        ]
    ]
    return text, InlineKeyboardMarkup(buttons)


@Client.on_message(filters.text & (filters.group | filters.private) & filters.incoming & ~filters.regex(r"^/") & ~filters.user(ADMINS) & ~filters.chat(SUPPORT_CHAT_ID), group=-5)
async def maintenance_interceptor(client: Client, message: Message):
    bot_id = temp.ME or getattr(client.me, "id", None)
    if bot_id and await db.maintenance_status(bot_id):
        user_mention = message.from_user.mention if message.from_user else "User"
        await message.reply_text(
            text=script.MAINTENANCE_TXT.format(user_mention),
            parse_mode=enums.ParseMode.HTML
        )
        raise StopPropagation


@Client.on_callback_query(~filters.user(ADMINS) & ~filters.chat(SUPPORT_CHAT_ID), group=-5)
async def maintenance_callback_interceptor(client: Client, query: CallbackQuery):
    bot_id = temp.ME or getattr(client.me, "id", None)
    if bot_id and await db.maintenance_status(bot_id):
        await query.answer(
            text="⚠️ ᴛʜɪꜱ ꜱᴇʀᴠɪᴄᴇ ɪꜱ ᴄᴜʀʀᴇɴᴛʟʏ ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ! ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ. 😊",
            show_alert=True
        )
        raise StopPropagation


@Client.on_message(filters.command("maintenance") & filters.user(ADMINS))
async def maintenance_cmd(client: Client, message: Message):
    bot_id = temp.ME or getattr(client.me, "id", None)
    is_maintenance = await db.maintenance_status(bot_id)
    bot_mention = temp.B_LINK or f"@{temp.U_NAME}" or "Auto Filter Bot"

    text, reply_markup = build_maintenance_panel(bot_mention, is_maintenance)
    await message.reply_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_callback_query(filters.regex(r"^maintenance_") & filters.user(ADMINS))
async def maintenance_toggle_callback(client: Client, query: CallbackQuery):
    bot_id = temp.ME or getattr(client.me, "id", None)
    action = query.data.split("_")[1]

    if action == "on":
        await db.update_maintenance_status(bot_id, True)
        await query.answer("🟢 ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ ᴇɴᴀʙʟᴇᴅ!", show_alert=True)
    elif action == "off":
        await db.update_maintenance_status(bot_id, False)
        await query.answer("🔴 ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ ᴅɪꜱᴀʙʟᴇᴅ!", show_alert=True)
    elif action == "refresh":
        await query.answer("🔄 ꜱᴛᴀᴛᴜꜱ ʀᴇꜰʀᴇꜱʜᴇᴅ!")

    # Refresh the UI panel
    is_maintenance = await db.maintenance_status(bot_id)
    bot_mention = temp.B_LINK or f"@{temp.U_NAME}" or "Auto Filter Bot"
    text, reply_markup = build_maintenance_panel(bot_mention, is_maintenance)

    try:
        await query.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    except MessageNotModified:
        pass
    except Exception as e:
        logger.warning("Error editing maintenance panel: %s", e)
