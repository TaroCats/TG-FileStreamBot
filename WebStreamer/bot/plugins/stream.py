'''
Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditors: ablecats etsy@live.com
LastEditTime: 2025-10-22 17:55:57
Description: 
'''
# This file is a part of TG-FileStreamBot
# Coding : Jyothis Jayanth [@EverythingSuckz]

import re
from pyrogram import filters, errors
from WebStreamer.vars import Var
from urllib.parse import quote_plus
from WebStreamer.bot import StreamBot, logger
from WebStreamer.utils.file_properties import get_hash, get_name
from WebStreamer.utils.cloudreve import async_remote_download_url_from_vars
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import MessageEntityType
# 修复报错
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999999

# 缓存消息对应的直链，键为机器人回复消息的 id
STREAM_LINK_CACHE = {}

# 公共函数：生成短链与直链
def build_links(file_hash: str, msg_id: int, display_name: str):
    short_link = f"{Var.URL}{file_hash}{msg_id}"
    stream_link = f"{Var.URL}{msg_id}/{quote_plus(display_name)}?hash={file_hash}"
    return short_link, stream_link

# 公共函数：统一回复消息并缓存直链
async def reply_with_stream_links(target_msg: Message, stream_link: str, short_link: str, show_code_link: str = "stream"):
    try:
        text_link = stream_link if show_code_link == "stream" else short_link
        sent = await target_msg.reply_text(
            text="单击下面的链接可直接复制：\n<code>{}</code>".format(text_link),
            quote=True,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("打开直链", url=stream_link),
                        InlineKeyboardButton("保存到云盘", callback_data="save_cloudreve"),
                    ]
                ]
            ),
        )
        STREAM_LINK_CACHE[sent.id] = stream_link
        return sent
    except errors.ButtonUrlInvalid:
        sent = await target_msg.reply_text(
            text="<code>{}</code>\n\n短链: {}".format(stream_link, short_link),
            quote=True,
            parse_mode=ParseMode.HTML,
        )
        STREAM_LINK_CACHE[sent.id] = stream_link
        return sent

# 处理消息链接，通过TG消息链接获取文件直链


@StreamBot.on_message(filters.private & filters.text & filters.regex(r"https?://t\.me/"))
async def link_receive_handler(_, m: Message):
    link = m.text
    pattern = r"https?://t\.me/(?:c/)?([^/]+)/(\d+)"
    match = re.match(pattern, link.strip())
    if not match:
        return
    channel_username, message_id = match.groups()
    try:
        message = await StreamBot.get_messages(channel_username, int(message_id))
        log_msg = await message.forward(chat_id=Var.BIN_CHANNEL)
    except errors.ChannelPrivate:
        return await m.reply("这个频道是私有的，我不能访问它。", quote=True)
    except errors.ChannelInvalid:
        return await m.reply("这个频道不存在。", quote=True)
    except errors.MessageIdInvalid:
        return await m.reply("这个消息不存在。", quote=True)
    if not message.media:
        return await m.reply("这个消息不是文件。", quote=True)
    file_hash = get_hash(message, Var.HASH_LENGTH)
    short_link, stream_link = build_links(file_hash, log_msg.id, get_name(message))
    logger.info(f"直链： {stream_link} for {m.from_user.first_name}")
    await reply_with_stream_links(m, stream_link, short_link, show_code_link="stream")


# 处理消息中的文件（文档、视频、音频等）
@StreamBot.on_message(
    filters.private
    & (
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
async def media_receive_handler(_, m: Message):
    if Var.ALLOWED_USERS and not ((str(m.from_user.id) in Var.ALLOWED_USERS) or (m.from_user.username in Var.ALLOWED_USERS)):
        return await m.reply("你<b>没有权限</b>使用这个机器人。", quote=True)
    log_msg = await m.forward(chat_id=Var.BIN_CHANNEL)
    file_hash = get_hash(log_msg, Var.HASH_LENGTH)
    short_link, stream_link = build_links(file_hash, log_msg.id, get_name(m))
    logger.info(f"直链： {stream_link} for {m.from_user.first_name}")
    await reply_with_stream_links(m, stream_link, short_link, show_code_link="short")


@StreamBot.on_callback_query(filters.regex("^save_cloudreve$"))
async def save_to_cloudreve_handler(_, q: CallbackQuery):
    # 权限校验（复用与消息处理一致的策略）
    user = q.from_user
    if Var.ALLOWED_USERS and not ((str(user.id) in Var.ALLOWED_USERS) or (user.username in Var.ALLOWED_USERS)):
        return await q.answer("你没有权限使用此功能。", show_alert=True)

    # 先尝试从缓存中获取直链（由发送消息阶段写入）
    stream_link = STREAM_LINK_CACHE.get(q.message.id)

    # 从消息内容和内联按钮/实体中健壮地解析直链（作为兜底）
    if not stream_link:
        text = q.message.text or ""
        # 优先内联按钮
        try:
            markup = getattr(q.message, "reply_markup", None)
            if markup and getattr(markup, "inline_keyboard", None):
                for row in markup.inline_keyboard:
                    for btn in row:
                        url = getattr(btn, "url", None)
                        if url:
                            stream_link = url.strip()
                            break
                    if stream_link:
                        break
        except Exception:
            pass
        # 文本链接实体
        if not stream_link:
            entities = getattr(q.message, "entities", None) or []
            for ent in entities:
                if ent.type == MessageEntityType.TEXT_LINK and getattr(ent, "url", None):
                    stream_link = ent.url.strip()
                    break
        # code 实体
        if not stream_link:
            entities = getattr(q.message, "entities", None) or []
            for ent in entities:
                if ent.type == MessageEntityType.CODE:
                    try:
                        stream_link = text[ent.offset: ent.offset +
                                           ent.length].strip()
                        break
                    except Exception:
                        continue
        # 纯文本正则
        if not stream_link:
            m = re.search(r"https?://\S+", text)
            stream_link = m.group(0).strip() if m else None

    if not stream_link:
        return await q.answer("未能解析直链，请重试或重新生成。", show_alert=True)

    try:
        await async_remote_download_url_from_vars(stream_link)
        # 使用一次后可删除缓存，避免堆积
        try:
            STREAM_LINK_CACHE.pop(q.message.id, None)
        except Exception:
            pass
        await q.answer("已提交到云盘。", show_alert=True)
    except Exception as e:
        # 将错误返回给用户
        await q.answer(f"云盘提交失败：{e}", show_alert=True)
