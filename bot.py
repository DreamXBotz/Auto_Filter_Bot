import plugins.monkey_patch  # noqa: F401
import logging
import logging.config
from pyrogram import idle, __version__
from pyrogram.raw.all import layer
import time
from pyrogram.errors import FloodWait
import asyncio
from datetime import date, datetime
from pathlib import Path
import pytz
from aiohttp import web
from database.ia_filterdb import Media, Media2
from database.users_chats_db import db
from info import MULTIPLE_DB, ON_HEROKU, LOG_STR, LOG_CHANNEL, PORT
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

botStartTime = time.time()

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
    dreamxbotz.username = bot_info.username
    await initialize_clients()
    plugins_names = get_plugins_names()
    if plugins_names:
        plugins_list = "\n".join(f"  {i}. {name}" for i, name in enumerate(plugins_names, 1))
        logger.info("Plugins Found (%d):\n%s", len(plugins_names), plugins_list)
    else:
        logger.warning("No plugins found.")

    if ON_HEROKU:
        asyncio.create_task(ping_server())
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats
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
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    current_time = now.strftime("%I:%M:%S %p")
    await dreamxbotz.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(temp.B_LINK, today, current_time))
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