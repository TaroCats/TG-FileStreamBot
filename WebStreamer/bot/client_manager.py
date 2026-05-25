import asyncio
import logging
from os import environ
from ..config import Config
from pyrogram import Client

logger = logging.getLogger("multi_client")

class ClientManager:
    def __init__(self, main_bot: Client, sessions_dir: str):
        self.clients = {0: main_bot}
        self.work_loads = {0: 0}
        self.sessions_dir = sessions_dir
        self.main_bot = main_bot

    async def initialize_clients(self):
        all_tokens = dict(
            (c + 1, t)
            for c, (_, t) in enumerate(
                filter(
                    lambda n: n[0].startswith("MULTI_TOKEN"), sorted(environ.items())
                )
            )
        )
        if not all_tokens:
            logger.info("No additional clients found, using default client")
            return
        
        async def start_client(client_id, token):
            try:
                logger.info(f"Starting - Client {client_id}")
                if client_id == len(all_tokens):
                    await asyncio.sleep(2)
                    print("This will take some time, please wait...")
                client = await Client(
                    name=str(client_id),
                    api_id=Config.API_ID,
                    api_hash=Config.API_HASH,
                    bot_token=token,
                    sleep_threshold=Config.SLEEP_THRESHOLD,
                    workdir=self.sessions_dir if Config.USE_SESSION_FILE else Client.PARENT_DIR,
                    no_updates=True,
                    in_memory=not Config.USE_SESSION_FILE,
                ).start()
                self.work_loads[client_id] = 0
                return client_id, client
            except Exception:
                logger.error(f"Failed starting Client - {client_id} Error:", exc_info=True)
                return None
        
        results = await asyncio.gather(*[start_client(i, token) for i, token in all_tokens.items()])
        for res in results:
            if res:
                client_id, client = res
                self.clients[client_id] = client
                self.work_loads[client_id] = 0

        if len(self.clients) > 1:
            Config.MULTI_CLIENT = True
            logger.info("Multi-client mode enabled")
        else:
            logger.info("No additional clients were initialized, using default client")

    def get_fastest_client(self):
        index = min(self.work_loads, key=self.work_loads.get)
        return index, self.clients[index]

    def increment_load(self, index: int):
        self.work_loads[index] += 1

    def decrement_load(self, index: int):
        self.work_loads[index] -= 1

    async def stop_all(self):
        for index, client in self.clients.items():
            if index != 0:  # Main bot is stopped separately
                await client.stop()

