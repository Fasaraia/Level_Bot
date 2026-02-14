import discord
from discord.ext import commands
from discord import app_commands
from utils import firebase_manager
from config import config as bot_config

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def normalize_role_name(self, role_input):
        role_map = {
            'red': 'Red',
            'orange': 'Orange',
            'teal': 'Teal',
            'blue': 'Blue',
            'purple': 'Purple',
            'black': 'Black',
            'other_role_1': 'other_role_1',
            'otherrole1': 'other_role_1',
            'special1': 'other_role_1',
            'other_role_2': 'other_role_2',
            'otherrole2': 'other_role_2',
            'special2': 'other_role_2',
        }
        return role_map.get(role_input.lower().strip(), None)
    
    def normalize_booster_name(self, booster_input):
        booster_map = {
            'tiny_booster': 'tiny_booster',
            'tiny': 'tiny_booster',
            'booster1': 'tiny_booster',
            'small_booster': 'small_booster',
            'small': 'small_booster',
            'booster2': 'small_booster',
            'medium_booster': 'medium_booster',
            'medium': 'medium_booster',
            'booster3': 'medium_booster',
            'large_booster': 'large_booster',
            'large': 'large_booster',
            'booster4': 'large_booster',
        }
        return booster_map.get(booster_input.lower().strip(), None)
    
    def get_role_price(self, role_name):
        prices = {
            'Red': 1000,
            'Orange': 1000,
            'Teal': 1000,
            'Blue': 1000,
            'Purple': 1000,
            'Black': 1000,
            'other_role_1': 5000,
            'other_role_2': 5000,
        }
        return prices.get(role_name, 0)
    
    def get_role_display_name(self, role_name):
        if role_name.startswith('other_role_'):
            return f"Special Role {role_name.split('_')[-1]}"
        return role_name.capitalize()
    
    def get_booster_info(self, booster_name):
        booster_data = {
            'tiny_booster': {'name': 'Tiny Booster | 1.1x XP Booster', 'price': 1440, 'multiplier': '1.1x', 'multiplier_value': 1.1, 'duration': 4320},
            'small_booster': {'name': 'Small Booster | 1.2x XP Booster', 'price': 2160, 'multiplier': '1.2x', 'multiplier_value': 1.2, 'duration': 4320},
            'medium_booster': {'name': 'Medium Booster | 1.3x XP Booster', 'price': 3240, 'multiplier': '1.3x', 'multiplier_value': 1.3, 'duration': 4320},
            'large_booster': {'name': 'Large Booster | 1.5x XP Booster', 'price': 4320, 'multiplier': '1.5x', 'multiplier_value': 1.5, 'duration': 4320},
        }
        return booster_data.get(booster_name, {})
    
    @commands.hybrid_command(name="shop", description="View the role shop")
    async def shop(self, ctx):
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_roles = user_data.get('roles', {})
        user_items = user_data.get('items', {})
        user_xp = user_data['currentXP']  # Changed from totalXP to currentXP
        
        embed = discord.Embed(
            title="🛒 Shop",
            description=f"Your XP: **{user_xp:,}**\n\nUse `/buy <item_name>` to purchase\nUse `/equip <role_name>` to equip roles\nUse `/use <booster>` to activate boosters",
            color=discord.Color.blue()
        )
        
        # Color Roles
        color_roles = []
        for role_name in ['Red', 'Orange', 'Teal', 'Blue', 'Purple', 'Black']:
            owned = user_roles.get(role_name, False)
            price = self.get_role_price(role_name)
            status = "✅ Owned" if owned else f"{price:,} XP"
            
            # Get the Discord role to show it (without ping)
            discord_role_id = bot_config.COLOUR_ROLES.get(role_name)
            if discord_role_id:
                discord_role = ctx.guild.get_role(discord_role_id)
                if discord_role:
                    color_roles.append(f"{discord_role.mention} **{role_name}** - {status}")
                else:
                    color_roles.append(f"**{role_name}** - {status}")
            else:
                color_roles.append(f"**{role_name}** - {status}")
        
        embed.add_field(
            name="🎨 Color Roles",
            value="\n".join(color_roles),
            inline=False
        )
        
        # Special Roles
        special_roles = []
        for role_name in ['other_role_1', 'other_role_2']:
            owned = user_roles.get(role_name, False)
            price = self.get_role_price(role_name)
            display_name = self.get_role_display_name(role_name)
            status = "✅ Owned" if owned else f"{price:,} XP"
            special_roles.append(f"**{display_name}** - {status}")
        
        embed.add_field(
            name="⭐ Special Roles",
            value="\n".join(special_roles),
            inline=False
        )
        
        # XP Boosters (large_booster excluded from shop)
        boosters = []
        for booster_name in ['tiny_booster', 'small_booster', 'medium_booster']:
            info = self.get_booster_info(booster_name)
            amount = user_items.get(booster_name, {}).get('amount', 0)
            boosters.append(f"**{info['name']}** ({info['multiplier']}) - {info['price']:,} XP | Owned: {amount}")
        
        embed.add_field(
            name="⚡ XP Boosters",
            value="\n".join(boosters),
            inline=False
        )
        
        await ctx.send(embed=embed, allowed_mentions=discord.AllowedMentions(roles=False))
    
    @commands.hybrid_command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item="The item to buy (e.g., Red, Blue, tiny, small, medium, large)")
    async def buy(self, ctx, item: str):
        # Try to normalize as role first
        role = self.normalize_role_name(item)
        booster = self.normalize_booster_name(item)
        
        if role:
            await self._buy_role(ctx, role)
        elif booster:
            await self._buy_booster(ctx, booster)
        else:
            await ctx.send(f"Item doesn't exist or isn't purchasable in the shop!", ephemeral=True)
    
    async def _buy_role(self, ctx, role):
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_roles = user_data.get('roles', {})
        user_xp = user_data['currentXP']  # Changed from totalXP to currentXP
        
        if user_roles.get(role, False):
            await ctx.send(f"You already own the **{self.get_role_display_name(role)}** role!", ephemeral=True)
            return
        
        price = self.get_role_price(role)
        
        if user_xp < price:
            await ctx.send(f"Not enough XP! You need **{price:,} XP** but only have **{user_xp:,} XP**.", ephemeral=True)
            return
        
        firebase_manager.add_xp(ctx.author.id, str(ctx.author), -price)
        firebase_manager.set_user_role(ctx.author.id, role, True)
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You bought the **{self.get_role_display_name(role)}** role for **{price:,} XP**!\n\nUse `/equip {role}` to equip it.",
            color=discord.Color.green()
        )
        embed.add_field(name="Remaining XP", value=f"{user_xp - price:,}", inline=True)
        
        await ctx.send(embed=embed)
    
    async def _buy_booster(self, ctx, booster):
        # Prevent buying large_booster
        if booster == 'large_booster':
            await ctx.send(f"This booster is not available for purchase!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_xp = user_data['currentXP']  # Changed from totalXP to currentXP
        
        info = self.get_booster_info(booster)
        price = info['price']
        
        if user_xp < price:
            await ctx.send(f"Not enough XP! You need **{price:,} XP** but only have **{user_xp:,} XP**.", ephemeral=True)
            return
        
        firebase_manager.add_xp(ctx.author.id, str(ctx.author), -price)
        firebase_manager.add_item(ctx.author.id, booster, 1)
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You bought **{info['name']}** for **{price:,} XP**!\n\nUse `/use {booster}` to activate it.",
            color=discord.Color.green()
        )
        embed.add_field(name="Remaining XP", value=f"{user_xp - price:,}", inline=True)
        embed.add_field(name="Duration", value=f"7 days", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="inventory", aliases=["inv"], description="View your inventory")
    async def inventory(self, ctx):
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_items = user_data.get('items', {})
        
        embed = discord.Embed(
            title="🎒 Your Inventory",
            description="Your owned items and boosters",
            color=discord.Color.purple()
        )
        
        # Boosters
        booster_list = []
        for booster_name in ['tiny_booster', 'small_booster', 'medium_booster', 'large_booster']:
            info = self.get_booster_info(booster_name)
            item_data = user_items.get(booster_name, {})
            amount = item_data.get('amount', 0)
            active = item_data.get('active', 0)
            
            status = "🟢 Active" if active else f"Amount: {amount}"
            booster_list.append(f"**{info['name']}** - {status}")
        
        embed.add_field(
            name="⚡ XP Boosters",
            value="\n".join(booster_list) if booster_list else "No boosters",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="use", description="Use an XP booster")
    @app_commands.describe(booster="The booster to use (e.g., tiny, small, medium, large)")
    async def use_booster(self, ctx, booster: str):
        booster = self.normalize_booster_name(booster)
        
        if not booster:
            await ctx.send(f"Invalid booster! Use `/inventory` to see your boosters.", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_items = user_data.get('items', {})
        
        # Check if user has any active boosters
        active_boosters = firebase_manager.get_active_boosters(ctx.author.id)
        if active_boosters:
            active_names = [self.get_booster_info(b['name'])['name'] for b in active_boosters]
            await ctx.send(f"You already have an active booster: **{', '.join(active_names)}**!\nWait for it to expire before using another.", ephemeral=True)
            return
        
        # Check if user has the booster
        booster_data = user_items.get(booster, {})
        if booster_data.get('amount', 0) <= 0:
            await ctx.send(f"You don't have any **{self.get_booster_info(booster)['name']}**!\nBuy one from `/shop`.", ephemeral=True)
            return
        
        # Use the booster
        success = firebase_manager.use_item(ctx.author.id, booster)
        
        if success:
            info = self.get_booster_info(booster)
            embed = discord.Embed(
                title="⚡ Booster Activated!",
                description=f"You activated **{info['name']}**!\n\n**Multiplier:** {info['multiplier']}\n**Duration:** 7 days",
                color=discord.Color.gold()
            )
            embed.set_footer(text="You'll receive a DM when it expires!")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Failed to use booster. Please try again.", ephemeral=True)
    
    @commands.hybrid_command(name="equip", description="Equip an owned role")
    @app_commands.describe(role="The role to equip (e.g., Red, Blue, other_role_1)")
    async def equip(self, ctx, role: str):
        role = self.normalize_role_name(role)
        
        if not role:
            await ctx.send(f"Invalid role!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_roles = user_data.get('roles', {})
        
        if not user_roles.get(role, False):
            await ctx.send(f"You don't own the **{self.get_role_display_name(role)}** role! Purchase it from `/shop` first.", ephemeral=True)
            return
        
        discord_role_id = None
        if role in bot_config.COLOUR_ROLES:
            discord_role_id = bot_config.COLOUR_ROLES[role]
        elif role in bot_config.SPECIAL_ROLES:
            discord_role_id = bot_config.SPECIAL_ROLES[role]
        
        if not discord_role_id:
            await ctx.send(f"Role not configured in the bot!", ephemeral=True)
            return
        
        discord_role = ctx.guild.get_role(discord_role_id)
        if not discord_role:
            await ctx.send(f"Role not found in the server!", ephemeral=True)
            return
        
        if discord_role in ctx.author.roles:
            await ctx.send(f"You already have the **{self.get_role_display_name(role)}** role equipped!", ephemeral=True)
            return
        
        try:
            await ctx.author.add_roles(discord_role)
            
            embed = discord.Embed(
                title="✅ Role Equipped!",
                description=f"You equipped the **{self.get_role_display_name(role)}** role!\nTo unequip use `/unequip {role}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error adding Discord role: {e}")
            await ctx.send(f"Failed to equip role. Please contact @sh.or", ephemeral=True)

    @commands.hybrid_command(name="unequip", description="Unequip an owned role")
    @app_commands.describe(role="The role to unequip (e.g., Red, Blue, other_role_1)")
    async def unequip(self, ctx, role: str):
        role = self.normalize_role_name(role)
        
        if not role:
            await ctx.send(f"Invalid role!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_roles = user_data.get('roles', {})
        
        if not user_roles.get(role, False):
            await ctx.send(f"You don't own the **{self.get_role_display_name(role)}** role! Purchase it from `/shop` first.", ephemeral=True)
            return
        
        discord_role_id = None
        if role in bot_config.COLOUR_ROLES:
            discord_role_id = bot_config.COLOUR_ROLES[role]
        elif role in bot_config.SPECIAL_ROLES:
            discord_role_id = bot_config.SPECIAL_ROLES[role]
        
        if not discord_role_id:
            await ctx.send(f"Role not configured in the bot!", ephemeral=True)
            return
        
        discord_role = ctx.guild.get_role(discord_role_id)
        if not discord_role:
            await ctx.send(f"Role not found in the server!", ephemeral=True)
            return
        
        if discord_role not in ctx.author.roles:
            await ctx.send(f"You don't have the **{self.get_role_display_name(role)}** role equipped!", ephemeral=True)
            return
        
        try:
            await ctx.author.remove_roles(discord_role)
            
            embed = discord.Embed(
                title="✅ Role Unequipped!",
                description=f"You unequipped the **{self.get_role_display_name(role)}** role!\nTo equip use `/equip {role}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error removing Discord role: {e}")
            await ctx.send(f"Failed to unequip role. Please contact @sh.or", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Shop(bot))