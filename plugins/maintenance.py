from pyrogram import Client, filters, enums, StopPropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import ADMINS, SUPPORT_CHAT_ID
from database.users_chats_db import db
from Script import script
from utils import temp
import logging

logger = logging.getLogger(__name__)


@Client.on_message(filters.text & (filters.group | filters.private) & filters.incoming & ~filters.regex(r"^/") & ~filters.user(ADMINS) & ~filters.chat(SUPPORT_CHAT_ID), group=-5)
async def maintenance_interceptor(bot: Client, message: Message):
    bot_id = temp.ME
    if await db.maintenance_status(bot_id):
        user_mention = message.from_user.mention if message.from_user else "User"
        await message.reply_text(
            text=script.MAINTENANCE_TXT.format(user_mention),
            parse_mode=enums.ParseMode.HTML
        )
        raise StopPropagation

@Client.on_callback_query(~filters.user(ADMINS) & ~filters.chat(SUPPORT_CHAT_ID), group=-5)
async def maintenance_callback_interceptor(bot: Client, query: CallbackQuery):
    bot_id = temp.ME
    if await db.maintenance_status(bot_id):
        await query.answer(
            text="The service is currently under maintenance. Please try again later.",
            show_alert=True
        )
        raise StopPropagation

@Client.on_message(filters.command("maintenance") & filters.user(ADMINS))
async def maintenance_cmd(bot: Client, message: Message):
    bot_id = temp.ME
    is_maintenance = await db.maintenance_status(bot_id)
    
    status_text = "<b>Enabled 🟢</b>" if is_maintenance else "<b>Disabled 🔴</b>"
    
    buttons = [
        [
            InlineKeyboardButton(
                "Turn ON" if not is_maintenance else "Already ON",
                callback_data="maintenance_on" if not is_maintenance else "none"
            ),
            InlineKeyboardButton(
                "Turn OFF" if is_maintenance else "Already OFF",
                callback_data="maintenance_off" if is_maintenance else "none"
            )
        ]
    ]
    
    await message.reply_text(
        text=f"<b>🛠️ Maintenance Mode Status</b>\n\nCurrent Status: {status_text}\n\nUse the buttons below to toggle maintenance mode.",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_callback_query(filters.regex(r"^maintenance_") & filters.user(ADMINS))
async def maintenance_toggle_callback(bot: Client, query: CallbackQuery):
    bot_id = temp.ME
    action = query.data.split("_")[1]
    
    if action == "on":
        await db.update_maintenance_status(bot_id, True)
        await query.answer("Maintenance Mode Enabled 🟢", show_alert=True)
    elif action == "off":
        await db.update_maintenance_status(bot_id, False)
        await query.answer("Maintenance Mode Disabled 🔴", show_alert=True)
    
    # Update message
    is_maintenance = await db.maintenance_status(bot_id)
    status_text = "<b>Enabled 🟢</b>" if is_maintenance else "<b>Disabled 🔴</b>"
    
    buttons = [
        [
            InlineKeyboardButton(
                "Turn ON" if not is_maintenance else "Already ON",
                callback_data="maintenance_on" if not is_maintenance else "none"
            ),
            InlineKeyboardButton(
                "Turn OFF" if is_maintenance else "Already OFF",
                callback_data="maintenance_off" if is_maintenance else "none"
            )
        ]
    ]
    
    try:
        await query.message.edit_text(
            text=f"<b>🛠️ Maintenance Mode Status</b>\n\nCurrent Status: {status_text}\n\nUse the buttons below to toggle maintenance mode.",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass

@Client.on_callback_query(filters.regex("none"))
async def none_callback(bot, query):
    await query.answer("Already in this state!", show_alert=False)
