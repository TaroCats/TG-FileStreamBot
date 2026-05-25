# This file is a part of TG-FileStreamBot
# Coding : Jyothis Jayanth [@EverythingSuckz]


import os
import os.path
from ..config import Config
import logging
from pyrogram import Client

logger = logging.getLogger("bot")

sessions_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
if Config.USE_SESSION_FILE:
    logger.info("Using session files")
    logger.info("Session folder path: {}".format(sessions_dir))
    if not os.path.isdir(sessions_dir):
        os.makedirs(sessions_dir)

StreamBot = Client(
    name="WebStreamer",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    workdir=sessions_dir if Config.USE_SESSION_FILE else "WebStreamer",
    plugins={"root": "WebStreamer/bot/plugins"},
    bot_token=Config.BOT_TOKEN,
    sleep_threshold=Config.SLEEP_THRESHOLD,
    workers=Config.WORKERS,
    in_memory=not Config.USE_SESSION_FILE,
)


