import asyncio
import logging
import re
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
    LinkPreviewOptions
)
from pyrogram.errors import MessageNotModified, MessageTooLong
from plugins.Dreamxfutures.Imdbposter import get_movie_detailsx
from info import ADMINS, MOVIE_UPDATE_CHANNEL, ABOVE_PREVIEW
from utils import temp

#code is created by @bharath_boy for public use so atleast don't remove credits
logger = logging.getLogger(__name__)

post_sessions = {}

USE_GETFILE_BUTTON_BY_DEFAULT = True
DEFAULT_WATERMARK = "Join [ᴅʀᴇᴀᴍxʙᴏᴛᴢ](https://t.me/dreamxbotz)"
LANGUAGES_FORMAT = "➥ <b>Languages :</b> <code>{langs}</code>"
RESOLUTIONS_FORMAT = "\n➥ <b>Qualities :</b> <code>{resolutions}</code>"
OTT_FORMAT = "\n➥ <b>Available on :</b> <code>{otts}</code>"

TEMPLATES = {
    "classic_emoji": """<b>{title} ({year})</b>
⭐️ <b>Rating:</b> {rating}/10
🎭 <b>Genre:</b> {genres}
💬 <b>Plot:</b> {plot}""",
    "minimalist": """🎬 <b>{title}</b>
🗓 <b>Year:</b> {year}
🌟 <b>Rating:</b> {rating}""",
    "sparkle_header": """✨ <b>{title}</b> ✨

<b>🗓 Year:</b> {year} | <b>⭐️ Rating:</b> {rating}/10
<b>🎭 Genres:</b> {genres}

<i>{plot}</i>""",
    "markdown_style": """🎥 **{title}** ({year})

- **Rating**: {rating} / 10 🌟
- **Genres**: {genres}

**Plot Summary**:
{plot}""",
    "divider_list": """🎬 <b>{title} {year}</b>
━━━━━━━━━━━━━━━━━━
➥ <b>Rating :</b> <code>★ {rating}/10</code>
➥ <b>Genres :</b> <code>{genres}</code>
""",

    "dashed_box": """- - - - - - - - - - - - - - - - - -
🎥 <b>{title}</b>
- - - - - - - - - - - - - - - - - -

➛ <b>Year ∥</b> {year}
➛ <b>Rating ∥</b> {rating}/10
➛ <b>Genres ∥</b> {genres}

<b><u>Synopsis</u></b>
<i>{plot}</i>""",
    "chevron_details": """<b>{title}</b>

» <b>Year ➣</b> {year}
» <b>Rating ➣</b> ★ {rating}/10
» <b>Genres ➣</b> {genres}

<b>∥ PLOT ∥</b>
└─ <i>{plot}</i>""",
    "bullet_points": """✨ <b><u>{title} ({year})</u></b> ✨

● <b>Rating :</b> {rating}/10
● <b>Genres :</b> {genres}

<b>💬 Plot Summary ➥</b>
<i>{plot}</i>""",
    "clean_grid": """🎬 {title} ({year})

🗓️ <b>Year ∥</b> {year}
⭐️ <b>Rating ∥</b> {rating}/10
🎭 <b>Genres ∥</b> {genres}

➣ <i>{plot}</i>"""
}
LANGUAGES = [
    
    "Bengali", "English", "Gujarati", "Hindi", "Kannada", "Malayalam",
    "Marathi", "Punjabi", "Tamil", "Telugu", "Urdu",
    
    "Arabic", "French", "German", "Italian", "Japanese", "Korean",
    "Mandarin", "Portuguese", "Russian", "Spanish"
]
RESOLUTIONS = [
    
    "144p", "240p", "480p", "720p", "1080p", "1440p", "2160p", "4320p",
    
    "BluRay", "BDRip", "WEB-DL", "VOD", "WEBRip", "HDTV",
    "DVDRip", "DVDScr", "TS", "CAM",
    
    "AV1", "HEVC", "x264"
]

OTT_PLATFORMS = [
    
    "Aha",
    "ALTBalaji",
    "JioHotstar",
    "Eros Now",
    "Hoichoi",
    "JioCinema",
    "MX Player",
    "SonyLIV",
    "Sun NXT",
    "Voot",
    "Zee5",

    
    "Amazon Prime Video",  
    "Apple TV+",
    "Crunchyroll",
    "Discovery+",
    "HBO Max",
    "Hulu",
    "Netflix",
    "Paramount+",
    "Peacock",
    "YouTube Premium"
]


@Client.on_message(filters.command("post") & filters.user(ADMINS), group=-4)
async def post_command(client: Client, message: Message):
    if len(message.command) == 1:
        return await message.reply_text("Please provide a movie name. Usage: `/post The Dark Knight`")

    movie_name = " ".join(message.command[1:])
    user_id = message.from_user.id
    logger.info(f"User {user_id} initiated post for '{movie_name}'")

    await start_post_session(client, message, user_id, movie_name)

#code is created by @bharath_boy for public use so atleast don't remove credits
async def start_post_session(client: Client, message: Message, user_id: int, movie_name: str):
    movie_details = await get_movie_detailsx(movie_name)
    if not movie_details:
        return await message.reply_text("Could not fetch details for the movie.")

    logger.info(f"User {user_id} is starting post session for '{movie_name}'.")

    if user_id in post_sessions and post_sessions[user_id].get("last_preview_message_id"):
        try:
            await client.delete_messages(message.chat.id, post_sessions[user_id]["last_preview_message_id"])
        except Exception:
            pass

    post_sessions[user_id] = {
        "movie_name": movie_name, "caption": None, "buttons": [],
        "photo_mode": False,
        "use_landscape": True if movie_details.get("backdrop_url") else False,
        "custom_languages": [], "custom_resolutions": [], "custom_otts": [],
        "last_preview_message_id": None, "original_message_id": message.id,
        "custom_poster": None,
        "watermark": DEFAULT_WATERMARK,
        "lang_format": LANGUAGES_FORMAT,
        "ott_format": OTT_FORMAT,
        "res_format": RESOLUTIONS_FORMAT, "active_template": "divider_list",
        "movie_details": movie_details
    }

    if USE_GETFILE_BUTTON_BY_DEFAULT:
        title = movie_details.get("title", "movie")
        year = movie_details.get("year", "")
        movie_year = f"{title} {year}".strip()
        movie_year = re.sub(r"[ *:\.]", "-", movie_year)
        url = f"https://telegram.me/{temp.U_NAME}?start=getfile-{movie_year}"
        post_sessions[user_id]["buttons"].append(
            [InlineKeyboardButton("📥 Get Files 📥", url=url)])
        logger.info(f"Default 'Get Files' button added for session {user_id}")

    await update_post_preview(client, user_id, message.chat.id, force_resend=True)


async def _build_final_post_content(session: dict, session_id: int):
    movie_details = session["movie_details"]
    if not movie_details:
        return None, None, None

    if not session.get("caption"):
        raw_genres = movie_details.get("genres") or []
        genres_str = raw_genres if isinstance(raw_genres, str) else ", ".join(raw_genres)
        session["caption"] = TEMPLATES[session["active_template"]].format(
            title=movie_details.get("title", "N/A"), year=movie_details.get("year", "N/A"),
            rating=movie_details.get("rating", "N/A"),
            genres=genres_str,
            plot=movie_details.get("plot", "N/A"),
        )

    final_caption = session["caption"]
    if session.get("custom_languages"):
        final_caption += session["lang_format"].format(
            langs=', '.join(session['custom_languages']))
    if session.get("custom_resolutions"):
        final_caption += session["res_format"].format(
            resolutions=', '.join(session['custom_resolutions']))
    if session.get("custom_otts"):
        final_caption += session["ott_format"].format(
            otts=', '.join(session['custom_otts']))
    if session.get("watermark"):
        final_caption += f"\n\n{session['watermark']}"

    keyboard = build_keyboard(session, session_id)
    poster_to_use = session.get("custom_poster") or \
        (movie_details.get("backdrop_url") if session.get(
            "use_landscape") else movie_details.get("poster_url"))

    return final_caption, keyboard, poster_to_use

#code is created by @bharath_boy for public use so atleast don't remove credits
async def update_post_preview(client: Client, session_id: int, chat_id: int, force_resend: bool = False):
    session = post_sessions.get(session_id)
    if not session:
        return

    is_new = not session.get("last_preview_message_id")

    if is_new or force_resend:
        if not is_new:
            try:
                await client.delete_messages(chat_id, session["last_preview_message_id"])
            except Exception:
                pass
        status_msg = await client.send_message(
            chat_id, "<i>Fetching details...</i>",
            reply_to_message_id=session["original_message_id"]
        )
        session["last_preview_message_id"] = status_msg.id

    final_caption, keyboard, poster_to_use = await _build_final_post_content(session, session_id)

    if not final_caption:
        return await client.edit_message_text(chat_id, session["last_preview_message_id"], "Could not find details for this movie.")

    try:
        if session["photo_mode"] and poster_to_use:
            if force_resend:
                await client.delete_messages(chat_id, session["last_preview_message_id"])
                sent_message = await client.send_photo(chat_id, photo=poster_to_use, caption=final_caption, reply_markup=keyboard, reply_to_message_id=session["original_message_id"])
                session["last_preview_message_id"] = sent_message.id
            else:
                await client.edit_message_caption(chat_id, session["last_preview_message_id"], caption=final_caption, reply_markup=keyboard)
        else:
            text_content = f"<a href='{poster_to_use}'>&#8205;</a>{final_caption}" if poster_to_use else final_caption
            await client.edit_message_text(chat_id, session["last_preview_message_id"], text_content, reply_markup=keyboard, link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=ABOVE_PREVIEW))
    except MessageNotModified:
        pass
    except Exception as e:
        logger.error(f"Error updating preview: {e}", exc_info=True)


def build_keyboard(session: dict, session_id: int):
    rows = []
    if session.get("buttons"):
        rows.extend(session["buttons"])

    rows.extend([
        [InlineKeyboardButton("✏️ Buttons", callback_data=f"post:buttons_menu:{session_id}"),
         InlineKeyboardButton("✏️ Caption", callback_data=f"post:edit_caption:{session_id}")],
        [InlineKeyboardButton("🖼️ Poster", callback_data=f"post:set_poster:{session_id}"),
         InlineKeyboardButton(
             "✨ Templates", callback_data=f"post:templates:{session_id}"),
         InlineKeyboardButton("💧 Watermark", callback_data=f"post:set_watermark:{session_id}")],
        [InlineKeyboardButton("🗣️ Languages", callback_data=f"post:languages:{session_id}"),
         InlineKeyboardButton(
             "📺 Qualities", callback_data=f"post:resolutions:{session_id}"),
         InlineKeyboardButton("🌐 OTT", callback_data=f"post:otts:{session_id}")],  
        [InlineKeyboardButton(f"Mode: {'Photo' if session['photo_mode'] else 'Text'}", callback_data=f"post:toggle_preview:{session_id}"),
         InlineKeyboardButton(f"Poster: {'Landscape' if session['use_landscape'] else 'Portrait'}", callback_data=f"post:toggle_poster:{session_id}")],
        [InlineKeyboardButton("✅ Post", callback_data=f"post:finalize:{session_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"post:cancel:{session_id}")]
    ])
    return InlineKeyboardMarkup(rows)

#code is created by @bharath_boy for public use so atleast don't remove credits
@Client.on_callback_query(filters.regex(r"^post:"), group=-4)
async def post_callbacks(client: Client, query: CallbackQuery):
    data_parts = query.data.split(":")
    action = data_parts[1]
    session_id = int(data_parts[2])
    extra_data = data_parts[3:]

    if query.from_user.id != session_id:
        return await query.answer("This is not for you!", show_alert=True)

    session = post_sessions.get(session_id)
    if not session:
        await query.answer("Session expired or was cancelled.", show_alert=True)
        return await query.message.delete()

    force_resend = False

    if action == "back":
        await query.answer()

    elif action in ["languages", "resolutions", "templates", "buttons_menu", "remove_buttons_menu", "otts"]:  
        await query.answer()
        if action == "languages":
            await show_selection_menu(query, session_id, "languages")
        elif action == "resolutions":
            await show_selection_menu(query, session_id, "resolutions")
        elif action == "otts":
            
            await show_selection_menu(query, session_id, "otts")
        elif action == "templates":
            await handle_templates_menu(query, session)
        elif action == "buttons_menu":
            await handle_buttons_menu(query, session_id)
        elif action == "remove_buttons_menu":
            await handle_remove_buttons_menu(query, session)
        return

    elif action in ["select_lang", "select_res", "select_ott"]:  
        await query.answer()
        item = extra_data[0]
        if action == "select_lang":
            if item not in session["custom_languages"]:
                session["custom_languages"].append(item)
            else:
                session["custom_languages"].remove(item)
            await show_selection_menu(query, session_id, "languages")
        elif action == "select_res":
            if item not in session["custom_resolutions"]:
                session["custom_resolutions"].append(item)
            else:
                session["custom_resolutions"].remove(item)
            await show_selection_menu(query, session_id, "resolutions")
        elif action == "select_ott":  
            if item not in session["custom_otts"]:
                session["custom_otts"].append(item)
            else:
                session["custom_otts"].remove(item)
            await show_selection_menu(query, session_id, "otts")
        return

    else:
        
        if action == "edit_buttons":
            await handle_edit_buttons(client, query, session)
        elif action == "add_get_files":
            await handle_add_get_files(session)
            await query.answer("✅ 'Get Files' button added!")
        elif action == "edit_caption":
            await handle_edit_caption(client, query, session)
        elif action == "set_poster":
            force_resend = await handle_set_poster(client, query, session)
        elif action == "remove_button":
            await handle_remove_button(session, extra_data)
            await handle_remove_buttons_menu(query, session)
            return
        elif action == "select_template":
            await handle_select_template(session, extra_data[0])
        elif action == "toggle_preview":
            force_resend = await handle_toggle_preview(query, session)
        elif action == "toggle_poster":
            force_resend = await handle_toggle_poster(session)
        elif action == "set_watermark":
            await handle_set_watermark(client, query, session)
        elif action == "format_lang":
            await handle_format_lang(client, query, session)
        elif action == "format_res":
            await handle_format_res(client, query, session)
        elif action == "format_ott":
            
            await handle_format_ott(client, query, session)
        elif action == "finalize":
            return await finalize_and_post(client, query, session_id)
        elif action == "cancel":
            return await handle_cancel(client, query, session_id)

    await update_post_preview(client, session_id, query.message.chat.id, force_resend)

#code is created by @bharath_boy for public use so atleast don't remove credits
async def show_selection_menu(query: CallbackQuery, session_id: int, menu_type: str):
    session = post_sessions[session_id]

    
    if menu_type == "languages":
        items, selected, action_prefix, format_action = (
            LANGUAGES, session["custom_languages"], "select_lang", "format_lang")
    elif menu_type == "resolutions":
        items, selected, action_prefix, format_action = (
            RESOLUTIONS, session["custom_resolutions"], "select_res", "format_res")
    elif menu_type == "otts":
        items, selected, action_prefix, format_action = (
            OTT_PLATFORMS, session["custom_otts"], "select_ott", "format_ott")
    else:
        return

    buttons = [InlineKeyboardButton(
        f"✅ {i}" if i in selected else i, callback_data=f"post:{action_prefix}:{session_id}:{i}") for i in items]
    keyboard = [buttons[i:i+3]
                for i in range(0, len(buttons), 3)]  
    keyboard.append([InlineKeyboardButton("⚙️ Change Format",
                    callback_data=f"post:{format_action}:{session_id}")])
    keyboard.append([InlineKeyboardButton(
        "✅ Done", callback_data=f"post:back:{session_id}")])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))


async def get_user_input(client, query, session, prompt_text):
    ask_msg = await client.send_message(chat_id=query.message.chat.id, text=prompt_text, reply_to_message_id=session.get("original_message_id"))
    try:
        response = await client.listen(chat_id=query.message.chat.id, user_id=query.from_user.id, timeout=300)
        await ask_msg.delete()
        if response:
            await response.delete()
            return response
    except asyncio.TimeoutError:
        await ask_msg.edit("Timeout (5 minutes). The operation was cancelled.")
        await asyncio.sleep(5)
        await ask_msg.delete()
    return None


async def handle_buttons_menu(query, session_id):
    buttons = [
        [InlineKeyboardButton(
            "➕ Add/Edit Layout", callback_data=f"post:edit_buttons:{session_id}")],
        [InlineKeyboardButton("📥 Add 'Get Files' Button",
                              callback_data=f"post:add_get_files:{session_id}")],
        [InlineKeyboardButton(
            "🗑️ Remove a Button", callback_data=f"post:remove_buttons_menu:{session_id}")],
        [InlineKeyboardButton("Back", callback_data=f"post:back:{session_id}")]
    ]
    await query.edit_message_reply_markup(InlineKeyboardMarkup(buttons))


async def handle_edit_buttons(client: Client, query: CallbackQuery, session: dict):
    response = await get_user_input(client, query, session, "Send the button layout. Format:\n`Button 1 - URL1 | Button 2 - URL2` (for same row)\n`Button 3 - URL3` (for new row)")
    if response and response.text:
        new_layout = []
        for row_str in response.text.strip().split('\n'):
            row_btns = [InlineKeyboardButton(text.strip(), url=url.strip()) for btn_str in row_str.split(
                '|') if ' - ' in btn_str for text, url in [btn_str.split(' - ', 1)]]
            if row_btns:
                new_layout.append(row_btns)
        session["buttons"] = new_layout

#code is created by @bharath_boy for public use so atleast don't remove credits
async def handle_add_get_files(session):
    movie_details = session["movie_details"]
    if movie_details:
        title = movie_details.get("title", "movie")
        year = movie_details.get("year", "")
        movie_year = f"{title} {year}".strip()
        url = f"https://telegram.me/{temp.U_NAME}?start=getfile-{movie_year.replace(' ', '-')}"
        session["buttons"].append(
            [InlineKeyboardButton("📥 Get Files 📥", url=url)])


async def handle_edit_caption(client: Client, query: CallbackQuery, session: dict):
    response = await get_user_input(client, query, session, "Send the new caption text.")
    if response and response.text:
        session["caption"] = response.text


async def handle_set_poster(client: Client, query: CallbackQuery, session: dict):
    response = await get_user_input(client, query, session, "Send a photo or an image URL. Send `/reset` to use the default poster.")
    if response:
        if response.photo:
            session["custom_poster"] = response.photo.file_id
            if not session["photo_mode"]:
                session["photo_mode"] = True
                await query.answer("Switched to Photo mode as you uploaded an image.", show_alert=True)
        elif response.text and response.text.startswith("http"):
            session["custom_poster"] = response.text
        elif response.text and response.text == "/reset":
            session["custom_poster"] = None
    return True


async def handle_set_watermark(client, query, session):
    prompt_text = (
        "Send the watermark text. Markdown is supported.\n\n"
        "• Send `/reset` to remove the watermark.\n"
        "• Send `/default` to use the default watermark."
    )
    response = await get_user_input(client, query, session, prompt_text)
    if response and response.text:
        if response.text == "/reset":
            session["watermark"] = ""
        elif response.text == "/default":
            session["watermark"] = DEFAULT_WATERMARK
        else:
            session["watermark"] = response.text

#code is created by @bharath_boy for public use so atleast don't remove credits
async def handle_format_lang(client, query, session):
    response = await get_user_input(client, query, session, "Send the format for languages. Use `{langs}` as a placeholder. Send `/reset` for default.\n\n Current: " + session["lang_format"])
    if response and response.text:
        session["lang_format"] = LANGUAGES_FORMAT if response.text == "/reset" else response.text


async def handle_format_res(client, query, session):
    response = await get_user_input(client, query, session, "Send the format for qualities. Use `{resolutions}` as a placeholder. Send `/reset` for default.\n\n Current: " + session["res_format"])
    if response and response.text:
        session["res_format"] = RESOLUTIONS_FORMAT if response.text == "/reset" else response.text




async def handle_format_ott(client, query, session):
    response = await get_user_input(client, query, session, "Send the format for OTT. Use `{otts}` as a placeholder. Send `/reset` for default.\n\n Current: " + session["ott_format"])
    if response and response.text:
        session["ott_format"] = OTT_FORMAT if response.text == "/reset" else response.text


async def handle_templates_menu(query, session):
    buttons = []
    for name in TEMPLATES:
        text = f"✅ {name}" if session.get("active_template") == name else name
        buttons.append([InlineKeyboardButton(
            text, callback_data=f"post:select_template:{query.from_user.id}:{name}")])
    buttons.append([InlineKeyboardButton(
        "Back", callback_data=f"post:back:{query.from_user.id}")])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(buttons))


async def handle_select_template(session, template_name):
    session["active_template"] = template_name
    session["caption"] = None

#code is created by @bharath_boy for public use so atleast don't remove credits
async def handle_remove_buttons_menu(query, session):
    buttons = []
    for i, row in enumerate(session["buttons"]):
        for j, btn in enumerate(row):
            buttons.append([InlineKeyboardButton(
                f"❌ {btn.text}", callback_data=f"post:remove_button:{query.from_user.id}:{i}:{j}")])
    if not buttons:
        buttons.append([InlineKeyboardButton(
            "No buttons to remove", callback_data="noop")])
    buttons.append([InlineKeyboardButton(
        "Back", callback_data=f"post:back:{query.from_user.id}")])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(buttons))


async def handle_remove_button(session, extra_data):
    try:
        row_i, col_i = int(extra_data[0]), int(extra_data[1])
        session["buttons"][row_i].pop(col_i)
        if not session["buttons"][row_i]:
            session["buttons"].pop(row_i)
    except (IndexError, ValueError):
        logger.warning("Tried to remove a button that does not exist.")


async def handle_toggle_preview(query: CallbackQuery, session: dict):
    if session.get("custom_poster") and not session["custom_poster"].startswith("http"):
        await query.answer("Cannot switch to Text mode with an uploaded photo.", show_alert=True)
        return False
    session["photo_mode"] = not session["photo_mode"]
    return True


async def handle_toggle_poster(session):
    session["use_landscape"] = not session["use_landscape"]
    return True


async def handle_cancel(client: Client, query: CallbackQuery, session_id: int, _=None):
    if session := post_sessions.pop(session_id, None):
        if session.get("last_preview_message_id"):
            await client.delete_messages(query.message.chat.id, session["last_preview_message_id"])
    target_msg = query.message.reply_to_message or query.message
    await target_msg.reply_text("Post creation cancelled.")


async def finalize_and_post(client: Client, query: CallbackQuery, session_id: int, _=None):
    session = post_sessions.pop(session_id, None)
    if not session:
        logger.warning(
            f"Finalize called for an expired or invalid session_id: {session_id}")
        return

    await client.delete_messages(query.message.chat.id, session["last_preview_message_id"])
    target_msg = query.message.reply_to_message or query.message
    status_msg = await target_msg.reply_text("<i>Finalizing and posting...</i>")

    final_caption, _, poster_to_use = await _build_final_post_content(session, session_id)
    final_keyboard = InlineKeyboardMarkup(
        session["buttons"]) if session["buttons"] else None

    if not final_caption:
        logger.error(
            f"Failed to fetch movie details for '{session['movie_name']}' during finalization.")
        return await status_msg.edit("Could not fetch movie details to post. Aborting.")

    mode = "Photo" if session["photo_mode"] and poster_to_use else "Text"
    try:
        if mode == "Photo":
            await client.send_photo(
                chat_id=MOVIE_UPDATE_CHANNEL, photo=poster_to_use,
                caption=final_caption, reply_markup=final_keyboard
            )
        else:
            text_content = f"<a href='{poster_to_use}'>&#8205;</a>{final_caption}" if poster_to_use else final_caption
            await client.send_message(
                chat_id=MOVIE_UPDATE_CHANNEL, text=text_content,
                reply_markup=final_keyboard, link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=ABOVE_PREVIEW)
            )

        await status_msg.edit("✅ Post has been sent to the update channel.")
        logger.info(
            f"Successfully posted '{session['movie_name']}' to the update channel.")

    except MessageTooLong:
        error_text = "<b>Post Failed</b>\n\nThe final caption is too long for a Telegram message (limit is 4096 characters). Please shorten the plot or other text and try again."
        await status_msg.edit(error_text)
        logger.error(
            f"Failed to post '{session['movie_name']}': MessageTooLong error.", exc_info=True)
    except Exception as e:
        error_text = f"Failed to post to update channel.\n<b>Error:</b> <code>{e}</code>"
        await status_msg.edit(error_text)
        logger.error(
            f"An unexpected error occurred while posting '{session['movie_name']}':", exc_info=True)

