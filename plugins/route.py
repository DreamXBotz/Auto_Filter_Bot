from aiohttp import web
import re
import math
import logging
import secrets
import mimetypes
import asyncio
from aiohttp.http_exceptions import BadStatusLine
from dreamxbotz.Bot import multi_clients, work_loads
from dreamxbotz.server.exceptions import FIleNotFound, InvalidHash
from dreamxbotz.util.custom_dl import ByteStreamer
from dreamxbotz.util.render_template import render_page
import info

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

@routes.get("/favicon.ico")
async def favicon_route_handler(request):
    return web.FileResponse('dreamxbotz/template/favicon.ico')

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    try:
        with open("dreamxbotz/template/Invalid.html", "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html")
    except Exception:
        return web.Response(
            text="<h1>Restricted Cloud Node</h1><p>Visit official Telegram bot: <a href='https://t.me/BoultflixMovieBot'>@BoultflixMovieBot</a></p>",
            content_type="text/html"
        )

@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def watch_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return web.Response(text=await render_page(id, secure_hash), content_type='text/html')
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logger.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id_match = re.search(r"(\d+)(?:\/\S+)?", path)
            if not id_match:
                raise web.HTTPNotFound(text="Not found")
            id = int(id_match.group(1))
            secure_hash = request.rel_url.query.get("hash")
        
        # Check if AAC Transcode or Multi-Audio track is requested
        if request.rel_url.query.get("transcode") == "1" or "audio" in request.rel_url.query:
            return await transcode_streamer(request, id, secure_hash)

        return await media_streamer(request, id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except web.HTTPNotFound:
        raise
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logger.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

class_cache = {}

async def get_tg_streamer(id: int, secure_hash: str):
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
    else:
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
    file_id = await tg_connect.get_file_properties(id)
    if file_id.unique_id[:6] != secure_hash:
        raise InvalidHash
    return tg_connect, file_id, index

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    tg_connect, file_id, index = await get_tg_streamer(id, secure_hash)
    file_size = file_id.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )
    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil((until_bytes + 1) / chunk_size) - math.floor(offset / chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name

    if not mime_type:
        mime_type = mimetypes.guess_type(file_name)[0] or "video/mp4"

    resp_headers = {
        "Content-Type": f"{mime_type}",
        "Content-Length": str(req_length),
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Accept-Ranges": "bytes",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Content-Type",
        "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges",
    }
    
    if range_header:
        resp_headers["Content-Range"] = f"bytes {from_bytes}-{until_bytes}/{file_size}"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers=resp_headers
    )

# Real-Time On-The-Fly Audio Transcoding (DDP/AC3 -> AAC) & Multi-Audio Selector
async def transcode_streamer(request: web.Request, id: int, secure_hash: str):
    tg_connect, file_id, index = await get_tg_streamer(id, secure_hash)
    audio_idx = request.rel_url.query.get("audio", "0")
    
    # Internal source loop stream
    source_url = f"http://127.0.0.1:{info.PORT}/{request.match_info['path']}?hash={secure_hash}"
    
    ffmpeg_cmd = [
        "ffmpeg",
        "-reconnect", "1",
        "-reconnect_at_eof", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", source_url,
        "-map", "0:v:0",
        "-map", f"0:a:{audio_idx}?",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "-f", "mp4",
        "pipe:1"
    ]

    process = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL
    )

    response = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "video/mp4",
            "Content-Disposition": f'inline; filename="stream_{file_id.file_name}.mp4"',
            "Access-Control-Allow-Origin": "*",
        }
    )
    await response.prepare(request)

    try:
        while True:
            chunk = await process.stdout.read(64 * 1024)
            if not chunk:
                break
            await response.write(chunk)
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        try:
            process.kill()
        except Exception:
            pass

    return response
