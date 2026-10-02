#Thanks @dreamxbotz for helping in this journey 

from info import BIN_CHANNEL, URL
from dreamxbotz.Bot import dreamxbotz
from dreamxbotz.util.human_readable import humanbytes
from dreamxbotz.util.file_properties import get_file_ids
from dreamxbotz.server.exceptions import InvalidHash
import urllib.parse
import logging
import aiohttp

logger = logging.getLogger(__name__)

async def render_page(id, secure_hash, src=None):
    await dreamxbotz.get_messages(int(BIN_CHANNEL), int(id))
    file_data = await get_file_ids(dreamxbotz, int(BIN_CHANNEL), int(id))
    if file_data.unique_id[:6] != secure_hash:
        logger.debug(f"link hash: {secure_hash} - {file_data.unique_id[:6]}")
        logger.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash

    src = urllib.parse.urljoin(
        URL,
        f"{id}/{urllib.parse.quote_plus(file_data.file_name)}?hash={secure_hash}",
    )

    tag = file_data.mime_type.split("/")[0].strip()
    file_size = humanbytes(file_data.file_size)
    if tag in ["video", "audio"]:
        template_file = "dreamxbotz/template/dl.html"
    else:
        template_file = "dreamxbotz/template/dl.html"
        async with aiohttp.ClientSession() as s:
            async with s.get(src) as u:
                file_size = humanbytes(int(u.headers.get("Content-Length")))

    with open(template_file, "r", encoding="utf-8") as f:
        html_raw = f.read()

    file_name = file_data.file_name.replace("_", " ")

    return html_raw.replace("{{file_name}}", file_name) \
                   .replace("{{file_url}}", src) \
                   .replace("{{file_size}}", file_size) \
                   .replace("{{file_unique_id}}", file_data.unique_id) \
                   .replace("{{tutorial}}", "https://youtube.com/")
