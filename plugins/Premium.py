import logging
import re

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery

from info import PREMIUM_LOGS


logger = logging.getLogger(__name__)

DONATION_AMOUNTS = (10, 25, 50, 100)
DONATION_PAYLOAD_RE = re.compile(r"movieflix_donation_(10|25|50|100)")


@Client.on_callback_query(filters.regex(r"^donate_(10|25|50|100)$"))
async def donation_stars_invoice(client, callback_query: CallbackQuery):
    """Create a voluntary Telegram Stars donation invoice."""
    try:
        amount = int(callback_query.data.rsplit("_", 1)[1])
        if amount not in DONATION_AMOUNTS:
            await callback_query.answer("Invalid donation amount.", show_alert=True)
            return

        await client.send_invoice(
            chat_id=callback_query.message.chat.id,
            title="Support MovieFlix",
            description=f"Voluntary donation of {amount} Telegram Stars to support MovieFlix.",
            payload=f"movieflix_donation_{amount}",
            currency="XTR",
            prices=[LabeledPrice(label="MovieFlix donation", amount=amount)],
        )
        await callback_query.answer("Your Stars donation invoice is ready.")
    except Exception:
        logger.exception("Could not create Telegram Stars donation invoice")
        await callback_query.answer(
            "Unable to create the donation invoice. Please try again.",
            show_alert=True,
        )


@Client.on_pre_checkout_query()
async def pre_checkout_handler(client, query: PreCheckoutQuery):
    """Approve only valid voluntary donations paid in Telegram Stars."""
    try:
        payload = query.payload or ""
        match = DONATION_PAYLOAD_RE.fullmatch(payload)
        if (
            match
            and query.currency == "XTR"
            and query.total_amount == int(match.group(1))
        ):
            await query.answer(ok=True)
        else:
            await query.answer(
                ok=False,
                error_message="This is not a valid Telegram Stars donation.",
            )
    except Exception:
        logger.exception("Donation pre-checkout validation failed")
        await query.answer(
            ok=False,
            error_message="Unable to validate this donation. Please try again.",
        )


@Client.on_message(filters.successful_payment)
async def successful_donation_payment(client, message):
    """Acknowledge and log donations; payments never grant premium access."""
    payment = message.successful_payment
    payload = payment.invoice_payload or ""
    match = DONATION_PAYLOAD_RE.fullmatch(payload)

    if not match:
        logger.warning(
            "Ignoring unrecognized successful payment payload for user_id=%s",
            message.from_user.id if message.from_user else "unknown",
        )
        return

    expected_amount = int(match.group(1))
    amount = int(payment.total_amount)
    user_id = message.from_user.id if message.from_user else 0

    if payment.currency != "XTR" or amount != expected_amount:
        logger.error(
            "Donation payment mismatch: expected=%s received=%s currency=%s user_id=%s",
            expected_amount,
            amount,
            payment.currency,
            user_id,
        )
        await message.reply_text(
            "⚠️ We could not verify this donation. Please contact support."
        )
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
            f"🧾 Charge ID: <code>{payment.telegram_payment_charge_id}</code>",
        )
    except Exception:
        logger.exception("Could not send donation log for user_id=%s", user_id)
