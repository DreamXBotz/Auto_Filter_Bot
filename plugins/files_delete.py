import re
import logging
from pyrogram import Client, filters
from info import DELETE_CHANNELS
from database.ia_filterdb import (
    unpack_new_file_id, delete_media_by_id, delete_media_matching,
)

logger = logging.getLogger(__name__)
media_filter = filters.document | filters.video | filters.audio


@Client.on_message(filters.chat(DELETE_CHANNELS) & media_filter)
async def deletemultiplemedia(client, message):
    """Delete channel-removed files from MongoDB and Turso."""
    media = next(
        (getattr(message, kind, None) for kind in ("document", "video", "audio")
         if getattr(message, kind, None) is not None),
        None,
    )
    if media is None:
        return

    file_id, _ = unpack_new_file_id(media.file_id)
    deleted = await delete_media_by_id(file_id)
    if not deleted:
        file_name = re.sub(r"([_\-.+])", " ", str(media.file_name))
        deleted = await delete_media_matching(file_name, media.file_size, media.mime_type)
        if not deleted:
            deleted = await delete_media_matching(media.file_name, media.file_size, media.mime_type)

    if deleted:
        logger.info("Successfully deleted %s indexed record(s).", deleted)
    else:
        logger.info("Deleted-channel media was not found in the index.")
