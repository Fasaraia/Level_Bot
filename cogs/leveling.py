import discord
from discord.ext import commands, tasks
from utils import firebase_manager
from config import config as bot_config
from datetime import datetime
import time

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}
        self.cooldown_time = bot_config.XP_COOLDOWN
        self.check_booster_expiry.start()
        self.check_custom_role_expiry.start()
    
    def cog_unload(self):
        self.check_booster_expiry.cancel()
    
    #=============================#
    #     Booster & Role Tasks    #
    #=============================#

    @tasks.loop(seconds=bot_config.BOOSTER_CHECK_INTERVAL)
    async def check_booster_expiry(self):
        try:
            active_boosters_map = firebase_manager.get_all_active_boosters_all_users()
            
            for user_id, booster_names in active_boosters_map.items():
                for booster_name in booster_names:
                    duration = bot_config.BOOSTER_DURATIONS.get(booster_name, 30)
                    
                    if firebase_manager.check_booster_expiry(user_id, booster_name, duration):
                        firebase_manager.deactivate_item(user_id, booster_name)
    
                        user = await self.bot.fetch_user(int(user_id))
                        if user:
                            embed = discord.Embed(
                                title="Booster Expired",
                                description=f"Your **{booster_name.replace('_', ' ').title()}** has expired!",
                                color=discord.Color.orange()
                            )
                            await user.send(embed=embed)

        except Exception as e:
            print(f"Error in booster expiry check: {e}")

    @tasks.loop(seconds=bot_config.CUSTOM_ROLE_CHECK_INTERVAL)
    async def check_custom_role_expiry(self):
        all_users = firebase_manager.get_all_users_with_custom_roles()
        
        for user_id, crp_data in all_users.items():
            crp_time = crp_data.get('timeActivated')
            role_id = crp_data.get('roleId')
            
            if not crp_time or not role_id:
                continue

            activated_time = datetime.fromisoformat(crp_time)
            current_time = datetime.now()
            time_diff = current_time - activated_time
            hours_passed = time_diff.total_seconds() / 3600
            duration_hours = 30 * 24
            
            if hours_passed >= duration_hours:
                role_deleted = False
                member_notified = False
                
                for guild in self.bot.guilds:
                    custom_role = guild.get_role(role_id)
                    
                    if custom_role:
                        member = guild.get_member(int(user_id))
                        
                        if member:
                            await member.remove_roles(custom_role)
                            print(f"Removed role {custom_role.name} from {member.name}")
                            
                            if not member_notified:
                                try:
                                    embed = discord.Embed(
                                        title="Custom Role Expired",
                                        description=f"Your custom role **{custom_role.name}** has been removed because your Custom Role Pass expired (30 days).",
                                        color=discord.Color.orange()
                                    )
                                    embed.add_field(
                                        name="Want it back?",
                                        value="Use `/use customrole` to activate a new Custom Role Pass and `/customrole` to recreate it!"
                                    )
                                    await member.send(embed=embed)
                                    member_notified = True
                                except discord.Forbidden:
                                    pass
                        
                        if not role_deleted:
                            await custom_role.delete(reason="Custom Role Pass expired")
                            role_deleted = True
                            print(f"Deleted custom role {custom_role.name}")

                firebase_manager.clear_custom_role_pass(user_id)

    #============================#
    #    Registers coroutines    #
    #============================#

    @check_booster_expiry.before_loop
    async def before_check_booster_expiry(self):
        await self.bot.wait_until_ready()
    
    @check_custom_role_expiry.before_loop
    async def before_check_custom_role_expiry(self):
        await self.bot.wait_until_ready()

    #============================#
    #      Helper Functions      #
    #============================#

    def has_admin_role(self, member):
        for role in member.roles:
            if role.id in bot_config.ADMIN_ROLE_IDS or role.name in bot_config.ADMIN_ROLE_NAMES:
                return True
        return False
    
    def check_cooldown(self, user_id):
        current_time = time.time()
        
        if user_id in self.xp_cooldowns:
            if current_time - self.xp_cooldowns[user_id] < self.cooldown_time:
                return False
        
        self.xp_cooldowns[user_id] = current_time
        return True
    
    def calculate_booster_multiplier(self, user_id):
        """Calculate the total XP multiplier from active boosters"""
        active_boosters = firebase_manager.get_active_boosters(user_id)
        
        if not active_boosters:
            return 1.0
        
        # Get the booster multiplier based on which booster is active
        booster_multipliers = {
            'tiny_booster': 1.1,    # 1.1x - 10% boost
            'small_booster': 1.2,   # 1.2x - 20% boost
            'medium_booster': 1.3,  # 1.3x - 30% boost
            'large_booster': 1.5,   # 1.5x - 50% boost
        }
        
        # Get the first active booster (only one should be active at a time)
        active_booster_name = active_boosters[0]['name']
        return booster_multipliers.get(active_booster_name, 1.0)
    
    async def update_level_roles(self, member, user_level):
        """
        Update level roles for a member based on their current level.
        Adds all level roles they've earned (stacking).
        """
        if not hasattr(bot_config, 'LEVEL_ROLES'):
            return
        
        roles_to_add = []
        roles_to_remove = []
        
        # Get all level role IDs the user should have
        earned_role_ids = set()
        for level_requirement, role_id in bot_config.LEVEL_ROLES.items():
            if user_level >= level_requirement:
                earned_role_ids.add(role_id)
        
        # Check current level roles the user has
        current_level_role_ids = set()
        for role in member.roles:
            if role.id in bot_config.LEVEL_ROLES.values():
                current_level_role_ids.add(role.id)
        
        # Determine which roles to add and remove
        for role_id in earned_role_ids:
            if role_id not in current_level_role_ids:
                role = member.guild.get_role(role_id)
                if role:
                    roles_to_add.append(role)
        
        for role_id in current_level_role_ids:
            if role_id not in earned_role_ids:
                role = member.guild.get_role(role_id)
                if role:
                    roles_to_remove.append(role)
        
        # Apply role changes
        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason=f"Earned level roles (Level {user_level})")
                print(f"Added {len(roles_to_add)} level role(s) to {member.name}")
            
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason=f"Lost level roles (Level {user_level})")
                print(f"Removed {len(roles_to_remove)} level role(s) from {member.name}")
        except discord.Forbidden:
            print(f"Missing permissions to manage roles for {member.name}")
        except Exception as e:
            print(f"Error updating level roles for {member.name}: {e}")
    
    #============================#
    #  XP & Leveling Listerner   #
    #============================#

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        if not self.check_cooldown(message.author.id):
            return
        
        base_xp = float(bot_config.XP_BASE)
        bonus_multiplier = 1.0
        
        # Role bonus multiplier - only take the HIGHEST bonus
        role_bonuses = []
        for role in message.author.roles:
            if role.id in bot_config.XP_BONUS_ROLE:
                role_bonuses.append(bot_config.XP_BONUS_ROLE[role.id])
        
        if role_bonuses:
            highest_bonus = max(role_bonuses)
            bonus_multiplier += (highest_bonus / 100.0)
        
        # Booster multiplier
        booster_multiplier = self.calculate_booster_multiplier(message.author.id)
        
        total_multiplier = bonus_multiplier * booster_multiplier
        xp_gain = round(base_xp * total_multiplier, 2)
        
        result = firebase_manager.add_xp(
            message.author.id,
            str(message.author),
            xp_gain
        )
        
        # Update level roles
        await self.update_level_roles(message.author, result['new_level'])
        
        if result['leveled_up']:
            embed = discord.Embed(
                title="🎉 Level Up!",
                description=f"Congratulations {message.author.mention}! You've reached **Level {result['new_level']}**!",
                color=discord.Color.gold()
            )
            
            if bot_config.LEVEL_UP_CHANNEL_ID:
                level_up_channel = message.guild.get_channel(bot_config.LEVEL_UP_CHANNEL_ID)
                if level_up_channel:
                    await level_up_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))