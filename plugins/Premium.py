from pyrogram import enums

import logging
import datetime
from Script import script 
from info import ADMINS, PREMIUM_LOGS, STAR_PREMIUM_PLANS, SUBSCRIPTION, TZ
from utils import get_seconds, temp
from database.users_chats_db import db 
import asyncio
from pyrogram import Client, filters 
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong
from pyrogram.types import (
    LinkPreviewOptions,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    PreCheckoutQuery
)

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("remove_premium") & filters.user(ADMINS))
async def remove_premium(client, message):
    if len(message.command) == 2:
        user_id = int(message.command[1])
        user = await client.get_users(user_id)
        if await db.remove_premium_access(user_id):
            await message.reply_text("ᴜꜱᴇʀ ʀᴇᴍᴏᴠᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ !")
            await client.send_message(
                chat_id=user_id,
                text=script.PREMIUM_END_TEXT.format(user.mention)
            )
        else:
            await message.reply_text("ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴜꜱᴇʀ !\nᴀʀᴇ ʏᴏᴜ ꜱᴜʀᴇ, ɪᴛ ᴡᴀꜱ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ɪᴅ ?")
    else:
        await message.reply_text("ᴜꜱᴀɢᴇ : /remove_premium user_id") 


@Client.on_message(filters.command("myplan"))
async def myplan(client, message):
    await message.reply_text("MovieFlix is free. We do not offer paid subscriptions.")

@Client.on_message(filters.command("get_premium") & filters.user(ADMINS))
async def get_premium(client, message):
    if len(message.command) == 2:
        user_id = int(message.command[1])
        user = await client.get_users(user_id)
        data = await db.get_user(user_id)  
        if data and data.get("expiry_time"):
            expiry = data.get("expiry_time") 
            expiry_ist = expiry.astimezone(TZ)
            expiry_str_in_ist = expiry_ist.strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")            
            current_time = datetime.datetime.now(TZ)
            time_left = expiry_ist - current_time
            days = time_left.days
            if days < 0:
                time_left_str = "Expired"
            else:
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
            await message.reply_text(f"⚜️ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :\n\n👤 ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}")
        else:
            await message.reply_text("ɴᴏ ᴘʀᴇᴍɪᴜᴍ ᴅᴀᴛᴀ ᴏꜰ ᴛʜɪꜱ ᴜꜱᴇʀ ᴡᴀꜱ ꜰᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀꜱᴇ !")
    else:
        await message.reply_text("ᴜꜱᴀɢᴇ : /get_premium user_id")

@Client.on_message(filters.command("add_premium") & filters.user(ADMINS))
async def give_premium_cmd_handler(client, message):
    if len(message.command) == 4:
        time_zone = datetime.datetime.now(TZ)
        current_time = time_zone.strftime("%d-%m-%Y\n⏱️ ᴊᴏɪɴɪɴɢ ᴛɪᴍᴇ : %I:%M:%S %p") 
        user_id = int(message.command[1])  
        user = await client.get_users(user_id)
        time = message.command[2]+" "+message.command[3]
        seconds = await get_seconds(time)
        if seconds > 0:
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
            user_data = {"id": user_id, "expiry_time": expiry_time}  
            await db.update_user(user_data) 
            data = await db.get_user(user_id)
            expiry = data.get("expiry_time")   
            expiry_str_in_ist = expiry.astimezone(TZ).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")         
            await message.reply_text(f"ᴘʀᴇᴍɪᴜᴍ ᴀᴅᴅᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅\n\n👤 ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n\n⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}", link_preview_options=LinkPreviewOptions(is_disabled=True))
            await client.send_message(
                chat_id=user_id,
                text=f"👋 ʜᴇʏ {user.mention},\nᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴘᴜʀᴄʜᴀꜱɪɴɢ ᴘʀᴇᴍɪᴜᴍ.\nᴇɴᴊᴏʏ !! ✨🎉\n\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}", link_preview_options=LinkPreviewOptions(is_disabled=True)              
            )    
            await client.send_message(PREMIUM_LOGS, text=f"#Added_Premium\n\n👤 ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n\n⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}", link_preview_options=LinkPreviewOptions(is_disabled=True))
                    
        else:
            await message.reply_text(
                "❌ ɪɴᴠᴀʟɪᴅ ᴛɪᴍᴇ ꜰᴏʀᴍᴀᴛ ❗\n"
                "🕒 ᴘʟᴇᴀsᴇ ᴜsᴇ: <code>1 day</code>, <code>1 hour</code>, <code>1 min</code>, <code>1 month</code>, or <code>1 year</code>"
            )
    else:
        await message.reply_text(
            "📌 ᴜsᴀɢᴇ: <code>/add_premium user_id time</code>\n"
            "📅 ᴇxᴀᴍᴘʟᴇ: <code>/add_premium 123456 1 month</code>\n"
            "🧭 ᴀᴄᴄᴇᴘᴛᴇᴅ ꜰᴏʀᴍᴀᴛs: <code>1 day</code>, <code>1 hour</code>, <code>1 min</code>, <code>1 month</code>, <code>1 year</code>"
            )

@Client.on_message(filters.command("premium_users") & filters.user(ADMINS))
async def premium_user(client, message):
    aa = await message.reply_text("<i>ꜰᴇᴛᴄʜɪɴɢ...</i>")
    new = " ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ ʟɪꜱᴛ :\n\n"
    user_count = 1
    users = await db.get_all_premium_user_data()
    async for data in users:
        expiry = data.get("expiry_time")
        if not expiry:
            continue
        expiry_ist = expiry.astimezone(TZ)
        expiry_str_in_ist = expiry_ist.strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")            
        current_time = datetime.datetime.now(TZ)
        time_left = expiry_ist - current_time
        days = time_left.days
        if days < 0:
            time_left_str = "Expired"
        else:
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
        
        try:
            user_obj = await client.get_users(data['id'])
            mention = user_obj.mention
        except Exception:
            mention = f"<a href='tg://user?id={data['id']}'>User</a>"
            
        new += f"{user_count}. {mention}\n👤 ᴜꜱᴇʀ ɪᴅ : {data['id']}\n⏳ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n"
        user_count += 1
    try:    
        await aa.edit_text(new)
    except MessageTooLong:
        with open('usersplan.txt', 'w+') as outfile:
            outfile.write(new)
        await message.reply_document('usersplan.txt', caption="Paid Users:")


@Client.on_message(filters.command("plan"))
async def plan(client, message):
    await message.reply_text("MovieFlix is free. We do not offer paid subscriptions.")


# Voluntary Telegram Stars donations (separate from premium purchases).
@Client.on_callback_query(filters.regex(r"^donate_(10|25|50|100)$"))
async def donation_stars_invoice(client, callback_query: CallbackQuery):
    try:
        amount = int(callback_query.data.split("_", 1)[1])
        await client.send_invoice(
            chat_id=callback_query.message.chat.id,
            title="Support MovieFlix",
            description=f"Voluntary donation of {amount} Telegram Stars to support MovieFlix.",
            payload=f"movieflix_donation_{amount}",
            currency="XTR",
            prices=[LabeledPrice(label="MovieFlix donation", amount=amount)],
        )
        await callback_query.answer("Your Stars invoice is ready.")
    except Exception as e:
        logger.exception("Could not create Telegram Stars donation invoice: %s", e)
        await callback_query.answer("Unable to create the donation invoice. Please try again.", show_alert=True)


# Telegram Star Payment Method 👇
# Credit - @BeingXAnonymous

@Client.on_callback_query(filters.regex(r"buy_\d+"))
async def premium_button(client, callback_query: CallbackQuery):
    try:
        amount = int(callback_query.data.split("_")[1])
        if amount in STAR_PREMIUM_PLANS:
            try:
                buttons = [[
                    InlineKeyboardButton("Pay with Stars ??", pay=True, style=enums.ButtonStyle.PRIMARY)
                ], [
                    InlineKeyboardButton("? Close ?", callback_data="close_data", style=enums.ButtonStyle.DANGER)
                ]]
                reply_markup = InlineKeyboardMarkup(buttons)
                await client.send_invoice(
                    chat_id=callback_query.message.chat.id,
                    title="Premium Subscription",
                    description=f"Pay {amount} Star And Get Premium For {STAR_PREMIUM_PLANS[amount]}",
                    payload=f"dreamxpremium_{amount}",
                    currency="XTR",
                    prices=[
                        LabeledPrice(
                            label="Premium Subscription", 
                            amount=amount
                        ) 
                    ],
                    reply_markup=reply_markup
                )
                await callback_query.answer()
            except Exception as e:
                logger.error("Error sending invoice: %s", e)
                await callback_query.answer("🚫 Error Processing Your Payment. Try again.", show_alert=True)
        else:
            await callback_query.answer("⚠️ Invalid Premium Package.", show_alert=True)
    except Exception as e:
        logger.error("Error In buy_: %s", e)
 
@Client.on_pre_checkout_query()
async def pre_checkout_handler(client, query: PreCheckoutQuery):
    try:
        if query.payload.startswith(("dreamxpremium_", "movieflix_donation_")):
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="⚠️ Invalid Purchase Type.")
    except Exception as e:
        logger.error("Pre-checkout error: %s", e)
        await query.answer(ok=False, error_message="🚫 Unexpected Error Occurred.")

@Client.on_message(filters.successful_payment)
async def successful_premium_payment(client, message):
    try:
        amount = int(message.successful_payment.total_amount)
        user_id = message.from_user.id
        invoice_payload = message.successful_payment.invoice_payload or ""

        if invoice_payload.startswith("movieflix_donation_"):
            expected_amount = int(invoice_payload.rsplit("_", 1)[1])
            if amount != expected_amount:
                logger.error("Donation amount mismatch: expected=%s received=%s user_id=%s", expected_amount, amount, user_id)
                await message.reply_text("⚠️ We could not verify this donation amount. Please contact support.")
                return
            await message.reply_text(
                f"💜 Thank you for supporting MovieFlix with {amount} Telegram Stars!\n\n"
                "Your contribution is voluntary and does not unlock paid features."
            )
            try:
                await client.send_message(
                    PREMIUM_LOGS,
                    f"#MovieFlix_Donation\n\n"
                    f"👤 User: {message.from_user.mention}\n"
                    f"🆔 User ID: <code>{user_id}</code>\n"
                    f"⭐ Donation: {amount} Stars\n"
                    f"🧾 Charge ID: <code>{message.successful_payment.telegram_payment_charge_id}</code>",
                )
            except Exception:
                logger.exception("Could not send donation log for user_id=%s", user_id)
            return

        time_zone = datetime.datetime.now(TZ)
        current_time = time_zone.strftime("%d-%m-%Y | %I:%M:%S %p") 
        if amount in STAR_PREMIUM_PLANS:
            time = STAR_PREMIUM_PLANS[amount]
            seconds = await get_seconds(time)
            if seconds > 0:
                expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
                user_data = {"id": user_id, "expiry_time": expiry_time}
                await db.update_user(user_data)
                data = await db.get_user(user_id)
                expiry = data.get("expiry_time")
                expiry_str_in_ist = expiry.astimezone(TZ).strftime("%d-%m-%Y | %I:%M:%S %p")    
                await message.reply(text=f"Thank you For Purchasing Premium Service Using Star ✅\n\nSubscription Time - {time}\nExpire In - {expiry_str_in_ist}", link_preview_options=LinkPreviewOptions(is_disabled=True))                
                await client.send_message(PREMIUM_LOGS, text=f"#Purchase_Premium_With_Star\n\n👤 ᴜꜱᴇʀ - {message.from_user.mention}\n\n⚡ ᴜꜱᴇʀ ɪᴅ - <code>{user_id}</code>\n\n🚫 ꜱᴛᴀʀ ᴘᴀʏ - {amount}⭐\n\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ - {time}\n\n⌛️ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ - {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ - {expiry_str_in_ist}", link_preview_options=LinkPreviewOptions(is_disabled=True))
            else:
                await message.reply("⚠️ Invalid Premium Time.")
        else:
            await message.reply("⚠️ Invalid Premium Package.")
    except Exception as e:
        logger.error("Error Processing Premium Payment: %s", e)
        await message.reply("✅ Thank You For Your Payment! (Error Logging Details)")


