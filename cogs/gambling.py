import discord
from discord.ext import commands
from discord import app_commands
from utils import firebase_manager
from datetime import datetime, timezone
import random
from config import config as bot_config
from typing import Literal

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="coinflip", description="Risk your coins for a chance to win more!")
    async def coinflip(self, interaction: discord.Interaction, amount: int, face: Literal["heads", "tails"]):
        try:
            user_id = str(interaction.user.id)
            user_data = firebase_manager.get_user_data(user_id)

            if amount <= 0 or amount > 1000:
                await interaction.response.send_message("Please enter a valid amount to perform a coinflip (max 1000).", ephemeral=True)
                return
            
            if user_data['coins'] < amount:
                await interaction.response.send_message("You don't have enough coins.", ephemeral=True)
                return
            
            # Check cooldown
            now = datetime.now(timezone.utc)
            last_gamble_time = user_data.get('lastGambleTime')
            if last_gamble_time:
                # Parse the string from Firebase back into a datetime
                last_gamble_dt = datetime.fromisoformat(last_gamble_time)
                
                # Make it timezone-aware if it isn't already
                if last_gamble_dt.tzinfo is None:
                    last_gamble_dt = last_gamble_dt.replace(tzinfo=timezone.utc)
                
                elapsed_time = (now - last_gamble_dt).total_seconds()

                if elapsed_time < bot_config.GAMBLE_COOLDOWN:
                    unlock_time = int(now.timestamp()) + bot_config.GAMBLE_COOLDOWN - int(elapsed_time)
                    await interaction.response.send_message(f"You are on cooldown! You can gamble again <t:{unlock_time}:R>.", ephemeral=True)
                    return
            
            opposite_face = "tails" if face == "heads" else "heads"
            roll = random.random()
            if roll < 0.49995:
                winnings = int(amount * 5)
                firebase_manager.add_coins(interaction.user.id, str(interaction.user), winnings)
                embed = discord.Embed(title="You won the flip!", description=f"The coin landed on **{face}**!", color=0x57F287)
                embed.add_field(name="Bet", value=f"{amount:,}", inline=True)
                embed.add_field(name="Result", value=f"+{winnings:,} coins", inline=True)
                embed.add_field(name="Balance", value=f"{user_data['coins'] + winnings:,}", inline=True)
            elif roll <= 0.500 and roll >= 0.49995:
                embed = discord.Embed(title="JACKPOT!", description="I felt like it so yeah (So like dm <@278365147167326208> for smth idk)", color=0xFAA81A)
            else:
                firebase_manager.add_coins(interaction.user.id, str(interaction.user), -amount)
                embed = discord.Embed(title="You lost the flip!", description=f"The coin landed on **{opposite_face}**. Better luck next time!", color=0xED4245)
                embed.add_field(name="Bet", value=f"{amount:,}", inline=True)
                embed.add_field(name="Result", value=f"-{amount:,} coins", inline=True)
                embed.add_field(name="Balance", value=f"{user_data['coins'] - amount:,}", inline=True)
            embed.set_author(name="Coinflip", icon_url=self.bot.user.display_avatar.url)
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"Coinflip error: {e}")
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Gambling(bot))
