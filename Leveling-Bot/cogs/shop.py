import discord
from discord.ext import commands
from discord import app_commands
from utils import firebase_manager
from config import config as bot_config
from datetime import datetime, timedelta

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #=============================#
    #  Item and Role Maps / Info  #
    #=============================#
    
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
        }
        return role_map.get(role_input.lower().strip().replace(' ', ''), None)
    
    def normalize_item_name(self, item_input):
        """Normalize both booster and custom role pass names"""
        item_input_clean = item_input.lower().strip()
        
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
    
    #============================#
    #       Buy Role/Booster     #
    #============================#

    async def _buy_role(self, interaction, role):
        user_data = firebase_manager.get_user_data(interaction.user.id)
        user_roles = user_data.get('roles', {})
        user_xp = user_data['currentXP']
        
        db_key = self.get_db_role_key(role)

        if role == 'Special Role 1' or role == 'Special Role 2':
            await interaction.response.send_message("This special role is not available for purchase!", ephemeral=True)
            return
        
        if user_roles.get(db_key, False):
            await interaction.response.send_message(f"You already own the **{role}** role!", ephemeral=True)
            return
        
        price = self.get_role_price(role)
        
        if user_xp < price:
            await interaction.response.send_message(f"Not enough XP! You need **{price:,} XP** but only have **{user_xp:,} XP**.", ephemeral=True)
            return
        
        firebase_manager.add_xp(interaction.user.id, str(interaction.user), -price)
        firebase_manager.set_user_role(interaction.user.id, db_key, True)
        
        embed = discord.Embed(
            title="Purchase Successful!",
            description=f"You bought the **{role}** role for **{price:,} XP**!\n\nUse `/equip {role}` to equip it.",
            color=discord.Color.green()
        )
        embed.add_field(name="Remaining XP", value=f"{user_xp - price:,}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    async def _buy_booster(self, interaction, booster):
        if booster == 'large_booster':
            await interaction.response.send_message("This booster is not available for purchase!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(interaction.user.id)
        user_xp = user_data['currentXP']
        
        info = self.get_booster_info(booster)
        price = info['price']
        
        if user_xp < price:
            await interaction.response.send_message(f"Not enough XP! You need **{price:,} XP** but only have **{user_xp:,} XP**.", ephemeral=True)
            return
        
        firebase_manager.add_xp(interaction.user.id, str(interaction.user), -price)
        firebase_manager.add_item(interaction.user.id, booster, 1)
        
        embed = discord.Embed(
            title="Purchase Successful!",
            description=f"You bought **{info['name']}** for **{price:,} XP**!\n\nUse `/use {booster}` to activate it.",
            color=discord.Color.green()
        )
        embed.add_field(name="Remaining XP", value=f"{user_xp - price:,}", inline=True)
        embed.add_field(name="Duration", value="3 days", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    #============================#
    #         Use Items          #
    #============================#

    async def _use_booster(self, interaction, booster):
        user_data = firebase_manager.get_user_data(interaction.user.id)
        user_items = user_data.get('items', {})
        
        active_boosters = firebase_manager.get_active_boosters(interaction.user.id)
        if active_boosters:
            active_names = [self.get_booster_info(b['name'])['name'] for b in active_boosters]
            await interaction.response.send_message(f"You already have an active booster: **{', '.join(active_names)}**!\nWait for it to expire before using another.", ephemeral=True)
            return
        
        booster_data = user_items.get(booster, {})
        if booster_data.get('amount', 0) <= 0:
            await interaction.response.send_message(f"You don't have any **{self.get_booster_info(booster)['name']}**!\nBuy one from `/shop`.", ephemeral=True)
            return
        
        success = firebase_manager.use_item(interaction.user.id, booster)
        
        if success:
            info = self.get_booster_info(booster)
            embed = discord.Embed(
                title="Booster Activated!",
                description=f"You activated **{info['name']}**!\n\n**Multiplier:** {info['multiplier']}\n**Duration:** 3 days",
                color=discord.Color.gold()
            )
            embed.set_footer(text="You'll receive a DM when it expires!")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Failed to use booster. Please try again.", ephemeral=True)

    async def _use_custom_role_pass(self, interaction):
        user_data = firebase_manager.get_user_data(interaction.user.id)
        user_items = user_data.get('items', {})
        
        crp_data = user_items.get('custom_role_pass', {})
        crp_amount = crp_data.get('amount', 0)
        crp_time = crp_data.get('timeActivated')
        
        if crp_amount <= 0:
            await interaction.response.send_message("You don't have any **Custom Role Passes**!", ephemeral=True)
            return
        
        if crp_time:
            try:
                activated_time = datetime.fromisoformat(crp_time)
                current_time = datetime.now()
                time_diff = current_time - activated_time
                hours_passed = time_diff.total_seconds() / 3600
                duration_hours = 30 * 24
                
                if hours_passed < duration_hours:
                    hours_remaining = duration_hours - hours_passed
                    days_remaining = int(hours_remaining // 24)
                    hours_only = int(hours_remaining % 24)
                    
                    await interaction.response.send_message(
                        f"You already have an active **Custom Role Pass**!\n"
                        f"Time remaining: {days_remaining}d {hours_only}h",
                        ephemeral=True
                    )
                    return
            except:
                pass
        
        user_ref = firebase_manager.db_ref.child('users').child(str(interaction.user.id)).child('items').child('custom_role_pass')
        user_ref.update({
            'amount': crp_amount - 1,
            'timeActivated': datetime.now().isoformat()
        })
        
        embed = discord.Embed(
            title="Custom Role Pass Activated!",
            description=f"You activated a **Custom Role Pass**!\n\n**Duration:** 30 days\n\n-# Message <@278365147167326208> for gradient colours (If available)!",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed)

    #============================#
    #          Commands          #
    #============================#

    @app_commands.command(name="shop", description="View the item shop")
    async def shop(self, interaction: discord.Interaction):
        if interaction.channel.id != bot_config.COMMANDS_CHANNEL_ID:
            return
        
        user_data = firebase_manager.get_user_data(interaction.user.id)
        user_roles = user_data.get('roles', {})
        user_items = user_data.get('items', {})
        user_xp = user_data['currentXP']
        
        embed = discord.Embed(
            title="Shop",
            description=f"Your XP: **{user_xp:,}**\n\nUse `/buy <item_name>` to purchase\nUse `/equip <role_name>` to equip roles\nUse `/use <booster>` to activate boosters",
            color=discord.Color.blue()
        )
        
        color_roles = []
        for role_name in ['Red', 'Orange', 'Teal', 'Blue', 'Purple', 'Black']:
            db_key = self.get_db_role_key(role_name)
            owned = user_roles.get(db_key, False)
            price = self.get_role_price(role_name)
            status = "🟢 **Owned**" if owned else f"{price:,} XP"
            
            discord_role_id = bot_config.COLOUR_ROLES.get(role_name)
            if discord_role_id:
                discord_role = interaction.guild.get_role(discord_role_id)
                if discord_role:
                    color_roles.append(f"{discord_role.mention} **{role_name}** - {status}")
                else:
                    color_roles.append(f"**{role_name}** - {status}")
            else:
                color_roles.append(f"**{role_name}** - {status}")
        
        embed.add_field(
            name="Color Roles",
            value="\n".join(color_roles),
            inline=False
        )
        
        special_roles = []
        for role_name in ['Custom Role 1', 'Custom Role 2']:
            db_key = self.get_db_role_key(role_name)
            owned = user_roles.get(db_key, False)
            price = self.get_role_price(role_name)
            status = "**🟢 Owned**" if owned else f"{price:,} XP"
            
            discord_role_id = bot_config.SPECIAL_ROLES.get(role_name)
            if discord_role_id:
                discord_role = interaction.guild.get_role(discord_role_id)
                if discord_role:
                    special_roles.append(f"{discord_role.mention} **{role_name}** - {status}")
                else:
                    special_roles.append(f"**{role_name}** - {status}")
            else:
                special_roles.append(f"**{role_name}** - {status}")
        
        embed.add_field(
            name="Special Roles",
            value="\n".join(special_roles),
            inline=False
        )
        
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
        
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=False))
    
    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item="The item to buy (e.g., Red, Blue, tiny, small, medium)")
    async def buy(self, interaction: discord.Interaction, item: str):
        if interaction.channel.id != bot_config.COMMANDS_CHANNEL_ID:
            return
        
        role = self.normalize_role_name(item)
        item_type, booster = self.normalize_item_name(item)
        
        if role:
            await self._buy_role(interaction, role)
        elif item_type == 'booster':
            await self._buy_booster(interaction, booster)
        else:
            await interaction.response.send_message("Item doesn't exist or isn't purchasable in the shop!", ephemeral=True)

    @app_commands.command(name="inventory", description="View your inventory")
    async def inventory(self, interaction: discord.Interaction):
        if interaction.channel.id != bot_config.COMMANDS_CHANNEL_ID:
            return
        
        user_data = firebase_manager.get_user_data(interaction.user.id)
        user_items = user_data.get('items', {})

        embed = discord.Embed(
            title="Your Inventory",
            description="Your owned items and boosters\nView owned roles from `/shop`",
            color=discord.Color.purple()
        )
        
        booster_list = []
        for booster_name in ['tiny_booster', 'small_booster', 'medium_booster', 'large_booster']:
            info = self.get_booster_info(booster_name)
            item_data = user_items.get(booster_name, {})
            amount = item_data.get('amount', 0)
            active = item_data.get('active', 0)
            time_activated = item_data.get('timeActivated')
            
            if active and time_activated:
                try:
                    activated_time = datetime.fromisoformat(time_activated)
                    current_time = datetime.now()
                    time_diff = current_time - activated_time
                    hours_passed = time_diff.total_seconds() / 3600
                    
                    duration_hours = 3 * 24
                    hours_remaining = duration_hours - hours_passed
                    
                    if hours_remaining > 0:
                        days_remaining = int(hours_remaining // 24)
                        hours_only = int(hours_remaining % 24)
                        
                        if days_remaining > 0:
                            time_left = f"{days_remaining}d {hours_only}h remaining"
                        else:
                            time_left = f"{hours_only}h remaining"
                        
                        status = f"Active | {time_left}"
                    else:
                        status = f"Amount: {amount}"
                except:
                    status = f"Amount: {amount}"
            else:
                status = f"Amount: {amount}"
            
            booster_list.append(f"**{info['name']}** - {status}")
        
        embed.add_field(
            name="XP Boosters",
            value="\n".join(booster_list),
            inline=False
        )
        
        crp_data = user_items.get('custom_role_pass', {})
        crp_amount = crp_data.get('amount', 0)
        crp_time = crp_data.get('timeActivated')
        
        if crp_time:
            try:
                activated_time = datetime.fromisoformat(crp_time)
                current_time = datetime.now()
                
                time_diff = current_time - activated_time
                hours_passed = time_diff.total_seconds() / 3600
                
                duration_hours = 30 * 24
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
            name="Custom Role Pass",
            value=f"**Custom Role Pass** - {crp_status}\n`/use customrole` to activate\n`/customrole` to create a custom role when active",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="use", description="Use an item (booster or custom role pass)")
    @app_commands.describe(item="The item to use (e.g., tiny, small, medium, large, customrole)")
    async def use_item(self, interaction: discord.Interaction, item: str):
        if interaction.channel.id != bot_config.COMMANDS_CHANNEL_ID:
            return

        item_type, item_name = self.normalize_item_name(item)
        
        if not item_type:
            await interaction.response.send_message("Invalid item! Use `/inventory` to see your items.", ephemeral=True)
            return
        
        if item_type == 'booster':
            await self._use_booster(interaction, item_name)
        elif item_type == 'custom_role_pass':
            await self._use_custom_role_pass(interaction)

    @app_commands.command(name="equip", description="Equip an owned role")
    @app_commands.describe(role="The role to equip")
    async def equip(self, interaction: discord.Interaction, role: str):
        if interaction.channel.id != bot_config.COMMANDS_CHANNEL_ID:
            return
        
        role = self.normalize_role_name(role)
        
        if not role:
            await interaction.response.send_message("Invalid role!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(interaction.user.id)
        user_roles = user_data.get('roles', {})
        
        db_key = self.get_db_role_key(role)
        
        discord_role_id = bot_config.COLOUR_ROLES.get(role) or bot_config.SPECIAL_ROLES.get(role)
        
        if not discord_role_id:
            await interaction.response.send_message("Role not configured in the bot!", ephemeral=True)
            return
        
        discord_role = interaction.guild.get_role(discord_role_id)
        if not discord_role:
            await interaction.response.send_message("Role not found in the server!", ephemeral=True)
            return
        
        if not user_roles.get(db_key, False):
            await interaction.response.send_message(f"You don't own the {discord_role.mention} role! Purchase it from `/shop` first.", ephemeral=True, allowed_mentions=discord.AllowedMentions(roles=False))
            return
        
        if discord_role in interaction.user.roles:
            await interaction.response.send_message(f"You already have the {discord_role.mention} role equipped!", ephemeral=True, allowed_mentions=discord.AllowedMentions(roles=False))
            return
        
        try:
            await interaction.user.add_roles(discord_role)
            
            embed = discord.Embed(
                title="Role Equipped!",
                description=f"You equipped the {discord_role.mention} role!\nTo unequip use `/unequip {role}`",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=False))
        except Exception as e:
            print(f"Error adding Discord role: {e}")
            await interaction.response.send_message("Failed to equip role. Please message <@278365147167326208>", ephemeral=True)

    @app_commands.command(name="unequip", description="Unequip an owned role")
    @app_commands.describe(role="The role to unequip (e.g., Red, Blue, Custom1, Special1)")
    async def unequip(self, interaction: discord.Interaction, role: str):
        if interaction.channel.id != bot_config.COMMANDS_CHANNEL_ID:
            return
            
        role = self.normalize_role_name(role)
        
        if not role:
            await interaction.response.send_message("Invalid role!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(interaction.user.id)
        user_roles = user_data.get('roles', {})
        
        db_key = self.get_db_role_key(role)
        
        discord_role_id = bot_config.COLOUR_ROLES.get(role) or bot_config.SPECIAL_ROLES.get(role)
        
        if not discord_role_id:
            await interaction.response.send_message("Role not configured in the bot!", ephemeral=True)
            return
        
        discord_role = interaction.guild.get_role(discord_role_id)
        if not discord_role:
            await interaction.response.send_message("Role not found in the server!", ephemeral=True)
            return
        
        if not user_roles.get(db_key, False):
            await interaction.response.send_message(f"You don't own the {discord_role.mention} role! Purchase it from `/shop` first.", ephemeral=True, allowed_mentions=discord.AllowedMentions(roles=False))
            return
        
        if discord_role not in interaction.user.roles:
            await interaction.response.send_message(f"You don't have the {discord_role.mention} role equipped!", ephemeral=True, allowed_mentions=discord.AllowedMentions(roles=False))
            return
        
        try:
            await interaction.user.remove_roles(discord_role)
            
            embed = discord.Embed(
                title="Role Unequipped!",
                description=f"You unequipped the {discord_role.mention} role!\nTo re-equip use `/equip {role}`",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=False))
        except Exception as e:
            print(f"Error removing Discord role: {e}")
            await interaction.response.send_message("Failed to unequip role. Please message <@278365147167326208>", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Shop(bot))