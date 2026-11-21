import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from typing import Dict, List
from collections import defaultdict
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from utils import get_settings, save_group_settings, LimitedDict
from info import (
    COLLECTION_NAME, COVERX, DATABASE_NAME, DATABASE_URI, DATABASE_URI2,
    INDEX_CAPTION, MAX_B_TN, MULTIPLE_DB, ULTRA_FAST_MODE, USE_CAPTION_FILTER,
    TURSO_ENABLED, MONGO_MAX_SIZE_MB,
)
from database import turso_store
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache


logger = logging.getLogger(__name__)
# ---------------------------------------------------------

# Global cache for DB size
_db_stats_cache = {"timestamp": None, "primary_size": 0.0}

@lru_cache(maxsize=512)
def compile_regex(pattern):
    return re.compile(pattern, re.IGNORECASE)

# Primary DB
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)

# secondary db
if MULTIPLE_DB and DATABASE_URI2:
    client2 = AsyncIOMotorClient(DATABASE_URI2)
    db2 = client2[DATABASE_NAME]
    instance2 = Instance.from_db(db2)
else:
    client2 = client
    db2 = db
    instance2 = instance


@instance.register
class Media(Document):
    file_id = fields.StrField(attribute="_id")
    file_unique_id = fields.StrField(allow_none=True)
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    cover = fields.StrField(allow_none=True)

    class Meta:
        indexes = ("$file_name",)
        collection_name = COLLECTION_NAME


@instance2.register
class Media2(Document):
    file_id = fields.StrField(attribute="_id")
    file_unique_id = fields.StrField(allow_none=True)
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    cover = fields.StrField(allow_none=True)


    class Meta:
        indexes = ("$file_name",)
        collection_name = COLLECTION_NAME


async def check_db_size(db):
    """Return primary MongoDB logical + index size in MiB."""
    try:
        stats = await db.command("dbstats")
        return (float(stats.get("dataSize", 0)) + float(stats.get("indexSize", 0))) / (1024 * 1024)
    except Exception:
        logger.exception("Error checking MongoDB size")
        # Never route new records into a potentially full MongoDB when Turso
        # overflow is enabled and its threshold cannot be verified.
        if TURSO_ENABLED:
            raise
        return 0.0


async def _save_file_unlocked(media):
    """Save to MongoDB while it has room; use Turso for overflow records.

    A Turso outage must not stop normal MongoDB indexing before the configured
    MongoDB threshold is reached. Once MongoDB is full, fail closed rather than
    lose an index record.
    """
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_unique_id = getattr(media, "file_unique_id", None)
    file_name = re.sub(
        r"""[_\-\.#+$%^&*()!~\x60,;:"'?/<>\[\]{}=|\\]""", " ", str(media.file_name)
    )
    file_name = re.sub(r"\s+", " ", file_name).strip()
    duplicate_filter = {"$or": [{"file_id": file_id}]}
    if file_unique_id:
        duplicate_filter["$or"].append({"file_unique_id": file_unique_id})

    # MongoDB duplicate checks are always required.
    try:
        if await Media.find_one(duplicate_filter):
            return False, 0
        if MULTIPLE_DB and await Media2.find_one(duplicate_filter):
            return False, 0
    except Exception:
        logger.exception("MongoDB duplicate check failed; refusing save.")
        return False, 3

    cover_media = getattr(media, "video_cover", None) or getattr(media, "cover", None)
    data = {
        "file_id": file_id,
        "file_unique_id": file_unique_id,
        "file_ref": file_ref,
        "file_name": file_name,
        "file_size": media.file_size,
        "file_type": media.file_type,
        "mime_type": media.mime_type,
        "caption": media.caption.html if media.caption and INDEX_CAPTION else None,
        "cover": getattr(cover_media, "file_id", None) if COVERX else None,
    }

    use_turso = False
    if TURSO_ENABLED:
        try:
            primary_size = await check_db_size(db)
        except Exception:
            logger.exception("MongoDB size could not be verified; refusing save.")
            return False, 3
        use_turso = primary_size >= MONGO_MAX_SIZE_MB

        # Check Turso for cross-database duplicates. If it is temporarily
        # unavailable while MongoDB still has room, keep indexing in MongoDB.
        try:
            if await turso_store.find_duplicate(file_id, file_unique_id):
                return False, 0
        except Exception:
            if use_turso:
                logger.exception("Turso duplicate check failed and MongoDB is at its limit.")
                return False, 3
            logger.warning(
                "Turso duplicate check unavailable; continuing in MongoDB because it has room.",
                exc_info=True,
            )

        if use_turso:
            try:
                saved = await turso_store.insert_media(data)
                return (True, 1) if saved else (False, 0)
            except Exception:
                logger.exception("Turso overflow insert failed; MongoDB is at its configured limit.")
                return False, 3

    save_media = Media
    target_db = "Primary"
    if not TURSO_ENABLED and MULTIPLE_DB:
        try:
            if await check_db_size(db) >= 407:
                save_media = Media2
                target_db = "Secondary"
        except Exception:
            logger.exception("Could not check MongoDB size; using primary as legacy fallback.")

    try:
        record = save_media(**data)
        await record.commit()
        return True, 1
    except DuplicateKeyError:
        return False, 0
    except Exception:
        logger.exception("Failed to save '%s' to %s database.", file_name, target_db)
        return False, 3


_MEDIA_SAVE_LOCK = asyncio.Lock()


async def save_file(media):
    """Serialize size-check and insert so concurrent indexing doesn't overfill MongoDB."""
    async with _MEDIA_SAVE_LOCK:
        return await _save_file_unlocked(media)

async def get_search_results(chat_id, query, file_type=None, max_results=None, offset=0, filter=False):
    if max_results is None:
        if chat_id is not None:
            settings = await get_settings(int(chat_id))
            if "max_btn" not in settings:
                await save_group_settings(int(chat_id), "max_btn", True)
                settings["max_btn"] = True
            max_results = 10 if settings["max_btn"] else int(MAX_B_TN)
        else:
            max_results = int(MAX_B_TN)
    if isinstance(query, list):
        raw_pattern = "|".join(re.escape(q.strip()) for q in query if q and q.strip())
        if not raw_pattern:
            return [], None, 0
        regex = compile_regex(raw_pattern)
        if USE_CAPTION_FILTER:
            filter_mongo = {"$or": [{"file_name": regex},{"caption": regex},]}
        else:
            filter_mongo = {"file_name": regex}
    else:
        query = query.strip()
        if not query:
            return [], None, 0
        if " " in query:
            words = [re.escape(w) for w in query.split() if w]
            raw_pattern = (r".*[\s\.\+\-_]".join(words) if words else r".")
        else:
            raw_pattern = (r"(\b|[\.\+\-_])" + re.escape(query) + r"(\b|[\.\+\-_])" )
        try:
            regex = compile_regex(raw_pattern)
        except re.error:
            return [], None, 0
        if USE_CAPTION_FILTER:
            filter_mongo = { "$or": [{"file_name": regex}, {"caption": regex},]}
        else:
            filter_mongo = {"file_name": regex}

    if file_type:
        filter_mongo["file_type"] = file_type

    # Fetch candidates from MongoDB and (when configured) Turso. Turso is
    # searched independently so files indexed after MongoDB filled remain visible.
    fetch_limit = offset + max_results + 1
    mongo_tasks = [
        Media.find(filter_mongo).sort("$natural", -1).limit(fetch_limit).to_list(length=fetch_limit)
    ]
    count_tasks = [Media.count_documents(filter_mongo)]
    if MULTIPLE_DB:
        mongo_tasks.append(
            Media2.find(filter_mongo).sort("$natural", -1).limit(fetch_limit).to_list(length=fetch_limit)
        )
        count_tasks.append(Media2.count_documents(filter_mongo))
    mongo_results = await asyncio.gather(*mongo_tasks)
    mongo_count = await asyncio.gather(*count_tasks)
    files = []
    if TURSO_ENABLED:
        try:
            turso_files = await turso_store.search_media(raw_pattern, file_type, USE_CAPTION_FILTER)
            files.extend(turso_files)
        except Exception:
            logger.exception("Turso search failed; continuing with MongoDB results.")
    if len(mongo_results) > 1:
        files.extend(mongo_results[1])
    files.extend(mongo_results[0])
    total_results = sum(mongo_count) + (len(turso_files) if TURSO_ENABLED and 'turso_files' in locals() else 0)
    # Turso records are newest overflow records, so they are placed before MongoDB.
    page = files[offset:offset + max_results]
    next_offset = offset + len(page)
    if next_offset >= total_results:
        next_offset = ""
    files = page
    return files, next_offset, total_results

async def get_bad_files(query, file_type=None):
    query = query.strip()
    if not query:
        return [], 0
    if " " not in query:
        raw_pattern = r"(\b|[\.\+\-_])" + re.escape(query) + r"(\b|[\.\+\-_])"
    else:
        raw_pattern = r".*[\s\.\+\-_]".join(map(re.escape, query.split()))
    try:
        regex = compile_regex(raw_pattern)
    except re.error:
        return [], 0
    if USE_CAPTION_FILTER:
        filter_mongo = {
            "$or": [
                {"file_name": regex},
                {"caption": regex}
            ]
        }
    else:
        filter_mongo = {"file_name": regex}

    if file_type:
        filter_mongo["file_type"] = file_type

    tasks = [
        Media.find(filter_mongo).sort("$natural", -1).to_list(300)
    ]
    if MULTIPLE_DB:
        tasks.append(Media2.find(filter_mongo).sort("$natural", -1).to_list(300))
    results = await asyncio.gather(*tasks)
    files = []
    if TURSO_ENABLED:
        try:
            files.extend(await turso_store.search_media(raw_pattern, file_type, USE_CAPTION_FILTER))
        except Exception:
            logger.exception("Turso bad-file search failed.")
    if len(results) > 1:
        files.extend(results[1])
    files.extend(results[0])
    files = files[:300]
    return files, len(files)

_FILE_DETAILS_CACHE = LimitedDict(maxsize=300)

async def get_file_details(query):
    if not query:
        return []
    if query in _FILE_DETAILS_CACHE:
        return _FILE_DETAILS_CACHE[query]
    filter = {"file_id": query}
    if TURSO_ENABLED:
        try:
            found = await turso_store.get_media_by_id(query)
            if found:
                _FILE_DETAILS_CACHE[query] = found
                return found
        except Exception:
            logger.exception("Turso file-details lookup failed.")
    tasks = [Media.find(filter).to_list(length=1)]
    if MULTIPLE_DB:
        tasks.append(Media2.find(filter).to_list(length=1))
    results = await asyncio.gather(*tasks)
    for filedetails in results:
        if filedetails:
            _FILE_DETAILS_CACHE[query] = filedetails
            return filedetails
    return []

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash,
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref


async def delete_media_by_id(file_id):
    deleted = await Media.collection.delete_one({"_id": file_id})
    total = deleted.deleted_count
    if MULTIPLE_DB:
        result = await Media2.collection.delete_one({"_id": file_id})
        total += result.deleted_count
    if TURSO_ENABLED:
        try:
            total += await turso_store.delete_by_id(file_id)
        except Exception:
            logger.exception("Turso deletion failed after MongoDB deletion.")
            raise
    if total:
        _FILE_DETAILS_CACHE.pop(file_id, None)
    return total


async def delete_media_matching(file_name, file_size, mime_type):
    query = {"file_name": file_name, "file_size": file_size, "mime_type": mime_type}
    result = await Media.collection.delete_many(query)
    total = result.deleted_count
    if MULTIPLE_DB:
        result = await Media2.collection.delete_many(query)
        total += result.deleted_count
    if TURSO_ENABLED:
        try:
            total += await turso_store.delete_matching(file_name, file_size, mime_type)
        except Exception:
            logger.exception("Turso matching-delete failed after MongoDB deletion.")
            raise
    return total


async def delete_all_media():
    await Media.collection.drop()
    if MULTIPLE_DB:
        await Media2.collection.drop()
    if TURSO_ENABLED:
        try:
            await turso_store.delete_all()
        except Exception:
            logger.exception("Turso delete-all failed after MongoDB collections were cleared.")
            raise


async def dreamxbotz_fetch_media(limit: int) -> List[dict]:
    files = []
    if TURSO_ENABLED:
        try:
            files.extend(await turso_store.recent_media(limit))
        except Exception:
            logger.exception("Turso recent-media lookup failed; continuing with MongoDB.")
    try:
        if MULTIPLE_DB:
            secondary = await Media2.find().sort("$natural", -1).limit(limit).to_list(length=limit)
            files.extend(secondary)
        files.extend(await Media.find().sort("$natural", -1).limit(limit).to_list(length=limit))
        return files[:limit]
    except Exception as e:
        logger.error("Error in dreamxbotz_fetch_media: %s", e)
        return files[:limit]


async def dreamxbotz_clean_title(filename: str, is_series: bool = False) -> str:
    try:
        year_match = re.search(r"^(.*?(\d{4}|\(\d{4}\)))", filename, re.IGNORECASE)
        if year_match:
            title = year_match.group(1).replace("(", "").replace(")", "")
            return (
                re.sub(
                    r"(?:@[^ \n\r\t.,:;!?()\[\]{}<>\\\/\"'=_%]+|[._\-\[\]@()]+)",
                    " ",
                    title,
                )
                .strip()
                .title()
            )
        if is_series:
            season_match = re.search(
                r"(.*?)(?:S(\d{1,2})|Season\s*(\d+)|Season(\d+))(?:\s*Combined)?",
                filename,
                re.IGNORECASE,
            )
            if season_match:
                title = season_match.group(1).strip()
                season = (
                    season_match.group(2)
                    or season_match.group(3)
                    or season_match.group(4)
                )
                title = (
                    re.sub(
                        r"(?:@[^ \n\r\t.,:;!?()\[\]{}<>\\\/\"'=_%]+|[._\-\[\]@()]+)",
                        " ",
                        title,
                    )
                    .strip()
                    .title()
                )
                return f"{title} S{int(season):02}"
        title = filename
        return (
            re.sub(
                r"(?:@[^ \n\r\t.,:;!?()\[\]{}<>\\\/\"'=_%]+|[._\-\[\]@()]+)", " ", title
            )
            .strip()
            .title()
        )
    except Exception as e:
        logger.error(f"Error in truncate_title: {e}")
        return filename


async def dreamxbotz_get_movies(limit: int = 20) -> List[str]:
    try:
        cursor = await dreamxbotz_fetch_media(limit * 2)
        results = set()
        pattern = r"(?:s\d{1,2}|season\s*\d+|season\d+)(?:\s*combined)?(?:e\d{1,2}|episode\s*\d+)?\b"
        for file in cursor:
            file_name = getattr(file, "file_name", "")
            if not re.search(pattern, file_name, re.IGNORECASE):
                title = await dreamxbotz_clean_title(file_name)
                results.add(title)
            if len(results) >= limit:
                break
        return sorted(list(results))[:limit]
    except Exception as e:
        logger.error(f"Error in dreamxbotz_get_movies: {e}")
        return []


async def dreamxbotz_get_series(limit: int = 30) -> Dict[str, List[int]]:
    try:
        cursor = await dreamxbotz_fetch_media(limit * 5)
        grouped = defaultdict(list)
        pattern = r"(.*?)(?:S(\d{1,2})|Season\s*(\d+)|Season(\d+))(?:\s*Combined)?(?:E(\d{1,2})|Episode\s*(\d+))?\b"
        for file in cursor:
            file_name = getattr(file, "file_name", "")
            match = re.search(pattern, file_name, re.IGNORECASE)
            if match:
                title = await dreamxbotz_clean_title(match.group(1), is_series=True)
                season = int(match.group(2) or match.group(3) or match.group(4))
                grouped[title].append(season)
        return {
            title: sorted(set(seasons))[:10]
            for title, seasons in grouped.items()
            if seasons
        }
    except Exception as e:
        logger.error(f"Error in dreamxbotz_get_series: {e}")
        return []
