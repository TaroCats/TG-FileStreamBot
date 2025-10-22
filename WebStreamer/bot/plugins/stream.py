'''
Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditors: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
LastEditTime: 2025-10-22 09:47:09
Description: 
'''
# This file is a part of TG-FileStreamBot
# Coding : Jyothis Jayanth [@EverythingSuckz]

import logging
import re
from pyrogram import filters, errors
from WebStreamer.vars import Var
from urllib.parse import quote_plus
from WebStreamer.bot import StreamBot, logger
from WebStreamer.utils.file_properties import get_hash, get_name
from WebStreamer.utils.cloudreve import async_remote_download_url_from_vars
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery


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
    stream_link = f"{Var.URL}{log_msg.id}/{quote_plus(get_name(m))}?hash={file_hash}"
    short_link = f"{Var.URL}{file_hash}{log_msg.id}"
    logger.info(f"直链： {stream_link} for {m.from_user.first_name}")
    try:
        await m.reply_text(
            text="直链已准备好(￣▽￣)／ 单击下面的链接可直接复制：\n<code>{}</code>\n(<a href='{}'>短链接</a>)".format(
                stream_link, short_link
            ),
            quote=True,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("打开", url=stream_link),
                        InlineKeyboardButton("保存到云盘", callback_data="save_cloudreve"),
                    ]
                ]
            ),
        )
    except errors.ButtonUrlInvalid:
        await m.reply_text(
            text="<code>{}</code>\n\n短链: {})".format(
                stream_link, short_link
            ),
            quote=True,
            parse_mode=ParseMode.HTML,
        )


@StreamBot.on_callback_query(filters.regex("^save_cloudreve$"))
async def save_to_cloudreve_handler(_, q: CallbackQuery):
    # 权限校验（复用与消息处理一致的策略）
    user = q.from_user
    if Var.ALLOWED_USERS and not ((str(user.id) in Var.ALLOWED_USERS) or (user.username in Var.ALLOWED_USERS)):
        return await q.answer("你没有权限使用此功能。", show_alert=True)

    # 从消息文本中解析直链
    text = q.message.text or ""
    m = re.search(r"<code>([^<]+)</code>", text)
    stream_link = m.group(1).strip() if m else None

    # 兜底：尝试使用短链（如存在）
    if not stream_link:
        m2 = re.search(r"<a href='([^']+)'>短链接</a>", text)
        stream_link = m2.group(1).strip() if m2 else None

    if not stream_link:
        return await q.answer("未能解析直链，请重试或重新生成。", show_alert=True)

    try:
        await async_remote_download_url_from_vars(stream_link)
        await q.answer("已提交到云盘。", show_alert=True)
    except Exception as e:
        # 将错误返回给用户
        await q.answer(f"云盘提交失败：{e}", show_alert=True)
