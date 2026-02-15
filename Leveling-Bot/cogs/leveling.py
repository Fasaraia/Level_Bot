import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils import firebase_manager
from config import config as bot_config
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import aiohttp
from datetime import datetime, timedelta
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
                                title="⚡ Booster Expired",
                                description=f"Your **{booster_name.replace('_', ' ').title()}** has expired!",
                                color=discord.Color.orange()
                            )
                            await user.send(embed=embed)

        except Exception as e:
            print(f"Error in booster expiry check: {e}")
    
    @check_booster_expiry.before_loop
    async def before_check_booster_expiry(self):
        await self.bot.wait_until_ready()
    
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
                                        title="⚠️ Custom Role Expired",
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

    @check_custom_role_expiry.before_loop
    async def before_check_custom_role_expiry(self):
        await self.bot.wait_until_ready()

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
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        if not self.check_cooldown(message.author.id):
            return
        
        base_xp = float(bot_config.XP_BASE)
        bonus_multiplier = 1.0
        
        # Role bonus multiplier
        for role in message.author.roles:
            if role.id in bot_config.XP_BONUS_ROLE:
                bonus_multiplier += (bot_config.XP_BONUS_ROLE[role.id] / 100.0)
        
        # Booster multiplier
        booster_multiplier = self.calculate_booster_multiplier(message.author.id)
        
        # Calculate total XP with all multipliers (keep as float)
        total_multiplier = bonus_multiplier * booster_multiplier
        xp_gain = round(base_xp * total_multiplier, 2)  # Float with 2 decimals
        
        result = firebase_manager.add_xp(
            message.author.id,
            str(message.author),
            xp_gain
        )
        
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

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def has_admin_role(self, member):
        for role in member.roles:
            if role.id in bot_config.ADMIN_ROLE_IDS:
                return True
        return False
    
    async def get_avatar_image(self, user):
        async with aiohttp.ClientSession() as session:
            async with session.get(str(user.display_avatar.url)) as resp:
                avatar_bytes = await resp.read()
                avatar = Image.open(io.BytesIO(avatar_bytes)).convert('RGBA')
                return avatar
    
    def create_circle_mask(self, size):
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)
        return mask
    
    def create_rank_card(self, user, user_data, rank):
        width, height = 900, 300
        card = Image.new('RGBA', (width, height), (47, 49, 54, 255))
        draw = ImageDraw.Draw(card)
        
        draw.rectangle([(0, 0), (width, height)], fill=(35, 39, 42, 255))
        
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([(20, 20), (width-20, height-20)], fill=(47, 49, 54, 230))
        card = Image.alpha_composite(card, overlay)
        draw = ImageDraw.Draw(card)
        
        current_level = user_data['level']
        total_xp = user_data['totalXP']
        user_xp = user_data['currentXP'] 
        
        # Calculate XP thresholds
        xp_for_current_level = firebase_manager.calculate_xp_for_level(current_level)
        xp_for_next_level = firebase_manager.calculate_xp_for_level(current_level + 1)
        
        # Progress bar: XP gained after previous level / XP needed for next level
        xp_after_previous = total_xp - xp_for_current_level
        xp_needed_for_next = xp_for_next_level - xp_for_current_level
        
        try:
            title_font = ImageFont.truetype("arial.ttf", 36)
            stat_font = ImageFont.truetype("arial.ttf", 24)
            label_font = ImageFont.truetype("arial.ttf", 18)
        except:
            title_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
        
        draw.text((200, 40), user.name, fill=(255, 255, 255, 255), font=title_font)
        
        draw.text((200, 90), f"Rank #{rank}", fill=(153, 170, 181, 255), font=stat_font)
        draw.text((350, 90), f"Level {current_level}", fill=(153, 170, 181, 255), font=stat_font)
        
        draw.text((200, 140), "Progress", fill=(153, 170, 181, 255), font=label_font)
        
        bar_x, bar_y = 200, 170
        bar_width, bar_height = 650, 40
        
        draw.rounded_rectangle(
            [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
            radius=20,
            fill=(32, 34, 37, 255)
        )
        
        # Progress bar fill: XP after previous level / XP needed for next level
        progress = xp_after_previous / xp_needed_for_next if xp_needed_for_next > 0 else 0
        filled_width = int(bar_width * progress)
        
        if filled_width > 0:
            draw.rounded_rectangle(
                [(bar_x, bar_y), (bar_x + filled_width, bar_y + bar_height)],
                radius=20,
                fill=(88, 101, 242, 255)
            )
        
        # Text display: Total XP / Total XP needed for next level
        xp_text = f"{total_xp:,}/{xp_for_next_level:,} XP"
        draw.text((bar_x + bar_width // 2, bar_y + bar_height // 2), xp_text, 
                 fill=(255, 255, 255, 255), font=label_font, anchor="mm")
        
        draw.text((200, 230), f"Current XP: {user_xp:,}", fill=(153, 170, 181, 255), font=label_font)
        draw.text((400, 230), f"Weekly Messages: {user_data['messageCount']:,}", fill=(153, 170, 181, 255), font=label_font)
        
        return card
    
    async def add_avatar_to_card(self, card, user):
        try:
            avatar = await self.get_avatar_image(user)
            avatar = avatar.resize((140, 140), Image.Resampling.LANCZOS)
            
            mask = self.create_circle_mask((140, 140))
            
            card.paste(avatar, (40, 80), mask)
        except Exception as e:
            print(f"Error adding avatar: {e}")
        
        return card
    
    async def create_leaderboard_card(self, leaderboard_data):
        width, height = 800, 800
        card = Image.new('RGBA', (width, height), (35, 39, 42, 255))
        draw = ImageDraw.Draw(card)
        
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            name_font = ImageFont.truetype("arial.ttf", 24)
            stat_font = ImageFont.truetype("arial.ttf", 20)
        except:
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
        
        draw.text((width // 2, 50), "Leaderboard", fill=(255, 215, 0, 255), 
                 font=title_font, anchor="mm")
        
        y_offset = 120
        row_height = 65
        avatar_size = 50
        
        for idx, user_data in enumerate(leaderboard_data):
            rank = user_data['rank']
            user_id = user_data['userId']
            username = user_data.get('lastUsername', 'Unknown')
            total_xp = user_data['totalXP']
            level = user_data['level']
            
            medal = f"#{rank}"
            
            draw.rounded_rectangle(
                [(40, y_offset), (width - 40, y_offset + row_height - 10)],
                radius=15,
                fill=(47, 49, 54, 255)
            )
            
            try:
                user = await self.bot.fetch_user(int(user_id))
                avatar = await self.get_avatar_image(user)
                avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = self.create_circle_mask((avatar_size, avatar_size))
                card.paste(avatar, (50, y_offset + 7), mask)
            except:
                pass
            
            draw.text((110, y_offset + row_height // 2 - 5), medal, 
                     fill=(255, 255, 255, 255), font=name_font, anchor="lm")
            
            draw.text((160, y_offset + row_height // 2 - 5), username, 
                     fill=(255, 255, 255, 255), font=name_font, anchor="lm")
            
            draw.text((width - 250, y_offset + row_height // 2 - 5), f"Level {level}", 
                     fill=(153, 170, 181, 255), font=stat_font, anchor="lm")
            
            draw.text((width - 120, y_offset + row_height // 2 - 5), f"{total_xp:,} XP", 
                     fill=(88, 101, 242, 255), font=stat_font, anchor="lm")
            
            y_offset += row_height
        
        return card
    
    async def create_weekly_leaderboard_card(self, weekly_data):
        width, height = 800, 800
        card = Image.new('RGBA', (width, height), (35, 39, 42, 255))
        draw = ImageDraw.Draw(card)
        
        try:
            title_font = ImageFont.truetype("arial.ttf", 48)
            name_font = ImageFont.truetype("arial.ttf", 24)
            stat_font = ImageFont.truetype("arial.ttf", 20)
        except:
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
        
        draw.text((width // 2, 50), "Weekly Leaderboard", fill=(88, 101, 242, 255), 
                 font=title_font, anchor="mm")
        
        y_offset = 120
        row_height = 65
        avatar_size = 50
        
        for idx, data in enumerate(weekly_data[:10]):
            rank = idx + 1
            user_id = data['userId']
            username = data['username']
            messages = data['messageCount']
            
            medal = f"#{rank}"
            
            draw.rounded_rectangle(
                [(40, y_offset), (width - 40, y_offset + row_height - 10)],
                radius=15,
                fill=(47, 49, 54, 255)
            )
            
            try:
                user = await self.bot.fetch_user(int(user_id))
                avatar = await self.get_avatar_image(user)
                avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = self.create_circle_mask((avatar_size, avatar_size))
                card.paste(avatar, (50, y_offset + 7), mask)
            except:
                pass
            
            draw.text((110, y_offset + row_height // 2 - 5), medal, 
                     fill=(255, 255, 255, 255), font=name_font, anchor="lm")
            
            draw.text((160, y_offset + row_height // 2 - 5), username, 
                     fill=(255, 255, 255, 255), font=name_font, anchor="lm")
            
            draw.text((width - 150, y_offset + row_height // 2 - 5), f"{messages:,} messages", 
                     fill=(88, 101, 242, 255), font=stat_font, anchor="lm")
            
            y_offset += row_height
        
        return card
    
    @commands.hybrid_command(name="rank", description="View your rank card")
    async def rank(self, ctx):
        await ctx.defer()
        
        try:
            user_data = firebase_manager.get_user_data(ctx.author.id)
            rank = firebase_manager.get_user_rank(ctx.author.id)
            
            card = self.create_rank_card(ctx.author, user_data, rank)
            card = await self.add_avatar_to_card(card, ctx.author)
            
            buffer = io.BytesIO()
            card.save(buffer, format='PNG')
            buffer.seek(0)
            
            file = discord.File(buffer, filename='rank.png')
            await ctx.send(file=file)
        except Exception as e:
            print(f"Error creating rank card: {e}")
            await ctx.send("Error creating rank card.")
    
    @commands.hybrid_command(name="leaderboard", aliases=["lb"], description="View the server leaderboard")
    async def leaderboard(self, ctx):
        await ctx.defer()
        
        try:
            leaderboard = firebase_manager.get_leaderboard(limit=10)
            
            if not leaderboard:
                await ctx.send("No users on the leaderboard yet!")
                return
            
            card = await self.create_leaderboard_card(leaderboard)
            
            buffer = io.BytesIO()
            card.save(buffer, format='PNG')
            buffer.seek(0)
            
            file = discord.File(buffer, filename='leaderboard.png')
            await ctx.send(file=file)
        except Exception as e:
            print(f"Error creating leaderboard: {e}")
            await ctx.send("Error creating leaderboard.")
    
    @commands.hybrid_command(name="weeklylb", aliases=["wlb"], description="View weekly message leaderboard")
    async def weeklylb(self, ctx):
        await ctx.defer()
        
        try:
            weekly_data = firebase_manager.get_weekly_leaderboard(limit=10)
            
            if not weekly_data:
                await ctx.send("No weekly data yet!")
                return
            
            card = await self.create_weekly_leaderboard_card(weekly_data)
            
            buffer = io.BytesIO()
            card.save(buffer, format='PNG')
            buffer.seek(0)
            
            file = discord.File(buffer, filename='weekly_leaderboard.png')
            await ctx.send(file=file)
        except Exception as e:
            print(f"Error creating weekly leaderboard: {e}")
            await ctx.send("Error creating weekly leaderboard.")
    
    @commands.hybrid_command(name="addxp", description="Add XP to a user")
    @app_commands.describe(user="The user to give XP to", amount="Amount of XP to add")
    async def addxp(self, ctx, user: discord.Member, amount: int):
        if not self.has_admin_role(ctx.author):
            return

        result = firebase_manager.add_xp(user.id, str(user), amount)
        
        embed = discord.Embed(
            title="✅ XP Added",
            description=f"Added **{amount} XP** to {user.mention}!",
            color=discord.Color.green()
        )
        embed.add_field(name="New Level", value=result['new_level'], inline=True)
        embed.add_field(name="Total XP", value=f"{result['total_xp']:,}", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="removexp", description="Remove XP from a user")
    @app_commands.describe(user="The user to remove XP from", amount="Amount of XP to remove")
    async def removexp(self, ctx, user: discord.Member, amount: int):
        if not self.has_admin_role(ctx.author):
            return
        
        result = firebase_manager.add_xp(user.id, str(user), -amount)
        
        embed = discord.Embed(
            title="✅ XP Removed",
            description=f"Removed **{amount} XP** from {user.mention}!",
            color=discord.Color.red()
        )
        embed.add_field(name="New Level", value=result['new_level'], inline=True)
        embed.add_field(name="Total XP", value=f"{result['total_xp']:,}", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="reset", description="Reset a user's XP and progress")
    @app_commands.describe(user="The user to reset")
    async def reset(self, ctx, user: discord.Member):
        if not self.has_admin_role(ctx.author):
            await ctx.send("❌ You don't have permission to use this command!", ephemeral=True)
            return
        
        firebase_manager.reset_user(user.id)
        
        await ctx.send(f"✅ Reset {user.mention}'s XP and progress!")


async def setup(bot):
    await bot.add_cog(Leveling(bot))
    await bot.add_cog(Commands(bot))