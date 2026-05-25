'''
Author: ablecats etsy@live.com
LastEditors: ablecats etsy@live.com
LastEditTime: 2026-05-25 17:19:26
Description: 
'''
# This file is a part of TG-FileStreamBot
# Coding : Jyothis Jayanth [@EverythingSuckz]

import sys
import asyncio
import logging
import logging.handlers
from .config import Config
from aiohttp import web
from pyrogram import idle
from WebStreamer import StreamBot
from WebStreamer.server import web_server
from WebStreamer.bot.client_manager import ClientManager
from WebStreamer.bot import sessions_dir
from WebStreamer.utils.keepalive import ping_server

logging.basicConfig(
    level=logging.DEBUG if Config.DEBUG else logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
    format="[%(asctime)s][%(name)s][%(levelname)s] ==> %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout),
              logging.handlers.RotatingFileHandler("streambot.log", maxBytes=1024 * 1024, backupCount=0, encoding="utf-8")],)

logging.getLogger("aiohttp").setLevel(logging.DEBUG if Config.DEBUG else logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.INFO if Config.DEBUG else logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.DEBUG if Config.DEBUG else logging.ERROR)

server = None

loop = asyncio.get_event_loop()

async def start_services():
    global server
    logging.info("Initializing Telegram Bot")
    await StreamBot.start()
    bot_info = await StreamBot.get_me()
    logging.debug(bot_info)

    StreamBot.username = bot_info.username
    logging.info("Initialized Telegram Bot")

    client_manager = ClientManager(StreamBot, sessions_dir)
    await client_manager.initialize_clients()
    
    if Config.KEEP_ALIVE:
        asyncio.create_task(ping_server())

    server = web.AppRunner(web_server(client_manager))
    await server.setup()
    await web.TCPSite(server, Config.BIND_ADDRESS, Config.PORT).start()
    logging.info("Service Started")
    logging.info("bot =>> {}".format(bot_info.first_name))

    if bot_info.dc_id:
        logging.info("DC ID =>> {}".format(str(bot_info.dc_id)))
    logging.info("URL =>> {}".format(Config.URL))
    
    await idle()
        
async def cleanup():
    global server
    if server is not None:
        try:
            await server.cleanup()
        except Exception as e:
            logging.error(f"Error cleaning up web server: {e}")
    try:
        if StreamBot.is_connected:
            await StreamBot.stop()
    except Exception as e:
        pass

if __name__ == "__main__":
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        logging.error(err.with_traceback(None))
    finally:
        loop.run_until_complete(cleanup())
        loop.stop()
        logging.info("Stopped Services")