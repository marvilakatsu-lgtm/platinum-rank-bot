import logging
import discord
from discord.ext import commands

import config
from database import Database

logging.basicConfig(level=logging.INFO)

EXTENSOES = ("cogs.perfil", "cogs.platinas", "cogs.ranking", "cogs.colizeu")


class ColizeuBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default())
        self.db = Database(config.DB_PATH)

    async def setup_hook(self):
        await self.db.connect()
        for ext in EXTENSOES:
            await self.load_extension(ext)
        if config.GUILD_ID:  # sincroniza instantâneo no seu servidor
            guild = discord.Object(config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:  # global pode levar até 1h para aparecer
            await self.tree.sync()

    async def on_ready(self):
        logging.info("Colizeu Bot online como %s", self.user)


if __name__ == "__main__":
    if not config.TOKEN:
        raise SystemExit("Defina DISCORD_TOKEN nas variáveis de ambiente.")
    ColizeuBot().run(config.TOKEN)
