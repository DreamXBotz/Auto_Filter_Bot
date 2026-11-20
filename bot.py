import plugins.listener  # noqa: F401
import logging
import logging.config
from pyrogram import idle, __version__
from pyrogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from pyrogram.raw.all import layer
import time
from pyrogram.errors import FloodWait
import asyncio
from datetime import date, datetime
from pathlib import Path
from aiohttp import web
from database.ia_filterdb import Media, Media2
from database.users_chats_db import db
from info import MULTIPLE_DB, ON_HEROKU, LOG_STR, LOG_CHANNEL, PORT, TIMEZONE, TZ, ADMINS
from utils import temp
from Script import script
from plugins import web_server, check_expired_premium, keep_alive
from dreamxbotz.Bot import dreamxbotz
from dreamxbotz.util.keepalive import ping_server
from dreamxbotz.Bot.clients import initialize_clients
from PIL import Image

Image.MAX_IMAGE_PIXELS = 500_000_000

logger = logging.getLogger(__name__)
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)
logging.getLogger("pymongo").setLevel(logging.WARNING)

try:
    import uvloop
    uvloop.install()
    logger.info("uvloop installed as event-loop policy.")
except ImportError:
    pass

botStartTime = time.time()

from pyrogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

# Commands visible to every regular user.
USER_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("id", "Show your Telegram ID"),
    BotCommand("info", "Show Telegram account information"),
    BotCommand("movies", "Browse the latest movie uploads"),
    BotCommand("series", "Browse the latest series uploads"),
    BotCommand("request", "Request a movie or series"),
    BotCommand("top_search", "Show popular searches"),
    BotCommand("trendlist", "Show today's trending searches"),
    BotCommand("plan", "View premium plans and free trial"),
    BotCommand("myplan", "Check your premium subscription"),
]

# Extra commands visible only to users listed in ADMINS.
OWNER_COMMANDS = USER_COMMANDS + [
    BotCommand("logs", "Send the bot log file"),
    BotCommand("save", "Save a file to the database"),
    BotCommand("delete", "Delete a file from the database"),
    BotCommand("deleteall", "Delete all indexed files"),
    BotCommand("settings", "Open group settings"),
    BotCommand("reload", "Connect or reload a group"),
    BotCommand("set_template", "Set the group file caption template"),
    BotCommand("send", "Send a stored file to a user"),
    BotCommand("deletefiles", "Delete indexed files"),
    BotCommand("pm_search", "Enable or disable private search"),
    BotCommand("movie_update", "Toggle movie update notifications"),
    BotCommand("restart", "Restart the bot"),
    BotCommand("del_msg", "Delete bot messages"),
    BotCommand("set_caption", "Set the group's file caption"),
    BotCommand("set_tutorial", "Set the first verification tutorial"),
    BotCommand("set_tutorial_2", "Set the second verification tutorial"),
    BotCommand("set_tutorial_3", "Set the third verification tutorial"),
    BotCommand("set_shortner", "Set the first URL shortener"),
    BotCommand("set_shortner_2", "Set the second URL shortener"),
    BotCommand("set_shortner_3", "Set the third URL shortener"),
    BotCommand("set_log_channel", "Set the group's log channel"),
    BotCommand("set_time", "Set the first verification timer"),
    BotCommand("set_time_2", "Set the second verification timer"),
    BotCommand("details", "Show group or bot details"),
    BotCommand("verify", "Manage user verification"),
    BotCommand("set_fsub", "Set the force-subscription channel"),
    BotCommand("resetallgroup", "Reset all connected groups"),
    BotCommand("trial_reset", "Reset a user's free trial"),
    BotCommand("remove_fsub", "Remove force subscription"),
    BotCommand("clean_groups", "Clean inactive connected groups"),
    BotCommand("broadcast", "Broadcast a message to users"),
    BotCommand("grp_broadcast", "Broadcast a message to groups"),
    BotCommand("clear_junk", "Clear junk user records"),
    BotCommand("junk_group", "Show or clear junk groups"),
    BotCommand("clear_junk_group", "Clear junk group records"),
    BotCommand("remove_premium", "Remove a user's premium access"),
    BotCommand("get_premium", "Check a user's premium status"),
    BotCommand("add_premium", "Give premium access to a user"),
    BotCommand("premium_users", "List premium users"),
    BotCommand("maintenance", "Open the maintenance controls"),
    BotCommand("banned", "Manage banned users and chats"),
    BotCommand("setskip", "Set the indexing skip number"),
    BotCommand("delreq", "Delete stored join requests"),
]

async def setup_command_menus(client):
    """Publish separate Telegram command menus for regular users and owners."""
    await client.set_bot_commands(
        USER_COMMANDS,
        scope=BotCommandScopeDefault()
    )

    for admin in ADMINS:
        try:
            try:
                admin_id = int(admin)
            except (TypeError, ValueError):
                admin_user = await client.get_users(admin)
                admin_id = admin_user.id

            await client.set_bot_commands(
                OWNER_COMMANDS,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
            logger.info("Owner command menu configured for %s", admin_id)
        except Exception as e:
            logger.warning("Could not configure owner command menu for %s: %s", admin, e)


def get_plugins_names(plugins_dir="plugins"):
    plugins_path = Path(plugins_dir)
    if not plugins_path.exists():
        logger.warning("Plugins directory not found: %s", plugins_path)
        return []

    return [
        ".".join(file.relative_to(plugins_path).with_suffix("").parts)
        for file in sorted(plugins_path.rglob("*.py"))
        if file.name != "__init__.py"
    ]

async def dreamxbotz_start():
    logger.info('\n\nInitializing DreamxBotz')
    dreamxbotz.loop = asyncio.get_running_loop()
    await dreamxbotz.start()
    bot_info = await dreamxbotz.get_me()
    await setup_command_menus(dreamxbotz)
    dreamxbotz.username = bot_info.username
    await initialize_clients()
    plugins_names = get_plugins_names()
    if plugins_names:
        logger.info("Plugins Loaded: %d plugins found.", len(plugins_names))
    else:
        logger.warning("No plugins found.")

    if ON_HEROKU:
        asyncio.create_task(ping_server())
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = set(b_users)
    temp.BANNED_CHATS = set(b_chats)
    await Media.ensure_indexes()
    if MULTIPLE_DB:
        await Media2.ensure_indexes()
        logger.info("Multiple Database Mode On. Now Files Will Be Save In Second DB If First DB Is Full")
    else:
        logger.info("Single DB Mode On ! Files Will Be Save In First Database")
    
    me = bot_info
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention
    dreamxbotz.username = '@' + me.username
    asyncio.create_task(check_expired_premium(dreamxbotz))
    
    logger.info(f"{me.first_name} with Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
    logger.info(LOG_STR)
    logger.info(script.LOGO)
    today = date.today()
    now = datetime.now(TZ)
    current_time = now.strftime("%I:%M:%S %p")
    await dreamxbotz.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(temp.B_LINK, today, current_time, TIMEZONE))
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()
    asyncio.create_task(keep_alive())

    try:
        await idle()
    finally:
        await app.cleanup()
        await dreamxbotz.stop()

if __name__ == '__main__':
    try:
        logger.info('Service started...')
        asyncio.run(dreamxbotz_start())
    except FloodWait as e:
        logger.info(f"FloodWait! Sleeping for {e.value} seconds then restarting...")
        time.sleep(e.value)
        asyncio.run(dreamxbotz_start())
    except KeyboardInterrupt:
        logger.info('Service stopped. Bye.')