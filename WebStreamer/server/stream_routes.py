# Taken from megadlbot_oss <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/webserver/routes.py>
# Thanks to Eyaadh <https://github.com/eyaadh>

import re
import time
import math
import logging
import mimetypes
from urllib.parse import quote_plus
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine

from WebStreamer.server.exceptions import FIleNotFound, InvalidHash
from WebStreamer import Config, StartTime, __version__
from WebStreamer.utils.custom_dl import ByteStreamer
from WebStreamer.utils.file_properties import get_hash, get_name
from WebStreamer.utils.time_format import get_readable_time

logger = logging.getLogger("routes")


routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request: web.Request):
    return web.json_response(
        {
            "server_status": "running",
            "uptime": get_readable_time(time.time() - StartTime),
            "telegram_bot": "@" + request.app["client_manager"].main_bot.username,
            "connected_bots": len(request.app["client_manager"].clients),
            "loads": dict(
                ("bot" + str(c + 1), l)
                for c, (_, l) in enumerate(
                    sorted(request.app["client_manager"].work_loads.items(), key=lambda x: x[1], reverse=True)
                )
            ),
            "version": f"v{__version__}",
        }
    )

async def _resolve_by_link(request: web.Request, link: str) -> web.Response:
    StreamBot = request.app["client_manager"].main_bot
    """Core resolver: given a t.me message link, return direct links JSON."""
    try:
        pattern = r"https?://t\.me/(?:c/)?([^/]+)/(\d+)"
        m = re.match(pattern, link.strip())
        if not m:
            return web.json_response({"error": "unsupported t.me link format"}, status=422)

        channel_or_id, message_id_str = m.groups()
        message_id = int(message_id_str)

        try:
            message = await StreamBot.get_messages(channel_or_id, message_id)
        except Exception as e:
            logger.exception("resolve: get_messages failed: %s", e)
            return web.json_response({"error": f"cannot fetch telegram message: {e}"}, status=502)

        # Copy/republish to BIN_CHANNEL to ensure stream permission
        try:
            log_msg = await StreamBot.copy_message(
                chat_id=Config.BIN_CHANNEL,
                from_chat_id=message.chat.id,
                message_id=message.id,
            )
        except Exception:
            # Fallback: send by specific media type
            try:
                if getattr(message, "document", None):
                    log_msg = await StreamBot.send_document(
                        Config.BIN_CHANNEL,
                        message.document.file_id,
                        caption=(message.caption or ""),
                        caption_entities=message.caption_entities,
                        reply_markup=message.reply_markup,
                    )
                elif getattr(message, "video", None):
                    log_msg = await StreamBot.send_video(
                        Config.BIN_CHANNEL,
                        message.video.file_id,
                        caption=(message.caption or ""),
                        caption_entities=message.caption_entities,
                        reply_markup=message.reply_markup,
                    )
                elif getattr(message, "audio", None):
                    log_msg = await StreamBot.send_audio(
                        Config.BIN_CHANNEL,
                        message.audio.file_id,
                        caption=(message.caption or ""),
                        caption_entities=message.caption_entities,
                        reply_markup=message.reply_markup,
                    )
                elif getattr(message, "animation", None):
                    log_msg = await StreamBot.send_animation(
                        Config.BIN_CHANNEL,
                        message.animation.file_id,
                        caption=(message.caption or ""),
                        caption_entities=message.caption_entities,
                        reply_markup=message.reply_markup,
                    )
                elif getattr(message, "voice", None):
                    log_msg = await StreamBot.send_voice(
                        Config.BIN_CHANNEL,
                        message.voice.file_id,
                        caption=(message.caption or ""),
                        caption_entities=message.caption_entities,
                        reply_markup=message.reply_markup,
                    )
                elif getattr(message, "photo", None):
                    # For photo, send the biggest size
                    photo = message.photo
                    file_id = photo.file_id if hasattr(photo, "file_id") else photo[-1].file_id
                    log_msg = await StreamBot.send_photo(
                        Config.BIN_CHANNEL,
                        file_id,
                        caption=(message.caption or ""),
                        caption_entities=message.caption_entities,
                        reply_markup=message.reply_markup,
                    )
                elif getattr(message, "video_note", None):
                    log_msg = await StreamBot.send_video_note(Config.BIN_CHANNEL, message.video_note.file_id)
                elif getattr(message, "sticker", None):
                    log_msg = await StreamBot.send_sticker(Config.BIN_CHANNEL, message.sticker.file_id)
                else:
                    # Fallback to plain text
                    log_msg = await StreamBot.send_message(
                        Config.BIN_CHANNEL,
                        (message.text or message.caption or ""),
                        entities=message.entities,
                        reply_markup=message.reply_markup,
                    )
            except Exception as e:
                logger.exception("resolve: send to BIN_CHANNEL failed: %s", e)
                return web.json_response({"error": f"cannot duplicate message: {e}"}, status=502)

        # Build links using BIN_CHANNEL message id and original media info
        file_hash = get_hash(message, Config.HASH_LENGTH)
        display_name = get_name(message)
        short_link = f"{Config.URL}{file_hash}{log_msg.id}"
        stream_link = f"{Config.URL}{log_msg.id}/{quote_plus(display_name)}?hash={file_hash}"

        return web.json_response({
            "ok": True,
            "short_link": short_link,
            "stream_link": stream_link,
            "message_id": log_msg.id,
            "hash": file_hash,
            "name": display_name,
        })
    except Exception as e:
        logger.exception("resolve: unexpected error: %s", e)
        return web.json_response({"error": str(e)}, status=500)

@routes.get("/api/resolve", allow_head=True)
async def resolve_tme_link_handler(request: web.Request):
    """Resolve a Telegram t.me message link into a streamable direct link.

    Query params:
      - url: https://t.me/<channel|group>/<message_id> or https://t.me/c/<id>/<message_id>

    Returns JSON with short_link and stream_link.
    """
    link = request.rel_url.query.get("url")
    if not link:
        return web.json_response({"error": "missing 'url' query param"}, status=400)
    return await _resolve_by_link(request, link)

@routes.post("/api/resolve")
async def resolve_tme_link_post_handler(request: web.Request):
    """POST variant: accepts JSON {url} or form field 'url', also raw text."""
    link = None
    try:
        ctype = request.content_type or ""
        if ctype.startswith("application/json"):
            data = await request.json()
            if isinstance(data, dict):
                link = data.get("url") or data.get("link")
        else:
            # form-encoded or multipart
            form = await request.post()
            link = form.get("url") or form.get("link")
        if not link:
            # fallback: treat raw text body as the URL
            text = (await request.text()).strip()
            if text.startswith("http"):
                link = text
    except Exception as e:
        logger.exception("resolve: parsing POST body failed: %s", e)
        return web.json_response({"error": f"invalid request body: {e}"}, status=400)

    if not link:
        return web.json_response({"error": "missing 'url' in body"}, status=400)

    return await _resolve_by_link(request, link)

@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([0-9a-f]{%s})(\d+)$" % (Config.HASH_LENGTH), path)
        if match:
            secure_hash = match.group(1)
            message_id = int(match.group(2))
        else:
            message_id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return await media_streamer(request, message_id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logger.critical(str(e), exc_info=True)
        raise web.HTTPInternalServerError(text=str(e))

class_cache = {}

async def media_streamer(request: web.Request, message_id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    
    client_manager = request.app["client_manager"]
    index, faster_client = client_manager.get_fastest_client()
    
    if Config.MULTI_CLIENT:
        logger.info(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logger.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logger.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
    logger.debug("before calling get_file_properties")
    file_id = await tg_connect.get_file_properties(message_id)
    logger.debug("after calling get_file_properties")
    
    
    if get_hash(file_id.unique_id, Config.HASH_LENGTH) != secure_hash:
        logger.debug(f"Invalid hash for message with ID {message_id}")
        raise InvalidHash
    
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
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size, client_manager
    )
    mime_type = file_id.mime_type
    file_name = get_name(file_id)
    disposition = "attachment"

    if not mime_type:
        mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

    if "video/" in mime_type or "audio/" in mime_type or "/html" in mime_type:
        disposition = "inline"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )
