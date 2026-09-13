import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import LinkPreviewOptions, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified, FloodWait
from info import IS_VERIFY, LOG_CHANNEL
from utils import get_settings, save_group_settings, delete_group_setting, is_check_admin
from database.users_chats_db import db

logger = logging.getLogger(__name__)

async def get_invite_link(client, grp_id):
    try:
        return await client.export_chat_invite_link(int(grp_id))
    except Exception:
        try:
            chat = await client.get_chat(int(grp_id))
            return chat.invite_link or "None"
        except Exception:
            return "None"

@Client.on_callback_query(filters.regex(r'^verification_setgs'))
async def handle_verification_menu(client, query):
    grp_id = query.data.split("#")[-1]
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)

    settings = await get_settings(int(grp_id))
    is_verified = settings.get('is_verify', IS_VERIFY)
    verified_str = "ᴏɴ" if is_verified else "ᴏꜰꜰ"

    btn = [[
        InlineKeyboardButton('ᴛᴜʀɴ ᴏꜰꜰ' if is_verified else 'ᴛᴜʀɴ ᴏɴ', callback_data=f'toggleverify#is_verify#{is_verified}#{grp_id}'),
    ],[
        InlineKeyboardButton('ꜱʜᴏʀᴛɴᴇʀ', callback_data=f'changeshortner#{grp_id}'),
    ],[
        InlineKeyboardButton('ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ɢᴀᴘ', callback_data=f'changetime#{grp_id}'),
    ],[
        InlineKeyboardButton('ᴛᴜᴛᴏʀɪᴀʟ', callback_data=f'changetutorial#{grp_id}')
    ],[
        InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'grp_pm#{grp_id}')
    ]]

    text = (
        "<b>ᴀᴅᴠᴀɴᴄᴇ ꜱᴇᴛᴛɪɴɢꜱ ᴍᴏᴅᴇ 📳\n\n"
        "ʏᴏᴜ ᴄᴀɴ ᴄᴜꜱᴛᴏᴍɪᴢᴇᴅ ꜱʜᴏʀᴛɴᴇʀ ᴠᴀʟᴜᴇꜱ ᴀɴᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ɢᴀᴘ ꜰʀᴏᴍ ʜᴇʀᴇ ✅\n"
        "ᴄʜᴏᴏꜱᴇ ꜰʀᴏᴍ ʙᴇʟᴏᴡ 👇\n\n"
        f"✅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ꜱᴛᴀᴛᴜꜱ : {verified_str}</b>"
    )

    try:
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^log_setgs'))
async def handle_log_channel_menu(client, query):
    _, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.", show_alert=True)

    settings = await get_settings(int(grp_id))
    log_channel_id = settings.get('log')
    log_display = f"<code>{log_channel_id}</code>" if log_channel_id else "ɴᴏᴛ ꜱᴇᴛ"

    btn = [[
        InlineKeyboardButton('ᴄʜᴀɴɢᴇ ʟᴏɢ', callback_data=f'changelog#{grp_id}'),
        InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ ʟᴏɢ', callback_data=f'removelog#{grp_id}', style=enums.ButtonStyle.DANGER),  # type: ignore
    ],[
        InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'grp_pm#{grp_id}')
    ]]

    text = (
        "<b>ᴀᴅᴠᴀɴᴄᴇ ꜱᴇᴛᴛɪɴɢꜱ ᴍᴏᴅᴇ 📳\n\n"
        "ʏᴏᴜ ᴄᴀɴ ᴄᴜꜱᴛᴏᴍɪᴢᴇᴅ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ᴠᴀʟᴜᴇ ꜰʀᴏᴍ ʜᴇʀᴇ ✅\n"
        "ᴄʜᴏᴏꜱᴇ ꜰʀᴏᴍ ʙᴇʟᴏᴡ 👇\n\n"
        f"📝 ʟᴏɢ ᴄʜᴀɴɴᴇʟ : {log_display}</b>"
    )
    try:
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^fsub_setgs'))
async def handle_forcesub_menu(client, query):
    _, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.", show_alert=True)

    settings = await get_settings(int(grp_id))
    fsub_list = settings.get('fsub_id')
    if fsub_list and isinstance(fsub_list, list):
         fsub_str = "\n".join([f"<code>{id}</code>" for id in fsub_list])
    elif fsub_list:
         fsub_str = f"<code>{fsub_list}</code>"
    else:
         fsub_str = "ɴᴏᴛ ꜱᴇᴛ"

    btn = [[
        InlineKeyboardButton('ꜱᴇᴛ ꜰꜱᴜʙ', callback_data=f'set_fsub_ui#{grp_id}'),
        InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ ꜰꜱᴜʙ', callback_data=f'remove_fsub_ui#{grp_id}', style=enums.ButtonStyle.DANGER),  # type: ignore
    ],[
        InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'grp_pm#{grp_id}')
    ]]

    text = (
        "<b>ᴀᴅᴠᴀɴᴄᴇ ꜱᴇᴛᴛɪɴɢꜱ ᴍᴏᴅᴇ 📳\n\n"
        "ʏᴏᴜ ᴄᴀɴ ᴄᴜꜱᴛᴏᴍɪᴢᴇᴅ ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ ᴠᴀʟᴜᴇ ꜰʀᴏᴍ ʜᴇʀᴇ ✅\n"
        "ᴄʜᴏᴏꜱᴇ ꜰʀᴏᴍ ʙᴇʟᴏᴡ 👇\n\n"
        f"🚫 ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ : \n{fsub_str}</b>"
    )
    try:
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^caption_setgs'))
async def handle_custom_caption_menu(client, query):
    _, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)

    settings = await get_settings(int(grp_id))
    caption = settings.get('caption')
    caption_text = f"<code>{caption}</code>" if caption else "ɴᴏᴛ ꜱᴇᴛ"

    btn = [[
        InlineKeyboardButton('ᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ', callback_data=f'changecaption#{grp_id}'),
        InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ ᴄᴀᴘᴛɪᴏɴ', callback_data=f'removecaption#{grp_id}', style=enums.ButtonStyle.DANGER),  # type: ignore
    ],[
        InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'grp_pm#{grp_id}')
    ]]

    text = (
        "<b>ᴀᴅᴠᴀɴᴄᴇ ꜱᴇᴛᴛɪɴɢꜱ ᴍᴏᴅᴇ 📳\n\n"
        "ʏᴏᴜ ᴄᴀɴ ᴄᴜꜱᴛᴏᴍɪᴢᴇᴅ ᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ᴠᴀʟᴜᴇꜱ ꜰʀᴏᴍ ʜᴇʀᴇ ✅\n"
        "ᴄʜᴏᴏꜱᴇ ꜰʀᴏᴍ ʙᴇʟᴏᴡ 👇\n\n"
        f"📂 ᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ : {caption_text}</b>"
    )
    try:
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^removelog'))
async def remove_log(client, query):
    _, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.", show_alert=True)
    await delete_group_setting(int(grp_id), 'log')
    await query.answer("ʟᴏɢ ᴄʜᴀɴɴᴇʟ ʀᴇᴍᴏᴠᴇᴅ!", show_alert=True)
    await handle_log_channel_menu(client, query)

@Client.on_callback_query(filters.regex(r'^set_fsub_ui'))
async def set_fsub_ui(client, query):
    await query.answer()
    _, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.", show_alert=True)

    m = await query.message.reply("<b>ꜱᴇɴᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ ᴛᴏ ꜱᴇᴛ ᴀꜱ ꜰꜱᴜʙ ᴄʜᴀɴɴᴇʟ (ᴇx: -100xxxxxxx) ᴏʀ <code>/cancel</code></b>")

    try:
        msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id)
        if not msg.text:
            await m.delete()
            await query.message.reply("<b>⚠️ ᴇʀʀᴏʀ: ᴘʟᴇᴀꜱᴇ ꜱᴇɴᴅ ᴛᴇxᴛ ᴏɴʟʏ.</b>")
            return
        if msg.text == "/cancel":
            await m.delete()
            await handle_forcesub_menu(client, query)
            return

        try:
            channel_id = int(msg.text)
        except ValueError:
             await m.delete()
             await query.message.reply('<b>ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴇ ɪᴅ ɪꜱ ᴀɴ ɪɴᴛᴇɢᴇʀ.</b>')
             return

        try:
            chat = await client.get_chat(channel_id)
        except Exception as e:
            await m.delete()
            return await query.message.reply(f"<b><code>{channel_id}</code> ɪꜱ ɪɴᴠᴀʟɪᴅ. ᴍᴀᴋᴇ ꜱᴜʀᴇ ʙᴏᴛ ɪꜱ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ</b>")

        if chat.type != enums.ChatType.CHANNEL:
            await m.delete()
            return await query.message.reply(f"<b><code>{channel_id}</code> ᴛʜɪꜱ ɪꜱ ɴᴏᴛ ᴄʜᴀɴɴᴇʟ.</b>")

        settings = await get_settings(int(grp_id))
        current_fsub = settings.get('fsub_id', [])
        if not isinstance(current_fsub, list):
             if current_fsub:
                 current_fsub = [current_fsub]
             else:
                 current_fsub = []
        if channel_id not in current_fsub:
            current_fsub.append(channel_id)

        await save_group_settings(int(grp_id), 'fsub_id', current_fsub)
        await m.delete()
        await msg.delete()

        btn = [[InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'fsub_setgs#{grp_id}')]]
        try:
            await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇᴛ ꜰᴏʀᴄᴇ ꜱᴜʙ ᴄʜᴀɴɴᴇʟ ꜰᴏʀ ɢʀᴏᴜᴘ\n\nᴄʜᴀɴɴᴇʟ ɴᴀᴍᴇ - {chat.title}\nɪᴅ - <code>{channel_id}</code></b>", reply_markup=InlineKeyboardMarkup(btn))
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇᴛ ꜰᴏʀᴄᴇ ꜱᴜʙ ᴄʜᴀɴɴᴇʟ ꜰᴏʀ ɢʀᴏᴜᴘ\n\nᴄʜᴀɴɴᴇʟ ɴᴀᴍᴇ - {chat.title}\nɪᴅ - <code>{channel_id}</code></b>", reply_markup=InlineKeyboardMarkup(btn))
        except MessageNotModified:
            pass
    except Exception as e:
        logger.error(e)
        await query.message.reply(f"ᴇʀʀᴏʀ: {e}")

@Client.on_callback_query(filters.regex(r'^remove_fsub_ui'))
async def remove_fsub_ui(client, query):
     _, grp_id = query.data.split("#")
     user_id = query.from_user.id if query.from_user else None
     if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.", show_alert=True)
     await delete_group_setting(int(grp_id), 'fsub_id')
     await query.answer("ꜰᴏʀᴄᴇ ꜱᴜʙ ʀᴇᴍᴏᴠᴇᴅ!", show_alert=True)
     await handle_forcesub_menu(client, query)

@Client.on_callback_query(filters.regex(r'^changelog'))
async def change_log(client, query):
    await query.answer()
    grp_id = query.data.split("#")[1]
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
    chat = await client.get_chat(int(grp_id))
    invite_link = await get_invite_link(client, grp_id)
    settings = await get_settings(int(grp_id))
    log_channel_id = settings.get(f'log')
    log_display = f"<code>{log_channel_id}</code>" if log_channel_id else "ɴᴏᴛ ꜱᴇᴛ"
    try:
        await query.message.edit(f'<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ ʟᴏɢ ᴄʜᴀɴɴᴇʟ.\n\nʟᴏɢ ᴄʜᴀɴɴᴇʟ: {log_display}.<b>')
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f'<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ ʟᴏɢ ᴄʜᴀɴɴᴇʟ.\n\nʟᴏɢ ᴄʜᴀɴɴᴇʟ: {log_display}.<b>')
    except MessageNotModified:
        pass

    m = await query.message.reply("<b>ꜱᴇɴᴅ ɴᴇᴡ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ɪᴅ ( ᴇxᴀᴍᴘʟᴇ: -100123569303) ᴏʀ ᴜꜱᴇ <code>/cancel</code> ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇꜱꜱ</b>")
    while True:
        log_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id)
        if log_msg.text == "/cancel":
            await m.delete()
            await handle_log_channel_menu(client, query)
            return
        if log_msg.text.startswith("-100") and log_msg.text[4:].isdigit() and len(log_msg.text) >= 10:
            try:
                int(log_msg.text)
                break
            except ValueError:
                await query.message.reply("<b>ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ! ᴍᴜꜱᴛ ʙᴇ ᴀ ɴᴜᴍʙᴇʀ ꜱᴛᴀʀᴛɪɴɢ ᴡɪᴛʜ -100 (ᴇxᴀᴍᴘʟᴇ: -100123456789)</b>")
        else:
            await query.message.reply("<b>ɪɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ɪᴅ! ᴍᴜꜱᴛ ʙᴇ ᴀ ɴᴜᴍʙᴇʀ ꜱᴛᴀʀᴛɪɴɢ ᴡɪᴛʜ -100 (ᴇxᴀᴍᴘʟᴇ: -100123456789)</b>")
    try:
        await m.delete()
        await log_msg.delete()
    except Exception:
        pass
    await save_group_settings(int(grp_id), f'log', int(log_msg.text))
    try: 
        await client.send_message(LOG_CHANNEL, f"#Set_Log_Channel\n\nɢʀᴏᴜᴘ ɴᴀᴍᴇ : {chat.title}\n\nɢʀᴏᴜᴘ ɪᴅ: {grp_id}\nɪɴᴠɪᴛᴇ ʟɪɴᴋ : {invite_link}\n\nᴜᴘᴅᴀᴛᴇᴅ ʙʏ : {query.from_user.username}")
    except Exception as e:
        logger.error(e)
    btn = [
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'log_setgs#{grp_id}')]
    ]
    try:
        await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ᴠᴀʟᴜᴇ ✅\nʟᴏɢ ᴄʜᴀɴɴᴇʟ: <code>{log_msg.text}</code></b>", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ᴠᴀʟᴜᴇ ✅\nʟᴏɢ ᴄʜᴀɴɴᴇʟ: <code>{log_msg.text}</code></b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^removecaption'))
async def remove_caption(client, query):
    _, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.", show_alert=True)
    await delete_group_setting(int(grp_id), 'caption')
    await query.answer("ᴄᴀᴘᴛɪᴏɴ ʀᴇᴍᴏᴠᴇᴅ!", show_alert=True)

    # Redirect back to caption settings
    await handle_custom_caption_menu(client, query)

@Client.on_callback_query(filters.regex(r'^changecaption'))
async def change_caption(client, query):
    await query.answer()
    grp_id = query.data.split("#")[1]
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
    chat = await client.get_chat(int(grp_id))
    invite_link = await get_invite_link(client, grp_id)
    title = chat.title
    settings = await get_settings(int(grp_id))
    current_caption = settings.get(f'caption')
    caption_text = f"<code>{current_caption}</code>" if current_caption else "ɴᴏᴛ ꜱᴇᴛ"

    try:
        await query.message.edit(f'<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ ᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ.\n\nᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ: {caption_text}.</b>')
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f'<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ ᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ.\n\nᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ: {caption_text}.</b>')
    except MessageNotModified:
        pass

    m = await query.message.reply("<b>ꜱᴇɴᴅ ɴᴇᴡ ᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ\n\nᴄᴀᴘᴛɪᴏɴ ꜰᴏʀᴍᴀᴛ:\nꜰɪʟᴇ ɴᴀᴍᴇ -<code>{file_name}</code>\nꜰɪʟᴇ ᴄᴀᴘᴛɪᴏɴ - <code>{file_caption}</code>\n<code>ꜰɪʟᴇ ꜱɪᴢᴇ - {file_size}</code>\n\nᴏʀ ᴜꜱᴇ <code>/cancel</code> ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇꜱꜱ</b>")
    caption_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id)
    if caption_msg.text == "/cancel":
        await m.delete()
        await handle_custom_caption_menu(client, query)
        return
    await m.delete()
    await caption_msg.delete()
    await save_group_settings(int(grp_id), f'caption', caption_msg.text)
    try: 
        await client.send_message(LOG_CHANNEL, f"#Set_Caption\n\nɢʀᴏᴜᴘ ɴᴀᴍᴇ : {title}\n\nɢʀᴏᴜᴘ ɪᴅ: {grp_id}\nɪɴᴠɪᴛᴇ ʟɪɴᴋ : {invite_link}\n\nᴜᴘᴅᴀᴛᴇᴅ ʙʏ : {query.from_user.username}")
    except Exception as e:
        logger.error(e)
    btn = [
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'caption_setgs#{grp_id}')]
    ]
    try:
        await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ᴠᴀʟᴜᴇꜱ ✅\n\nᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ: <code>{caption_msg.text}</code></b>", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ ᴠᴀʟᴜᴇꜱ ✅\n\nᴄᴜꜱᴛᴏᴍ ᴄᴀᴘᴛɪᴏɴ: <code>{caption_msg.text}</code></b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^toggleverify'))
async def toggle_verify(client, query):
    _, set_type, status, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
    new_status = not (status == "True")
    await save_group_settings(int(grp_id), set_type, new_status)
    await query.answer("ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ꜱᴛᴀᴛᴜꜱ ᴄʜᴀɴɢᴇᴅ ✅")

    # Reload verification settings menu
    await handle_verification_menu(client, query)

@Client.on_callback_query(filters.regex(r'^changeshortner'))
async def change_shortener(client, query):
    _, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
    btn = [
        [InlineKeyboardButton('ꜱʜᴏʀᴛɴᴇʀ 1', callback_data=f'shortner_menu#1#{grp_id}')],
        [InlineKeyboardButton('ꜱʜᴏʀᴛɴᴇʀ 2', callback_data=f'shortner_menu#2#{grp_id}')],
        [InlineKeyboardButton('ꜱʜᴏʀᴛɴᴇʀ 3', callback_data=f'shortner_menu#3#{grp_id}')],
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'verification_setgs#{grp_id}')]
    ]
    try:
        await query.message.edit("<b>ᴄʜᴏᴏꜱᴇ ꜱʜᴏʀᴛɴᴇʀ ᴛᴏ ᴍᴀɴᴀɢᴇ:</b>", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit("<b>ᴄʜᴏᴏꜱᴇ ꜱʜᴏʀᴛɴᴇʀ ᴛᴏ ᴍᴀɴᴀɢᴇ:</b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^shortner_menu'))
async def shortener_menu_handler(client, query):
    _, num, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)

    settings = await get_settings(int(grp_id))
    suffix = "" if num == "1" else f"_{'two' if num == '2' else 'three'}"
    current_url = settings.get(f'shortner{suffix}')
    current_api = settings.get(f'api{suffix}')

    text = f"<b>ꜱʜᴏʀᴛᴇɴᴇʀ {num} ꜱᴇᴛᴛɪɴɢꜱ:</b>\n\n🌐 ᴅᴏᴍᴀɪɴ: {current_url or 'ɴᴏᴛ ꜱᴇᴛ'}\n🔗 ᴀᴘɪ: {current_api or 'ɴᴏᴛ ꜱᴇᴛ'}"

    set_text = "ꜱᴇᴛ"

    btn = [
        [InlineKeyboardButton(set_text, callback_data=f'set_verify{num}#{grp_id}')],
        [InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ', callback_data=f'rm_verify{num}#{grp_id}')],
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'changeshortner#{grp_id}')]
    ]
    try:
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(text, reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^rm_verify'))
async def remove_shortener(client, query):
    shortner_num = query.data.split("#")[0][-1]
    grp_id = query.data.split("#")[1]
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.", show_alert=True)
    suffix = "" if shortner_num == "1" else f"_{'two' if shortner_num == '2' else 'three'}"
    await delete_group_setting(int(grp_id), f'shortner{suffix}')
    await delete_group_setting(int(grp_id), f'api{suffix}')
    await query.answer(f"ꜱʜᴏʀᴛᴇɴᴇʀ {shortner_num} ʀᴇᴍᴏᴠᴇᴅ!", show_alert=True)
    query.data = f'shortner_menu#{shortner_num}#{grp_id}'
    await shortener_menu_handler(client, query)

@Client.on_callback_query(filters.regex(r'^set_verify'))
async def set_shortener(client, query):
    await query.answer()
    shortner_num = query.data.split("#")[0][-1]
    grp_id = query.data.split("#")[1]
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
    chat = await client.get_chat(int(grp_id))
    invite_link = await get_invite_link(client, grp_id)
    settings = await get_settings(int(grp_id))
    suffix = "" if shortner_num == "1" else f"_{'two' if shortner_num == '2' else 'three'}"
    current_url = settings.get(f'shortner{suffix}', "ʏᴏᴜ ᴅɪᴅɴ'ᴛ ꜱᴇᴛ ᴀɴᴅ ᴠᴀʟᴜᴇ ꜱᴏ ᴜꜱɪɴɢ ᴅᴇꜰᴀᴜʟᴛ ᴠᴀʟᴜᴇꜱ")
    current_api = settings.get(f'api{suffix}', "ʏᴏᴜ ᴅɪᴅɴ'ᴛ ꜱᴇᴛ ᴀɴᴅ ᴠᴀʟᴜᴇ ꜱᴏ ᴜꜱɪɴɢ ᴅᴇꜰᴀᴜʟᴛ ᴠᴀʟᴜᴇꜱ")

    # Set query.data for back handling
    query.data = f'shortner_menu#{shortner_num}#{grp_id}'

    try:
        await query.message.edit(f"<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ ꜱʜᴏʀᴛɴᴇʀ {shortner_num}:\n🌐 ᴡᴇʙꜱɪᴛᴇ: <code>{current_url}</code>\n🔗 ᴀᴘɪ: <code>{current_api}</code></b>")
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ ꜱʜᴏʀᴛɴᴇʀ {shortner_num}:\n🌐 ᴡᴇʙꜱɪᴛᴇ: <code>{current_url}</code>\n🔗 ᴀᴘɪ: <code>{current_api}</code></b>")
    except MessageNotModified:
        pass

    m = await query.message.reply("<b>ꜱᴇɴᴅ ɴᴇᴡ ꜱʜᴏʀᴛɴᴇʀ ᴡᴇʙꜱɪᴛᴇ ᴏʀ ᴜꜱᴇ <code>/cancel</code> ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇꜱꜱ</b>")
    url_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id)
    if url_msg.text == "/cancel":
        await m.delete()
        await shortener_menu_handler(client, query)
        return
    await m.delete()
    await url_msg.delete()
    n = await query.message.reply("<b>ɴᴏᴡ ꜱᴇɴᴅ ꜱʜᴏʀᴛɴᴇʀ ᴀᴘɪ ᴏʀ ᴜꜱᴇ <code>/cancel</code> ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇꜱꜱ</b>")
    key_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id)
    if key_msg.text == "/cancel":
        await n.delete()
        await shortener_menu_handler(client, query)
        return
    await n.delete()
    await key_msg.delete()
    await save_group_settings(int(grp_id), f'shortner{suffix}', url_msg.text)
    await save_group_settings(int(grp_id), f'api{suffix}', key_msg.text)
    log_message = f"#New_Shortner_Set\n\n ꜱʜᴏʀᴛɴᴇʀ ɴᴏ - {shortner_num}\nɢʀᴏᴜᴘ ʟɪɴᴋ - `{invite_link}`\n\nɢʀᴏᴜᴘ ɪᴅ : `{grp_id}`\nᴀᴅᴅᴇᴅ ʙʏ - `{user_id}`\nꜱʜᴏʀᴛɴᴇʀ ꜱɪᴛᴇ - {url_msg.text}\nꜱʜᴏʀᴛɴᴇʀ ᴀᴘɪ - `{key_msg.text}`"
    try: 
        await client.send_message(LOG_CHANNEL, log_message, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as e:
        logger.error(e)

    btn = [
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'shortner_menu#{shortner_num}#{grp_id}')]
    ]
    try:
        await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ꜱʜᴏʀᴛɴᴇʀ {shortner_num} ᴠᴀʟᴜᴇꜱ ✅\n\nᴡᴇʙꜱɪᴛᴇ: <code>{url_msg.text}</code>\nᴀᴘɪ: <code>{key_msg.text}</code></b>", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ꜱʜᴏʀᴛɴᴇʀ {shortner_num} ᴠᴀʟᴜᴇꜱ ✅\n\nᴡᴇʙꜱɪᴛᴇ: <code>{url_msg.text}</code>\nᴀᴘɪ: <code>{key_msg.text}</code></b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^changetime'))
async def change_time(client, query):
    _, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
    btn = [
        [InlineKeyboardButton('ᴛɪᴍᴇ 1', callback_data=f'time_menu#1#{grp_id}')],
        [InlineKeyboardButton('ᴛɪᴍᴇ 2', callback_data=f'time_menu#2#{grp_id}')],
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'verification_setgs#{grp_id}')]
    ]
    try:
        await query.message.edit("<b>ᴄʜᴏᴏꜱᴇ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ ᴛᴏ ᴍᴀɴᴀɢᴇ:</b>", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit("<b>ᴄʜᴏᴏꜱᴇ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ ᴛᴏ ᴍᴀɴᴀɢᴇ:</b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^time_menu'))
async def time_menu_handler(client, query):
    _, num, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)

    settings = await get_settings(int(grp_id))
    # Mapping: 1->verify_time (old 2nd), 2->third_verify_time (old 3rd)
    if num == "1":
        key = "verify_time"
    elif num == "2":
        key = "third_verify_time"
    else:
        return await query.answer("Invalid Time Selection")

    val = settings.get(key)
    set_text = "ꜱᴇᴛ"

    btn = [
        [InlineKeyboardButton(set_text, callback_data=f'set_time{num}#{grp_id}')],
        [InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ', callback_data=f'rm_time{num}#{grp_id}')],
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'changetime#{grp_id}')]
    ]
    try:
        await query.message.edit(f"<b>⏰ Time {num} Settings:</b>\n\n⏱️ Value: {val or 'Not Set'}", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>⏰ Time {num} Settings:</b>\n\n⏱️ Value: {val or 'Not Set'}", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^rm_time'))
async def remove_time(client, query):
    time_num = query.data.split("#")[0][-1]
    grp_id = query.data.split("#")[1]
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.", show_alert=True)

    if time_num == "1":
        key = "verify_time"
    elif time_num == "2":
        key = "third_verify_time"
    else:
        return await query.answer("Invalid Time Selection")

    await delete_group_setting(int(grp_id), key)
    await query.answer(f"ᴛɪᴍᴇ {time_num} ʀᴇᴍᴏᴠᴇᴅ!", show_alert=True)

    query.data = f'time_menu#{time_num}#{grp_id}'
    await time_menu_handler(client, query)

@Client.on_callback_query(filters.regex(r'^set_time'))
async def set_time(client, query):
    await query.answer()
    time_num = query.data.split("#")[0][-1]
    grp_id = query.data.split("#")[1]
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
    chat = await client.get_chat(int(grp_id))
    invite_link = await get_invite_link(client, grp_id)

    settings = await get_settings(int(grp_id))
    if time_num == "1":
        key = "verify_time"
    elif time_num == "2":
        key = "third_verify_time"
    else:
        return await query.answer("Invalid Time Selection")

    current_time = settings.get(key, 'Not set')
    query.data = f'time_menu#{time_num}#{grp_id}'

    try:
        await query.message.edit(f"<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ {time_num} ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ:\n\n⏱️ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ: {current_time}</b>")
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ {time_num} ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ:\n\n⏱️ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ: {current_time}</b>")
    except MessageNotModified:
        pass

    m = await query.message.reply("<b>ꜱᴇɴᴅ ɴᴇᴡ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ (ɪɴ sᴇᴄᴏɴᴅs) ᴏʀ ᴜꜱᴇ <code>/cancel</code> ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇꜱꜱ.</b>")
    while True:
        time_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id)
        if time_msg.text == "/cancel":
            await m.delete()
            await time_menu_handler(client, query)
            return
        if time_msg.text.isdigit() and int(time_msg.text) > 0:
            break
        else:
            await query.message.reply("<b>ɪɴᴠᴀʟɪᴅ ᴛɪᴍᴇ! ᴍᴜꜱᴛ ʙᴇ ᴀ ᴘᴏꜱɪᴛɪᴠᴇ ɴᴜᴍʙᴇʀ (ᴇxᴀᴍᴘʟᴇ: 60)</b>")
    await m.delete()
    await time_msg.delete()
    await save_group_settings(int(grp_id), key, int(time_msg.text))
    log_message = f"#New_Time_Set\n\n ᴛɪᴍᴇ ɴᴏ - {time_num}\nɢʀᴏᴜᴘ ʟɪɴᴋ - `{invite_link}`\n\nɢʀᴏᴜᴘ ɪᴅ : `{grp_id}`\nᴀᴅᴅᴇᴅ ʙʏ - `{user_id}`\nᴛɪᴍᴇ - {time_msg.text}"
    try:
        await client.send_message(LOG_CHANNEL, log_message, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as e:
        logger.error(e)

    btn = [
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'time_menu#{time_num}#{grp_id}')]
    ]
    try:
        await query.message.edit(f"<b>{time_num} ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ ᴜᴘᴅᴀᴛᴇ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅\n\nᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ: {time_msg.text}</b>", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>{time_num} ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ ᴜᴘᴅᴀᴛᴇ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅\n\nᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ: {time_msg.text}</b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^changetutorial'))
async def change_tutorial(client, query):
    _, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
    btn = [
        [InlineKeyboardButton('ᴛᴜᴛᴏʀɪᴀʟ 1', callback_data=f'tutorial_menu#1#{grp_id}')],
        [InlineKeyboardButton('ᴛᴜᴛᴏʀɪᴀʟ 2', callback_data=f'tutorial_menu#2#{grp_id}')],
        [InlineKeyboardButton('ᴛᴜᴛᴏʀɪᴀʟ 3', callback_data=f'tutorial_menu#3#{grp_id}')],
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'verification_setgs#{grp_id}')]
    ]
    try:
        await query.message.edit("<b>ᴄʜᴏᴏꜱᴇ ᴛᴜᴛᴏʀɪᴀʟ ᴛᴏ ᴍᴀɴᴀɢᴇ:</b>", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit("<b>ᴄʜᴏᴏꜱᴇ ᴛᴜᴛᴏʀɪᴀʟ ᴛᴏ ᴍᴀɴᴀɢᴇ:</b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^tutorial_menu'))
async def tutorial_menu_handler(client, query):
    _, num, grp_id = query.data.split("#")
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)

    settings = await get_settings(int(grp_id))
    suffix = "" if num == "1" else f"_{'2' if num == '2' else '3'}"
    val = settings.get(f'tutorial{suffix}')
    set_text = "ꜱᴇᴛ"

    btn = [
        [InlineKeyboardButton(set_text, callback_data=f'set_tutorial{num}#{grp_id}')],
        [InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ', callback_data=f'rm_tutorial{num}#{grp_id}')],
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'changetutorial#{grp_id}')]
    ]
    try:
        await query.message.edit(f"<b>📹 Tutorial {num} Settings:</b>\n\n🔗 Value: {val or 'Not Set'}", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>📹 Tutorial {num} Settings:</b>\n\n🔗 Value: {val or 'Not Set'}", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r'^rm_tutorial'))
async def remove_tutorial(client, query):
    tutorial_num = query.data.split("#")[0][-1]
    grp_id = query.data.split("#")[1]
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.", show_alert=True)

    suffix = "" if tutorial_num == "1" else f"_{'2' if tutorial_num == '2' else '3'}"
    await delete_group_setting(int(grp_id), f'tutorial{suffix}')
    await query.answer(f"ᴛᴜᴛᴏʀɪᴀʟ {tutorial_num} ʀᴇᴍᴏᴠᴇᴅ!", show_alert=True)
    query.data = f'tutorial_menu#{tutorial_num}#{grp_id}'
    await tutorial_menu_handler(client, query)

@Client.on_callback_query(filters.regex(r'^set_tutorial'))
async def set_tutorial(client, query):
    await query.answer()
    tutorial_num = query.data.split("#")[0][-1]
    grp_id = query.data.split("#")[1]
    user_id = query.from_user.id if query.from_user else None
    if not await is_check_admin(client, int(grp_id), user_id):
        return await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
    chat = await client.get_chat(int(grp_id))
    invite_link = await get_invite_link(client, grp_id)
    settings = await get_settings(int(grp_id))
    suffix = "" if tutorial_num == "1" else f"_{'2' if tutorial_num == '2' else '3'}"
    tutorial_url = settings.get(f'tutorial{suffix}', "ʏᴏᴜ ᴅɪᴅɴ'ᴛ ꜱᴇᴛ ᴀɴᴅ ᴠᴀʟᴜᴇ ꜱᴏ ᴜꜱɪɴɢ ᴅᴇꜰᴀᴜʟᴛ ᴠᴀʟᴜᴇꜱ")
    query.data = f'tutorial_menu#{tutorial_num}#{grp_id}'

    try:
        await query.message.edit(f"<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ ᴛᴜᴛᴏʀɪᴀʟ {tutorial_num}:\n\n🔗 ᴛᴜᴛᴏʀɪᴀʟ ᴜʀʟ: {tutorial_url}.</b>")
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>📌 ᴅᴇᴛᴀɪʟꜱ ᴏꜰ ᴛᴜᴛᴏʀɪᴀʟ {tutorial_num}:\n\n🔗 ᴛᴜᴛᴏʀɪᴀʟ ᴜʀʟ: {tutorial_url}.</b>")
    except MessageNotModified:
        pass

    m = await query.message.reply("<b>ꜱᴇɴᴅ ɴᴇᴡ ᴛᴜᴛᴏʀɪᴀʟ ᴜʀʟ ᴏʀ ᴜꜱᴇ <code>/cancel</code> ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜᴇ ᴘʀᴏᴄᴇꜱꜱ</b>")
    tutorial_msg = await client.listen(chat_id=query.message.chat.id, user_id=user_id)
    if tutorial_msg.text == "/cancel":
        await m.delete()
        await tutorial_menu_handler(client, query)
        return
    await m.delete()
    await tutorial_msg.delete()
    await save_group_settings(int(grp_id), f'tutorial{suffix}', tutorial_msg.text)
    log_message = f"#New_Tutorial_Set\n\n ᴛᴜᴛᴏʀɪᴀʟ ɴᴏ - {tutorial_num}\nɢʀᴏᴜᴘ ʟɪɴᴋ - `{invite_link}`\n\nɢʀᴏᴜᴘ ɪᴅ : `{grp_id}`\nᴀᴅᴅᴇᴅ ʙʏ - `{user_id}`\nᴛᴜᴛᴏʀɪᴀʟ - {tutorial_msg.text}"
    try:
        await client.send_message(LOG_CHANNEL, log_message, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as e:
        logger.error(e)

    btn = [
        [InlineKeyboardButton('⇋ ʙᴀᴄᴋ ⇋', callback_data=f'tutorial_menu#{tutorial_num}#{grp_id}')]
    ]
    try:
        await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴜᴛᴏʀɪᴀʟ {tutorial_num} ᴠᴀʟᴜᴇꜱ ✅\n\nᴛᴜᴛᴏʀɪᴀʟ ᴜʀʟ: {tutorial_msg.text}</b>", reply_markup=InlineKeyboardMarkup(btn))
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        await query.message.edit(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ᴛᴜᴛᴏʀɪᴀʟ {tutorial_num} ᴠᴀʟᴜᴇꜱ ✅\n\nᴛᴜᴛᴏʀɪᴀʟ ᴜʀʟ: {tutorial_msg.text}</b>", reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r"^delete_group_check"))
async def prompt_group_deletion(client, query):
    try:
        _, grp_id = query.data.split("#")
        userid = query.from_user.id
        if not await is_check_admin(client, int(grp_id), userid):
            await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
            return

        buttons = [
            [
                InlineKeyboardButton('ʏᴇs, ᴅᴇʟᴇᴛᴇ', callback_data=f'delete_group#{grp_id}', style=enums.ButtonStyle.DANGER),  # type: ignore
                InlineKeyboardButton('ᴄᴀɴᴄᴇʟ', callback_data=f'open_settings#{grp_id}')
            ]
        ]
        await query.message.edit_text(
            "<b>⚠️ ᴀʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛʜɪs ɢʀᴏᴜᴘ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ? ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴀʟsᴏ ʟᴇᴀᴠᴇ ᴛʜᴇ ɢʀᴏᴜᴘ.</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
    except Exception as e:
        logger.error(f"Callback Error - {e}")
        await query.answer("An error occurred!", show_alert=True)

@Client.on_callback_query(filters.regex(r"^delete_group#"))
async def process_group_deletion(client, query):
    try:
        try:
            _, grp_id = query.data.split("#")
        except ValueError:
            return
        userid = query.from_user.id
        if not await is_check_admin(client, int(grp_id), userid):
            await query.answer("<b>ɴᴇᴇᴅ ᴛᴏ ʙᴇ ᴀᴅᴍɪɴ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ✅.</b>", show_alert=True)
            return
        await db.delete_chat(int(grp_id))
        await query.answer("ɢʀᴏᴜᴘ ᴅᴇʟᴇᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅", show_alert=True)
        await query.message.edit_text("<b>✅ ɢʀᴏᴜᴘ ᴅᴇʟᴇᴛᴇᴅ ꜰʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ ᴀɴᴅ ʙᴏᴛ ʟᴇꜰᴛ ᴛʜᴇ ɢʀᴏᴜᴘ.</b>")
        try:
            await client.leave_chat(int(grp_id))
        except Exception as e:
            logger.error(f"Error leaving group {grp_id}: {e}")
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
    except Exception as e:
        logger.error(f"Callback Error - {e}")
        await query.answer("An error occurred!", show_alert=True)


