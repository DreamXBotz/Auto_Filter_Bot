import os
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message

IMGBB_API_KEY = "d4cc3d793cb68b2c6cdc2197588e895c"

@Client.on_message(filters.command(["img", "cup", "telegraph"], prefixes="/") & filters.reply)
async def c_upload(client, message: Message):
    reply = message.reply_to_message
    if not reply.media:
        return await message.reply_text("Reply to a media to upload it to Cloud.")
    if reply.document and reply.document.file_size > 5 * 1024 * 1024:  # 5 MB
        return await message.reply_text("File size limit is 5 MB.")
    msg = await message.reply_text("Processing...")
    try:
        downloaded_media = await reply.download()
        if not downloaded_media:
            return await msg.edit_text("Something went wrong during download.")
        with open(downloaded_media, "rb") as f:
            img_bytes = f.read()
        os.remove(downloaded_media)

        data = aiohttp.FormData()
        data.add_field('key', IMGBB_API_KEY)
        data.add_field('image', img_bytes, filename="image.jpg")
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.imgbb.com/1/upload", data=data) as resp:
                status_code = resp.status
                if status_code == 200:
                    result = await resp.json()
        
        if status_code == 200:
            if result.get("success"):
                await msg.edit_text(f"{result['data']['url']}")
            else:
                await msg.edit_text("Something went wrong. Please try again later.")
        else:
            await msg.edit_text("Something went wrong. Please try again later.")

    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")
