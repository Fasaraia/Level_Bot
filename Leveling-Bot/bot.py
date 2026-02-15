import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class LevelingBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
    
    async def setup_hook(self):
        await self.load_extension('cogs.leveling')
        await self.load_extension('cogs.shop')
        await self.load_extension('cogs.commands')
        await self.load_extension('cogs.custom_roll')
        print("Syncing commands...")
        await self.tree.sync()
        print("Commands synced!")
    
    async def on_ready(self):
        print(f'✅ Logged in as {self.user.name} ({self.user.id})')
        print(f'Connected to {len(self.guilds)} guild(s)')
        print('------')


async def main():
    bot = LevelingBot()
    try:
        await bot.start(os.getenv('DISCORD_TOKEN'))
    except KeyboardInterrupt:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(main())