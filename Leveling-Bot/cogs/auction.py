import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils import firebase_manager
from config import config as bot_config
from datetime import datetime, timedelta
import asyncio

class Auctions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_auction_expiry.start()
    
    def cog_unload(self):
        self.check_auction_expiry.cancel()
    
    def has_auctioneer_role(self, member):
        return any(role.id in bot_config.AUCTIONEER_ROLE_IDS for role in member.roles)
    
    def get_auction_item_info(self, item_type):
        items = {
            'special_role_1': {
                'name': 'Special Role 1',
                'description': 'Exclusive special role with 5% XP bonus',
                'starting_bid': 10000
            },
            'special_role_2': {
                'name': 'Special Role 2',
                'description': 'Exclusive special role with 10% XP bonus',
                'starting_bid': 10000
            },
            'custom_role_pass': {
                'name': 'Custom Role Pass',
                'description': 'Create your own custom role with name, color, and icon* for 30 days\n\n-# Icon availability may vary',
                'starting_bid': 10000
            },
            'large_booster': {
                'name': 'Large Booster (1.5x XP)',
                'description': 'Exclusive 1.5x XP booster for 7 days',
                'starting_bid': 10000
            }
        }
        return items.get(item_type)
    
    @tasks.loop(minutes=1)
    async def check_auction_expiry(self):
        try:
            active_auctions = firebase_manager.get_active_auctions()
            
            for auction_id, auction_data in active_auctions.items():
                end_time_str = auction_data.get('endTime')
                if not end_time_str:
                    continue
                
                try:
                    end_time = datetime.fromisoformat(end_time_str)
                    current_time = datetime.now()
                    
                    if current_time >= end_time:
                        await self.complete_auction(auction_id, auction_data)
                except Exception as e:
                    print(f"Error checking auction {auction_id} expiry: {e}")
        
        except Exception as e:
            print(f"Error in auction expiry check: {e}")
    
    @check_auction_expiry.before_loop
    async def before_check_auction_expiry(self):
        await self.bot.wait_until_ready()
    
    async def complete_auction(self, auction_id, auction_data):
        try:
            winner_id = auction_data.get('highestBidder')
            winning_bid = auction_data.get('highestBid', 0)
            item_type = auction_data.get('itemType')
            
            auction_channel = self.bot.get_channel(bot_config.AUCTION_CHANNEL_ID)
            
            if not winner_id or winning_bid == 0:
                embed = discord.Embed(
                    title="Auction Ended - No Bids",
                    description=f"The auction for **{self.get_auction_item_info(item_type)['name']}** has ended with no bids.",
                    color=discord.Color.orange()
                )
                if auction_channel:
                    await auction_channel.send(embed=embed)
                
                firebase_manager.delete_auction(auction_id)
                return
            
            winner = await self.bot.fetch_user(int(winner_id))
            
            if item_type == 'special_role_1':
                firebase_manager.set_user_role(winner_id, 'Special Role 1', True)
                item_name = 'Special Role 1'
            elif item_type == 'special_role_2':
                firebase_manager.set_user_role(winner_id, 'Special Role 2', True)
                item_name = 'Special Role 2'
            elif item_type == 'custom_role_pass':
                firebase_manager.add_item(winner_id, 'custom_role_pass', 1)
                item_name = 'Custom Role Pass'
            elif item_type == 'large_booster':
                firebase_manager.add_item(winner_id, 'large_booster', 1)
                item_name = 'Large Booster'
            
            embed = discord.Embed(
                title="Auction Won!",
                description=f"{winner.mention} has won the auction for **{item_name}**!",
                color=discord.Color.gold()
            )
            embed.add_field(name="Winning Bid", value=f"{winning_bid:,} XP", inline=True)
            embed.add_field(name="Winner", value=winner.mention, inline=True)
            
            if auction_channel:
                await auction_channel.send(embed=embed)
            
            try:
                dm_embed = discord.Embed(
                    title="Congratulations!",
                    description=f"You won the auction for **{item_name}**!",
                    color=discord.Color.gold()
                )
                dm_embed.add_field(name="Your Winning Bid", value=f"{winning_bid:,} XP", inline=False)
                
                if item_type in ['special_role_1', 'special_role_2']:
                    dm_embed.add_field(name="Next Steps", value="Use `/equip` to equip your new role!", inline=False)
                elif item_type == 'custom_role_pass':
                    dm_embed.add_field(name="Next Steps", value="Use `/use customrole` to activate it, then `/customrole` to create your role!", inline=False)
                elif item_type == 'large_booster':
                    dm_embed.add_field(name="Next Steps", value="Use `/use large` to activate your booster!", inline=False)
                
                await winner.send(embed=dm_embed)
            except discord.Forbidden:
                pass
            
            firebase_manager.delete_auction(auction_id)
        
        except Exception as e:
            print(f"Error completing auction {auction_id}: {e}")
    
    @app_commands.command(name="startauction", description="Start an auction (Auctioneer only)")
    @app_commands.describe(
        item="Item to auction (special1, special2, customrole, largebooster)",
        duration="Duration in hours (1-72)",
        starting_bid="Starting bid amount (optional)"
    )
    async def start_auction(self, interaction: discord.Interaction, item: str, duration: int, starting_bid: int = None):
        if not self.has_auctioneer_role(interaction.user):
            await interaction.response.send_message("You don't have permission to start auctions!", ephemeral=True)
            return
        
        item_map = {
            'special1': 'special_role_1',
            'specialrole1': 'special_role_1',
            'special_role_1': 'special_role_1',
            'special2': 'special_role_2',
            'specialrole2': 'special_role_2',
            'special_role_2': 'special_role_2',
            'customrole': 'custom_role_pass',
            'customrolepass': 'custom_role_pass',
            'crp': 'custom_role_pass',
            'largebooster': 'large_booster',
            'large': 'large_booster',
            'booster4': 'large_booster'
        }
        
        item_type = item_map.get(item.lower())
        if not item_type:
            await interaction.response.send_message("Invalid item! Use: `special1`, `special2`, `customrole`, or `largebooster`", ephemeral=True)
            return
        
        if duration < 1 or duration > 72:
            await interaction.response.send_message("Duration must be between 1 and 72 hours!", ephemeral=True)
            return
        
        item_info = self.get_auction_item_info(item_type)
        if starting_bid is None:
            starting_bid = item_info['starting_bid']
        
        if starting_bid < 100:
            await interaction.response.send_message("Starting bid must be at least 100 XP!", ephemeral=True)
            return
        
        end_time = datetime.now() + timedelta(hours=duration)
        
        auction_id = firebase_manager.create_auction(
            item_type=item_type,
            starting_bid=starting_bid,
            duration_hours=duration,
            started_by=interaction.user.id
        )
        
        embed = discord.Embed(
            title=f"Auction Started - {item_info['name']}",
            description=item_info['description'],
            color=discord.Color.blue()
        )
        embed.add_field(name="Starting Bid", value=f"{starting_bid:,} XP", inline=True)
        embed.add_field(name="Current Bid", value=f"{starting_bid:,} XP", inline=True)
        embed.add_field(name="Highest Bidder", value="No bids yet", inline=True)
        embed.add_field(name="Ends At", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
        embed.set_footer(text=f"Use /bid {auction_id} <amount> to place a bid!")
        
        auction_channel = self.bot.get_channel(bot_config.AUCTION_CHANNEL_ID)
        if auction_channel:
            message = await auction_channel.send(embed=embed)
            firebase_manager.set_auction_message_id(auction_id, message.id)
        
        await interaction.response.send_message(f"Auction started! ID: `{auction_id}`", ephemeral=True)
    
    @app_commands.command(name="bid", description="Place a bid on an active auction")
    @app_commands.describe(
        auction_id="The auction ID",
        amount="Your bid amount"
    )
    async def bid(self, interaction: discord.Interaction, auction_id: str, amount: int):
        if interaction.channel.id != bot_config.COMMANDS_CHANNEL_ID:
            return
        
        auction = firebase_manager.get_auction(auction_id)
        
        if not auction:
            await interaction.response.send_message("Auction not found!", ephemeral=True)
            return
        
        if amount < 100:
            await interaction.response.send_message("Bid must be at least 100 XP!", ephemeral=True)
            return
        
        user_data = firebase_manager.get_user_data(interaction.user.id)
        user_xp = user_data['currentXP']
        
        current_highest = auction.get('highestBid', auction.get('startingBid', 0))
        previous_bidder = auction.get('highestBidder')
        
        is_own_bid = previous_bidder == str(interaction.user.id)
        
        if is_own_bid:
            xp_difference = amount - current_highest
            
            if xp_difference <= 0:
                await interaction.response.send_message(f"Your new bid must be higher than your current bid of {current_highest:,} XP!", ephemeral=True)
                return
            
            if user_xp < xp_difference:
                await interaction.response.send_message(f"Not enough XP! You need {xp_difference:,} more XP to increase your bid to {amount:,} XP.", ephemeral=True)
                return
            
            firebase_manager.add_xp(interaction.user.id, str(interaction.user), -xp_difference)
        else:
            if amount <= current_highest:
                await interaction.response.send_message(f"Your bid must be higher than the current bid of {current_highest:,} XP!", ephemeral=True)
                return
            
            if user_xp < amount:
                await interaction.response.send_message(f"Not enough XP! You have {user_xp:,} XP but bid {amount:,} XP.", ephemeral=True)
                return
            
            if previous_bidder:
                firebase_manager.add_xp(int(previous_bidder), "Auction Refund", current_highest)
                
                try:
                    prev_user = await self.bot.fetch_user(int(previous_bidder))
                    refund_embed = discord.Embed(
                        title="Bid Refunded",
                        description=f"Your bid of **{current_highest:,} XP** was outbid on auction `{auction_id}`.",
                        color=discord.Color.orange()
                    )
                    await prev_user.send(embed=refund_embed)
                except:
                    pass
            
            firebase_manager.add_xp(interaction.user.id, str(interaction.user), -amount)
        
        firebase_manager.update_auction_bid(auction_id, interaction.user.id, amount)
        
        auction_channel = self.bot.get_channel(bot_config.AUCTION_CHANNEL_ID)
        if auction_channel:
            message_id = auction.get('messageId')
            
            if message_id:
                try:
                    original_message = await auction_channel.fetch_message(int(message_id))
                    
                    item_info = self.get_auction_item_info(auction.get('itemType'))
                    end_time = datetime.fromisoformat(auction.get('endTime'))
                    starting_bid = auction.get('startingBid', 0)
                    
                    updated_embed = discord.Embed(
                        title=f"🔨 Auction Started - {item_info['name']}",
                        description=item_info['description'],
                        color=discord.Color.blue()
                    )
                    updated_embed.add_field(name="Starting Bid", value=f"{starting_bid:,} XP", inline=True)
                    updated_embed.add_field(name="Current Bid", value=f"{amount:,} XP", inline=True)
                    updated_embed.add_field(name="Highest Bidder", value=interaction.user.mention, inline=True)
                    updated_embed.add_field(name="Ends At", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
                    updated_embed.set_footer(text=f"Use /bid {auction_id} <amount> to place a bid!")
                    
                    await original_message.edit(embed=updated_embed)
                except discord.NotFound:
                    pass
                except Exception as e:
                    print(f"Error updating auction message: {e}")
        
        if is_own_bid:
            await interaction.response.send_message(f"Bid updated successfully! You increased your bid to {amount:,} XP.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Bid placed successfully!", ephemeral=True)

    @app_commands.command(name="auctions", description="View all active auctions")
    async def view_auctions(self, interaction: discord.Interaction):
        if interaction.channel.id != bot_config.COMMANDS_CHANNEL_ID:
            return
        
        auctions = firebase_manager.get_active_auctions()
        
        if not auctions:
            await interaction.response.send_message("No active auctions at the moment!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Active Auctions",
            description="Use `/bid <auction_id> <amount>` to place a bid",
            color=discord.Color.blue()
        )
        
        for auction_id, auction_data in auctions.items():
            item_info = self.get_auction_item_info(auction_data.get('itemType'))
            current_bid = auction_data.get('highestBid', auction_data.get('startingBid', 0))
            end_time = datetime.fromisoformat(auction_data.get('endTime'))
            
            bidder_text = "No bids yet"
            if auction_data.get('highestBidder'):
                try:
                    bidder = await self.bot.fetch_user(int(auction_data.get('highestBidder')))
                    bidder_text = bidder.mention
                except:
                    bidder_text = "Unknown"
            
            embed.add_field(
                name=f"{item_info['name']} (ID: {auction_id})",
                value=f"**Current Bid:** {current_bid:,} XP\n**Highest Bidder:** {bidder_text}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="cancelauction", description="Cancel an active auction (Auctioneer only)")
    @app_commands.describe(auction_id="The auction ID to cancel")
    async def cancel_auction(self, interaction: discord.Interaction, auction_id: str):
        if not self.has_auctioneer_role(interaction.user):
            await interaction.response.send_message("You don't have permission to cancel auctions!", ephemeral=True)
            return
        
        auction = firebase_manager.get_auction(auction_id)
        if not auction:
            await interaction.response.send_message("Auction not found!", ephemeral=True)
            return
        
        bidder_id = auction.get('highestBidder')
        bid_amount = auction.get('highestBid', 0)
        
        if bidder_id and bid_amount > 0:
            firebase_manager.add_xp(int(bidder_id), "Auction Cancelled", bid_amount)
            
            try:
                bidder = await self.bot.fetch_user(int(bidder_id))
                refund_embed = discord.Embed(
                    title="Auction Cancelled",
                    description=f"The auction you bid on has been cancelled. Your bid of **{bid_amount:,} XP** has been refunded.",
                    color=discord.Color.orange()
                )
                await bidder.send(embed=refund_embed)
            except:
                pass
        
        firebase_manager.delete_auction(auction_id)
        
        item_info = self.get_auction_item_info(auction.get('itemType'))
        
        embed = discord.Embed(
            title="Auction Cancelled",
            description=f"The auction for **{item_info['name']}** has been cancelled by {interaction.user.mention}.",
            color=discord.Color.red()
        )
        
        auction_channel = self.bot.get_channel(bot_config.AUCTION_CHANNEL_ID)
        if auction_channel:
            await auction_channel.send(embed=embed)
        
        await interaction.response.send_message("Auction cancelled successfully!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Auctions(bot))