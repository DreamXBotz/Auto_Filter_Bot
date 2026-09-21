from pyrogram import Client, filters , StopPropagation
from utils import temp
from pyrogram.types import Message
from database.users_chats_db import db
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import SUPPORT_CHAT, ADMINS
import os

async def banned_users(_, client, message: Message):
    return bool(message.from_user and message.from_user.id in temp.BANNED_USERS)

banned_user = filters.create(banned_users)

@Client.on_message(filters.command('banned') & filters.user(ADMINS))
async def get_banned(client, message):
    banned_users, _ = await db.get_banned()
    if not banned_users:
        await message.reply_text("No banned users found.")
        return
    
    text = ""
    for user_id in banned_users:
        try:
            user = await client.get_users(user_id)
            text += f"{user.mention} (`{user.id}`)\n"
        except Exception:
            text += f"Undefined (`{user_id}`)\n"
    
    if len(text) > 4096:
        with open('banned_users.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        await message.reply_document('banned_users.txt')
        os.remove('banned_users.txt')
    else:
        await message.reply_text(text)

async def disabled_chat(_, client, message: Message):
    return message.chat.id in temp.BANNED_CHATS
disabled_group=filters.create(disabled_chat)

@Client.on_message(filters.private & banned_user & filters.incoming , group=-1)
async def ban_reply(bot, message):
    ban = await db.get_ban_status(message.from_user.id)
    await message.reply(f'Sorry Dude, You are Banned from using Me. \nBan Reason : {ban["ban_reason"]}')
    raise StopPropagation

@Client.on_message(filters.group & disabled_group & filters.incoming , group=-1)
async def grp_bd(bot, message):
    buttons = [[
        InlineKeyboardButton('Support', url=SUPPORT_CHAT)
    ]]
    reply_markup=InlineKeyboardMarkup(buttons)
    vazha = await db.get_chat(message.chat.id)
    k = await message.reply(
        text=f"CHAT NOT ALLOWED 🐞\n\nMy admins have restricted me from working here ! If you want to know more about it contact support..\nReason : <code>{vazha['reason']}</code>.",
        reply_markup=reply_markup)
    try:
        await k.pin()
    except Exception:
        pass
    await bot.leave_chat(message.chat.id)
    raise StopPropagation
