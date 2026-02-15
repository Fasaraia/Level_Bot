import discord
from discord.ext import commands
from discord import app_commands
from utils import firebase_manager
from config import config as bot_config
from datetime import datetime, timedelta

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
            'customrole1': 'Custom Role 1',
            'custom1': 'Custom Role 1',
            'cr1': 'Custom Role 1',
            'customrole2': 'Custom Role 2',
            'custom2': 'Custom Role 2',
            'cr2': 'Custom Role 2',
            'specialrole1': 'Special Role 1',
            'special1': 'Special Role 1',
            'sr1': 'Special Role 1',
            'specialrole2': 'Special Role 2',
            'special2': 'Special Role 2',
            'sr2': 'Special Role 2',
        }
        return role_map.get(role_input.lower().strip().replace(' ', ''), None)
    
    def normalize_item_name(self, item_input):
        """Normalize both booster and custom role pass names"""
        item_input_clean = item_input.lower().strip()
        
        # Check boosters first
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
        
        if item_input_clean in booster_map:
            return ('booster', booster_map[item_input_clean])
        
        # Check custom role pass
        crp_aliases = ['custom_role_pass', 'customrolepass', 'customrole', 'custompass', 'rolepass', 'custom roll pass']
        if item_input_clean in crp_aliases:
            return ('custom_role_pass', 'custom_role_pass')
        
        return (None, None)
    
    def get_role_price(self, role_name):
        prices = {
            'Red': 1000,
            'Orange': 1000,
            'Teal': 1000,
            'Blue': 1000,
            'Purple': 1000,
            'Black': 1000,
            'Custom Role 1': 5000,
            'Custom Role 2': 5000,
            'Special Role 1': 7500,
            'Special Role 2': 7500,
        }
        return prices.get(role_name, 0)
    
    def get_role_display_name(self, role_name):
        return role_name
    
    def get_booster_info(self, booster_name):
        booster_data = {
            'tiny_booster': {'name': 'Tiny Booster | 1.1x XP Booster', 'price': 1440, 'multiplier': '1.1x', 'multiplier_value': 1.1, 'duration': 4320},
            'small_booster': {'name': 'Small Booster | 1.2x XP Booster', 'price': 2160, 'multiplier': '1.2x', 'multiplier_value': 1.2, 'duration': 4320},
            'medium_booster': {'name': 'Medium Booster | 1.3x XP Booster', 'price': 3240, 'multiplier': '1.3x', 'multiplier_value': 1.3, 'duration': 4320},
            'large_booster': {'name': 'Large Booster | 1.5x XP Booster', 'price': 4320, 'multiplier': '1.5x', 'multiplier_value': 1.5, 'duration': 4320},
        }
        return booster_data.get(booster_name, {})
    
    def get_db_role_key(self, role_name):
        """Map display names to database keys"""
        role_key_map = {
            'Red': 'Red',
            'Orange': 'Orange',
            'Teal': 'Teal',
            'Blue': 'Blue',
            'Purple': 'Purple',
            'Black': 'Black',
            'Custom Role 1': 'Custom Role 1',
            'Custom Role 2': 'Custom Role 2',
            'Special Role 1': 'Special Role 1',
            'Special Role 2': 'Special Role 2',
        }
        return role_key_map.get(role_name, role_name)
    
    @commands.hybrid_command(name="shop", description="View the role shop")
    async def shop(self, ctx):
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_roles = user_data.get('roles', {})
        user_items = user_data.get('items', {})
        user_xp = user_data['currentXP']
        
        embed = discord.Embed(
            title="Shop",
            description=f"Your XP: **{user_xp:,}**\n\nUse `/buy <item_name>` to purchase\nUse `/equip <role_name>` to equip roles\nUse `/use <booster>` to activate boosters",
            color=discord.Color.blue()
        )
        
        # Color Roles
        color_roles = []
        for role_name in ['Red', 'Orange', 'Teal', 'Blue', 'Purple', 'Black']:
            db_key = self.get_db_role_key(role_name)
            owned = user_roles.get(db_key, False)
            price = self.get_role_price(role_name)
            status = "✅ Owned" if owned else f"{price:,} XP"
            
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
        for role_name in ['Custom Role 1', 'Custom Role 2']:
            db_key = self.get_db_role_key(role_name)
            owned = user_roles.get(db_key, False)
            price = self.get_role_price(role_name)
            status = "✅ Owned" if owned else f"{price:,} XP"
            
            discord_role_id = bot_config.SPECIAL_ROLES.get(role_name)
            if discord_role_id:
                discord_role = ctx.guild.get_role(discord_role_id)
                if discord_role:
                    special_roles.append(f"{discord_role.mention} **{role_name}** - {status}")
                else:
                    special_roles.append(f"**{role_name}** - {status}")
            else: special_roles.append(f"**{role_name}** - {status}")
        
        embed.add_field(
            name="⭐ Special Roles",
            value="\n".join(special_roles),
            inline=False
        )
        
        # XP Boosters
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
    @app_commands.describe(item="The item to buy (e.g., Red, Blue, tiny, small, medium)")
    async def buy(self, ctx, item: str):
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
        user_xp = user_data['currentXP']
        
        db_key = self.get_db_role_key(role)

        if role == 'Special Role 1' or role == 'Special Role 2':
            await ctx.send(f"This special role is not available for purchase!", ephemeral=True)
            return
        
        if user_roles.get(db_key, False):
            await ctx.send(f"You already own the **{role}** role!", ephemeral=True)
            return
        
        price = self.get_role_price(role)
        
        if user_xp < price:
            await ctx.send(f"Not enough XP! You need **{price:,} XP** but only have **{user_xp:,} XP**.", ephemeral=True)
            return
        
        firebase_manager.add_xp(ctx.author.id, str(ctx.author), -price)
        firebase_manager.set_user_role(ctx.author.id, db_key, True)
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You bought the **{role}** role for **{price:,} XP**!\n\nUse `/equip {role}` to equip it.",
            color=discord.Color.green()
        )
        embed.add_field(name="Remaining XP", value=f"{user_xp - price:,}", inline=True)
        
        await ctx.send(embed=embed)
    
    async def _buy_booster(self, ctx, booster):
        if booster == 'large_booster':
            await ctx.send(f"This booster is not available for purchase!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_xp = user_data['currentXP']
        
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
        embed.add_field(name="Duration", value=f"3 days", inline=True)
        
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
        
        # XP Boosters
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
            value="\n".join(booster_list),
            inline=False
        )
        
        # Custom Role Pass
        crp_data = user_items.get('custom_role_pass', {})
        crp_amount = crp_data.get('amount', 0)
        crp_time = crp_data.get('timeActivated')
        
        if crp_time:
            try:
                activated_time = datetime.fromisoformat(crp_time)
                current_time = datetime.now()
                
                # Calculate time passed (in hours)
                time_diff = current_time - activated_time
                hours_passed = time_diff.total_seconds() / 3600
                
                # 30 day duration for custom role pass
                duration_hours = 30 * 24  # 30 days
                hours_remaining = duration_hours - hours_passed
                
                if hours_remaining > 0:
                    days_remaining = int(hours_remaining // 24)
                    hours_only = int(hours_remaining % 24)
                    
                    if days_remaining > 0:
                        time_left = f"{days_remaining}d {hours_only}h remaining"
                    else:
                        time_left = f"{hours_only}h remaining"
                    
                    crp_status = f"Amount: {crp_amount} | {time_left}"
                else:
                    crp_status = f"Amount: {crp_amount} | Not activated / Expired"
            except:
                crp_status = f"Amount: {crp_amount}"
        else:
            crp_status = f"Amount: {crp_amount} | Not activated"
        
        embed.add_field(
            name="🎨 Custom Role Pass",
            value=f"**Custom Role Pass** - {crp_status}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="use", description="Use an item (booster or custom role pass)")
    @app_commands.describe(item="The item to use (e.g., tiny, small, medium, large, customrole)")
    async def use_item(self, ctx, item: str):
        item_type, item_name = self.normalize_item_name(item)
        
        if not item_type:
            await ctx.send(f"Invalid item! Use `/inventory` to see your items.", ephemeral=True)
            return
        
        if item_type == 'booster':
            await self._use_booster(ctx, item_name)
        elif item_type == 'custom_role_pass':
            await self._use_custom_role_pass(ctx)

    async def _use_booster(self, ctx, booster):
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_items = user_data.get('items', {})
        
        active_boosters = firebase_manager.get_active_boosters(ctx.author.id)
        if active_boosters:
            active_names = [self.get_booster_info(b['name'])['name'] for b in active_boosters]
            await ctx.send(f"You already have an active booster: **{', '.join(active_names)}**!\nWait for it to expire before using another.", ephemeral=True)
            return
        
        booster_data = user_items.get(booster, {})
        if booster_data.get('amount', 0) <= 0:
            await ctx.send(f"You don't have any **{self.get_booster_info(booster)['name']}**!\nBuy one from `/shop`.", ephemeral=True)
            return
        
        success = firebase_manager.use_item(ctx.author.id, booster)
        
        if success:
            info = self.get_booster_info(booster)
            embed = discord.Embed(
                title="⚡ Booster Activated!",
                description=f"You activated **{info['name']}**!\n\n**Multiplier:** {info['multiplier']}\n**Duration:** 3 days",
                color=discord.Color.gold()
            )
            embed.set_footer(text="You'll receive a DM when it expires!")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Failed to use booster. Please try again.", ephemeral=True)

    async def _use_custom_role_pass(self, ctx):
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_items = user_data.get('items', {})
        
        crp_data = user_items.get('custom_role_pass', {})
        crp_amount = crp_data.get('amount', 0)
        crp_time = crp_data.get('timeActivated')
        
        # Check if user has any custom role passes
        if crp_amount <= 0:
            await ctx.send("You don't have any **Custom Role Passes**!", ephemeral=True)
            return
        
        # Check if there's already an active pass
        if crp_time:
            try:
                activated_time = datetime.fromisoformat(crp_time)
                current_time = datetime.now()
                time_diff = current_time - activated_time
                hours_passed = time_diff.total_seconds() / 3600
                duration_hours = 30 * 24  # 30 days
                
                if hours_passed < duration_hours:
                    hours_remaining = duration_hours - hours_passed
                    days_remaining = int(hours_remaining // 24)
                    hours_only = int(hours_remaining % 24)
                    
                    await ctx.send(
                        f"You already have an active **Custom Role Pass**!\n"
                        f"Time remaining: {days_remaining}d {hours_only}h",
                        ephemeral=True
                    )
                    return
            except:
                pass
        
        # Use the custom role pass
        user_ref = firebase_manager.db_ref.child('users').child(str(ctx.author.id)).child('items').child('custom_role_pass')
        user_ref.update({
            'amount': crp_amount - 1,
            'timeActivated': datetime.now().isoformat()
        })
        
        embed = discord.Embed(
            title="✅ Custom Role Pass Activated!",
            description=f"You activated a **Custom Role Pass**!\n\n**Duration:** 30 days\n**Remaining passes:** {crp_amount - 1}",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Contact @sh.or for gradient colours (If available)!")
        
        await ctx.send(embed=embed)


    @commands.hybrid_command(name="equip", description="Equip an owned role")
    @app_commands.describe(role="The role to equip")
    async def equip(self, ctx, role: str):
        role = self.normalize_role_name(role)
        
        if not role:
            await ctx.send(f"Invalid role!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_roles = user_data.get('roles', {})
        
        db_key = self.get_db_role_key(role)
        
        if not user_roles.get(db_key, False):
            await ctx.send(f"You don't own the **{role}** role! Purchase it from `/shop` first.", ephemeral=True)
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
            await ctx.send(f"You already have the **{role}** role equipped!", ephemeral=True)
            return
        
        try:
            await ctx.author.add_roles(discord_role)
            
            embed = discord.Embed(
                title="✅ Role Equipped!",
                description=f"You equipped the **{role}** role!\nTo unequip use `/unequip {role}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error adding Discord role: {e}")
            await ctx.send(f"Failed to equip role. Please contact @sh.or", ephemeral=True)

    @commands.hybrid_command(name="unequip", description="Unequip an owned role")
    @app_commands.describe(role="The role to unequip (e.g., Red, Blue, Custom1, Special1)")
    async def unequip(self, ctx, role: str):
        role = self.normalize_role_name(role)
        
        if not role:
            await ctx.send(f"Invalid role!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(ctx.author.id)
        user_roles = user_data.get('roles', {})
        
        db_key = self.get_db_role_key(role)
        
        if not user_roles.get(db_key, False):
            await ctx.send(f"You don't own the **{role}** role! Purchase it from `/shop` first.", ephemeral=True)
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
            await ctx.send(f"You don't have the **{role}** role equipped!", ephemeral=True)
            return
        
        try:
            await ctx.author.remove_roles(discord_role)
            
            embed = discord.Embed(
                title="✅ Role Unequipped!",
                description=f"You unequipped the **{role}** role!\nTo equip use `/equip {role}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error removing Discord role: {e}")
            await ctx.send(f"Failed to unequip role. Please contact @sh.or", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Shop(bot))