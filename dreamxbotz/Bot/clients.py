import asyncio
import logging
from info import API_ID, API_HASH, SLEEP_THRESHOLD, USER_SESSION_STRING, BIN_CHANNEL
from pyrogram import Client
from dreamxbotz.util.config_parser import TokenParser
from . import multi_clients, work_loads, dreamxbotz

logger = logging.getLogger(__name__)

# Optional user session: Telegram bot accounts cannot call messages.GetHistory.
bin_history_client = None

async def initialize_clients():
    global bin_history_client
    multi_clients[0] = dreamxbotz
    if USER_SESSION_STRING:
        try:
            bin_history_client = await Client(
                name="bin_history_user",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=USER_SESSION_STRING,
                in_memory=True,
                no_updates=True,
                sleep_threshold=SLEEP_THRESHOLD
            ).start()
            logger.info("BIN history user session started; it must be a member of BIN_CHANNEL=%s", BIN_CHANNEL)
        except Exception:
            bin_history_client = None
            logger.exception("Could not start BIN history user session. Check USER_SESSION_STRING/API credentials.")
    else:
        logger.warning("USER_SESSION_STRING is not configured; historical BIN scans are disabled.")
    work_loads[0] = 0
    all_tokens = TokenParser().parse_from_env()
    if not all_tokens:
        logger.info("No additional clients found, using default client")
        return
    
    async def start_client(client_id, token):
        try:
            logger.info("Starting - Client %s", client_id)
            if client_id == len(all_tokens):
                await asyncio.sleep(2)
                logger.info("This will take some time, please wait...")
            client = await Client(
                name=str(client_id),
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=token,
                sleep_threshold=SLEEP_THRESHOLD,
                no_updates=True,
                in_memory=True
            ).start()
            work_loads[client_id] = 0
            return client_id, client
        except Exception:
            logger.error(f"Failed starting Client - {client_id} Error:", exc_info=True)
    
    clients = await asyncio.gather(*[start_client(i, token) for i, token in all_tokens.items()])
    multi_clients.update(dict([c for c in clients if c]))
    if len(multi_clients) != 1:
        import info
        info.MULTI_CLIENT = True
        logger.info("Multi-Client Mode Enabled")
    else:
        logger.info("No additional clients were initialized, using default client")
