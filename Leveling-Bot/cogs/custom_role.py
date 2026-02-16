import discord
from discord.ext import commands
from discord import app_commands
from utils import firebase_manager
from datetime import datetime
from config import config as bot_config
import aiohttp

class CustomRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="customrole", description="Create your custom role (requires active Custom Role Pass)")
    async def customrole(self, ctx, name: str, color: str, icon: str = None):
        if ctx.channel.id != bot_config.COMMANDS_CHANNEL_ID:
            return
        
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_items = user_data.get('items', {})
        
        crp_data = user_items.get('custom_role_pass', {})
        crp_time = crp_data.get('timeActivated')
        
        if not crp_time:
            await ctx.send("You don't have an active **Custom Role Pass**!\nUse `!use customrole` to activate one.")
            return
        
        try:
            activated_time = datetime.fromisoformat(crp_time)
            current_time = datetime.now()
            time_diff = current_time - activated_time
            hours_passed = time_diff.total_seconds() / 3600
            duration_hours = 30 * 24
            
            if hours_passed >= duration_hours:
                await ctx.send("Your **Custom Role Pass** has expired!\nUse `!use customrole` to activate a new one.")
                return
        except:
            await ctx.send("Error checking your Custom Role Pass status. Message <@278365147167326208>")
            return
        
        color = color.strip().replace('#', '')
        
        if len(color) != 6:
            await ctx.send("Invalid color format! Use hex format like `#FF5733` or `FF5733`")
            return
        
        try:
            color_int = int(color, 16)
            discord_color = discord.Color(color_int)
        except ValueError:
            await ctx.send("Invalid color! Make sure to use a valid hex color code.")
            return
        
        if len(name) > 100:
            await ctx.send("Role name is too long! Maximum 100 characters.")
            return
        
        if len(name) < 2:
            await ctx.send("Role name is too short! Minimum 2 characters.")
            return
        
        existing_role = None
        stored_role_id = crp_data.get('roleId')
        
        if stored_role_id:
            existing_role = ctx.guild.get_role(stored_role_id)
        
        icon_bytes = None
        display_icon = None
        if icon:
            if icon.startswith('http://') or icon.startswith('https://'):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(icon) as resp:
                            if resp.status == 200:
                                icon_bytes = await resp.read()
                                
                                if len(icon_bytes) > 256 * 1024:
                                    await ctx.send("Image is too large! Maximum size is 256KB.")
                                    return
                                
                                display_icon = "Custom Image"
                            else:
                                await ctx.send(f"Failed to download icon image! Status: {resp.status}")
                                return
                except Exception as e:
                    await ctx.send(f"Error downloading icon: {e}")
                    return
            else:
                display_icon = icon
        
        try:
            if existing_role:
                edit_kwargs = {
                    "name": name,
                    "color": discord_color
                }
                
                if icon_bytes:
                    edit_kwargs["icon"] = icon_bytes
                elif icon and not icon.startswith('http'):
                    edit_kwargs["unicode_emoji"] = icon
                
                await existing_role.edit(**edit_kwargs)
                
                await existing_role.edit(position=10)

                if existing_role not in ctx.author.roles:
                    await ctx.author.add_roles(existing_role)
                
                action = "updated"
                role_id = existing_role.id
            else:
                role_kwargs = {
                    "name": name,
                    "color": discord_color,
                    "reason": f"Custom role created by {ctx.author} using Custom Role Pass"
                }
                
                if icon_bytes:
                    role_kwargs["icon"] = icon_bytes
                elif icon and not icon.startswith('http'):
                    role_kwargs["unicode_emoji"] = icon
                
                new_role = await ctx.guild.create_role(**role_kwargs)
                await ctx.author.add_roles(new_role)
                action = "created"
                role_id = new_role.id
            
            firebase_manager.set_custom_role_id(ctx.author.id, role_id)
            
            embed = discord.Embed(
                title=f"Custom Role {action.capitalize()}!",
                description=f"Your custom role **{name}** has been {action}!",
                color=discord_color
            )
            embed.add_field(name="Role Name", value=name, inline=True)
            embed.add_field(name="Color", value=f"#{color.upper()}", inline=True)
            if display_icon:
                embed.add_field(name="Icon", value=display_icon, inline=True)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to create/edit roles! Please contact <@270134285061893120>.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to create role: {e}")

async def setup(bot):
    await bot.add_cog(CustomRoles(bot))