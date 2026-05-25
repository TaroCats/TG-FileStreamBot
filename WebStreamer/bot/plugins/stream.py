'''
Author: ablecats etsy@live.com
LastEditors: ablecats etsy@live.com
LastEditTime: 2026-05-25 16:43:42
Description: 
'''
import re
from urllib.parse import quote_plus
from pyrogram import filters, Client
from pyrogram.types import Message
from WebStreamer.config import Config
from WebStreamer.bot import StreamBot
from WebStreamer.utils.file_properties import get_hash, get_name

async def generate_and_send_links(m: Message, source_message: Message):
    try:
        log_msg = await source_message.copy(chat_id=Config.BIN_CHANNEL)
        
        file_hash = get_hash(source_message, Config.HASH_LENGTH)
        display_name = get_name(source_message)
        
        short_link = f"{Config.URL}{file_hash}{log_msg.id}"
        stream_link = f"{Config.URL}{log_msg.id}/{quote_plus(display_name)}?hash={file_hash}"
        
        reply_text = (
            f"**文件名:** `{display_name}`\n"
            f"**短链接:** {short_link}\n"
            f"**流链接:** {stream_link}"
        )
        
        await m.reply_text(
            text=reply_text,
            quote=True,
            disable_web_page_preview=True
        )
    except Exception as e:
        await m.reply_text(f"生成直链失败: {e}", quote=True)

def check_user_permission(m: Message) -> bool:
    if Config.ALLOWED_USERS and not (
        (str(m.from_user.id) in Config.ALLOWED_USERS)
        or (m.from_user.username in Config.ALLOWED_USERS)
    ):
        return False
    return True

@StreamBot.on_message(
    filters.private & (
        filters.document
        | filters.video
        | filters.audio
        | filters.animation
        | filters.voice
        | filters.video_note
        | filters.photo
        | filters.sticker
    ),
    group=4,
)
async def private_receive_handler(c: Client, m: Message):
    if not check_user_permission(m):
        return await m.reply(
            "你不在可以使用我的用户的列表中。", disable_web_page_preview=True, quote=True
        )

    await generate_and_send_links(m, m)

@StreamBot.on_message(
    filters.private & filters.text & filters.regex(r"https?://t\.me/(?:c/)?([^/]+)/(\d+)"),
    group=5,
)
async def link_receive_handler(c: Client, m: Message):
    if not check_user_permission(m):
        return await m.reply(
            "你不在可以使用我的用户的列表中。", disable_web_page_preview=True, quote=True
        )

    try:
        pattern = r"https?://t\.me/(?:c/)?([^/]+)/(\d+)"
        matches = re.finditer(pattern, m.text)
        
        for match in matches:
            channel_or_id, message_id_str = match.groups()
            message_id = int(message_id_str)
            
            if channel_or_id.isdigit():
                chat_id = int(f"-100{channel_or_id}")
            else:
                chat_id = channel_or_id
                
            try:
                message = await c.get_messages(chat_id, message_id)
            except Exception as e:
                await m.reply(f"无法获取消息，请确保机器人有权限访问该频道/群组。\n链接: {match.group(0)}\n错误信息: {e}", quote=True)
                continue
                
            if message.empty:
                await m.reply(f"消息不存在或已被删除。\n链接: {match.group(0)}", quote=True)
                continue

            # 如果这条消息属于一个媒体组（多个文件），则获取该组内的所有文件
            if message.media_group_id:
                try:
                    media_group = await c.get_media_group(chat_id, message_id)
                    for mg_msg in media_group:
                        await generate_and_send_links(m, mg_msg)
                except Exception as e:
                    await m.reply_text(f"获取媒体组失败: {e}", quote=True)
            else:
                await generate_and_send_links(m, message)

    except Exception as e:
        await m.reply_text(f"解析链接失败: {e}", quote=True)
