import discord
from discord.ext import commands
from discord import app_commands
from utils import firebase_manager
from datetime import datetime
import aiohttp

class CustomRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="customrole", description="Create your custom role (requires active Custom Role Pass)")
    @app_commands.describe(
        name="The name of your custom role",
        color="The color in hex format (e.g., #FF5733 or FF5733)",
        icon="Image icon (URL or emoji) for your role (optional)"
    )
    async def customrole(self, ctx, name: str, color: str, icon: str = None):
        # Check if user has an active custom role pass
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_items = user_data.get('items', {})
        
        crp_data = user_items.get('custom_role_pass', {})
        crp_time = crp_data.get('timeActivated')
        
        if not crp_time:
            await ctx.send("You don't have an active **Custom Role Pass**!\nUse `/use crp` to activate one.", ephemeral=True)
            return
        
        # Check if pass is still valid
        try:
            activated_time = datetime.fromisoformat(crp_time)
            current_time = datetime.now()
            time_diff = current_time - activated_time
            hours_passed = time_diff.total_seconds() / 3600
            duration_hours = 30 * 24  # 30 days
            
            if hours_passed >= duration_hours:
                await ctx.send("Your **Custom Role Pass** has expired!\nUse `/use crp` to activate a new one.", ephemeral=True)
                return
        except:
            await ctx.send("Error checking your Custom Role Pass status.", ephemeral=True)
            return
        
        # Validate and parse color
        color = color.strip().replace('#', '')
        
        if len(color) != 6:
            await ctx.send("Invalid color format! Use hex format like `#FF5733` or `FF5733`", ephemeral=True)
            return
        
        try:
            color_int = int(color, 16)
            discord_color = discord.Color(color_int)
        except ValueError:
            await ctx.send("Invalid color! Make sure to use a valid hex color code.", ephemeral=True)
            return
        
        # Validate role name
        if len(name) > 100:
            await ctx.send("Role name is too long! Maximum 100 characters.", ephemeral=True)
            return
        
        if len(name) < 2:
            await ctx.send("Role name is too short! Minimum 2 characters.", ephemeral=True)
            return
        
        # Check if user already has a custom role stored
        existing_role = None
        stored_role_id = crp_data.get('roleId')
        
        if stored_role_id:
            existing_role = ctx.guild.get_role(stored_role_id)
        
        # Process icon if provided
        icon_bytes = None
        display_icon = None
        if icon:
            # Check if it's a URL (for custom icon image)
            if icon.startswith('http://') or icon.startswith('https://'):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(icon) as resp:
                            if resp.status == 200:
                                icon_bytes = await resp.read()
                                
                                display_icon = "Custom Image"
                            else:
                                await ctx.send(f"Failed to download icon image! Status: {resp.status}", ephemeral=True)
                                return
                except Exception as e:
                    await ctx.send(f"Error downloading icon: {e}", ephemeral=True)
                    return
            else:
                # It's an emoji (unicode or custom)
                display_icon = icon
        
        # Create or update the role
        try:
            if existing_role:
                # Update existing role
                if icon_bytes:
                    await existing_role.edit(name=name, color=discord_color, icon=icon_bytes)
                elif icon and not icon.startswith('http'):
                    await existing_role.edit(name=name, color=discord_color, unicode_emoji=icon)
                else:
                    await existing_role.edit(name=name, color=discord_color)
                
                # Make sure user has the role
                if existing_role not in ctx.author.roles:
                    await ctx.author.add_roles(existing_role)
                
                action = "updated"
                role_id = existing_role.id
            else:
                # Create new role
                role_kwargs = {
                    "name": name,
                    "color": discord_color,
                    "reason": f"Custom role created by {ctx.author} using Custom Role Pass"
                }
                
                # Add icon if provided
                if icon_bytes:
                    role_kwargs["icon"] = icon_bytes
                elif icon and not icon.startswith('http'):
                    role_kwargs["unicode_emoji"] = icon
                
                new_role = await ctx.guild.create_role(**role_kwargs)
                
                # Add role to user
                await ctx.author.add_roles(new_role)
                action = "created"
                role_id = new_role.id
            
            # Store role ID in database
            firebase_manager.set_custom_role_id(ctx.author.id, role_id)
            
            embed = discord.Embed(
                title=f"✅ Custom Role {action.capitalize()}!",
                description=f"Your custom role **{name}** has been {action}!",
                color=discord_color
            )
            embed.add_field(name="Role Name", value=name, inline=True)
            embed.add_field(name="Color", value=f"#{color.upper()}", inline=True)
            if display_icon:
                embed.add_field(name="Icon", value=display_icon, inline=True)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to create/edit roles! Please contact an administrator.", ephemeral=True)
        except discord.HTTPException as e:
            await ctx.send(f"Failed to create role: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CustomRoles(bot))