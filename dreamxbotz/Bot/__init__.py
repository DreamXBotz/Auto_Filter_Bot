import logging
import logging.config
from importlib import import_module
from pathlib import Path
from typing import Union, Optional, AsyncGenerator
from pyrogram import Client, types
from pyrogram.handlers import Handler
from info import API_ID, API_HASH, BOT_TOKEN, SESSION

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)


class dreamcinezoneXBot(Client):

    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=60,
            plugins=dict(root= "plugins"),
            sleep_threshold=5,
        )

    def load_plugins(self):
        if not self.plugins or not self.plugins.get("enabled", True):
            return

        root = self.plugins["root"]
        plugin_root = Path(root.replace(".", "/"))
        count = 0

        for path in sorted(plugin_root.rglob("*.py")):
            module_path = ".".join(path.with_suffix("").parts)
            module = import_module(module_path)

            for target in vars(module).values():
                handler_groups = getattr(target, "handlers", None)
                if not isinstance(handler_groups, (list, tuple)):
                    continue

                for handler, group in handler_groups:
                    if isinstance(handler, Handler) and isinstance(group, int):
                        self.add_handler(handler, group)
                        count += 1

        if count:
            logging.info("[%s] Successfully loaded %d plugins from %s", self.name, count, root)
        else:
            logging.warning("[%s] No plugin loaded from %s", self.name, root)

    async def iter_messages(self, chat_id: Union[int, str], limit: int, offset: int = 0,) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1
      
dreamxbotz = dreamcinezoneXBot()

multi_clients = {}
work_loads = {}
