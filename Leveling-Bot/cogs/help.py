import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class HelpCommand(commands.Cog):
    """Comprehensive help command system for Level Bot"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # All commands with detailed information
        self.commands_info = {
            # ============ LEVELING COMMANDS ============
            "rank": {
                "description": "View your rank card with level, XP progress, and stats",
                "usage": "/rank",
                "examples": [
                    "`/rank` - Shows your personal rank card with avatar"
                ],
                "aliases": [],
                "category": "Leveling"
            },
            "leaderboard": {
                "description": "View the top 10 users on the server leaderboard",
                "usage": "/leaderboard",
                "examples": [
                    "`/leaderboard` - Shows top 10 users by total XP"
                ],
                "aliases": ["lb"],
                "category": "Leveling"
            },
            "weeklylb": {
                "description": "View the weekly message leaderboard",
                "usage": "/weeklylb",
                "examples": [
                    "`/weeklylb` - Shows top 10 most active users this week"
                ],
                "aliases": ["wlb"],
                "category": "Leveling"
            },
            
            # ============ SHOP COMMANDS ============
            "shop": {
                "description": "View the item shop with roles, boosters, and special items",
                "usage": "/shop",
                "examples": [
                    "`/shop` - Browse available items and see what you own"
                ],
                "category": "Shop",
                "notes": "Shows color roles, special roles, and XP boosters with prices"
            },
            "buy": {
                "description": "Purchase items from `/shop` using your XP",
                "usage": "/buy <item>",
                "examples": [
                    "`/buy Red` - Buy the Red color role",
                    "`/buy Tiny Booster` - Buy a 1.1x XP booster",
                ],
                "category": "Shop",
                "notes": "Available roles: Red, Orange, Teal, Blue, Purple, Black\nAvailable boosters: Tiny, Small, Medium"
            },
            "inventory": {
                "description": "View your owned items, boosters, and active effects",
                "usage": "/inventory",
                "examples": [
                    "`/inventory` - See all your items and booster status"
                ],
                "category": "Shop",
                "notes": "Shows owned items, active boosters with time remaining, and Custom Role Pass status"
            },
            "use": {
                "description": "Activate a booster or Custom Role Pass from your inventory",
                "usage": "/use <item>",
                "examples": [
                    "`/use Tiny Booster` - Activate a 1.1x XP booster",
                    "`/use Custom Role Pass` - Activate a Custom Role Pass"
                ],
                "category": "Shop",
                "notes": "Only one booster can be active at a time. You'll receive a DM when it expires!"
            },
            "equip": {
                "description": "Equip a color role you own",
                "usage": "/equip <role>",
                "examples": [
                    "`/equip Red` - Equip your Red role",
                    "`/equip Blue` - Equip your Blue role"
                ],
                "category": "Shop",
                "notes": "You must own the role first. Purchase from /shop"
            },
            "unequip": {
                "description": "Unequip a color role you have equipped",
                "usage": "/unequip <role>",
                "examples": [
                    "/unequip Red - Unequip your Red role",
                    "/unequip Blue - Unequip your Blue role"
                ],
                "category": "Shop"
            },
            
            # ============ CUSTOM ROLE COMMANDS ============
            "customrole": {
                "description": "Create or update your custom role (requires active Custom Role Pass `/use Custom Role Pass`)",
                "usage": "!customrole <name> <color> [icon]",
                "examples": [
                    "`!customrole \"Custom Role\" #FF5733` - Create role with name and color",
                    "`!customrole \"Custom Role\" FF5733 https://i.imgur.com/example.png` - Create role with custom image icon (can send files too)"
                ],
                "category": "Custom Roles",
                "notes": "Must have an active Custom Role Pass. Use `/use Custom Role Pass` first!\nColor format: `#RRGGBB` or `RRGGBB` (hex)\nIcon can be file or image URL (max `256KB`)\nRole lasts `30 days`"
            },
            
            # ============ AUCTION COMMANDS ============
            "auctions": {
                "description": "View all currently active auctions",
                "usage": "/auctions",
                "examples": [
                    "`/auctions` - See all active auctions with current bids"
                ],
                "category": "Auctions"
            },
            "bid": {
                "description": "Place or update your bid on an active auction",
                "usage": "/bid <auction_id> <amount>",
                "examples": [
                    "`/bid abc123 15000` - Bid 15,000 Coins on auction abc123",
                    "`/bid abc123 3000` - Increase your bid to 18,000 Coins"
                ],
                "category": "Auctions",
                "notes": "Your Coins are locked when you bid. If outbid, your Coins are `refunded`.\nYou can increase your own bid by paying only the `difference`. (e.g. Your current bid is 1500 Coins, you may `/bid <auction_id> 1600` to increase to `1600`!)\nMinimum bid increase: `100 Coins`"
            }
        }
        
        # Category descriptions
        self.categories = {
            "Leveling": "View your rank, level, and compete on the leaderboard",
            "Shop":  "Buy roles, boosters, and special items with your Coins",
            "Custom Roles": " Create and customize your own unique role",
            "Auctions": " Bid on exclusive items and special roles",
        }
    
    def get_commands_by_category(self, category: str) -> list:
        """Get all commands in a specific category"""
        return sorted([cmd for cmd, info in self.commands_info.items() 
                      if info.get("category") == category])
    
    def create_general_help_embed(self) -> discord.Embed:
        """Create the general help overview embed"""
        
        # Create the embed first with initial description
        embed = discord.Embed(
            title="Help Menu",
            description="Gain XP & Coins by chatting, level up, and unlock rewards!\n\n"
                    "Use `/help <command>` for detailed information about a specific command.",
            color=discord.Color.blue()
        )
        
        # Add fields for each category
        for category, description in self.categories.items():
            commands_list = self.get_commands_by_category(category)
            commands_str = ", ".join([f"`/{cmd}`" for cmd in commands_list[:8]])
            if commands_str == "`/customrole`":
                commands_str = "`!customrole`"
            elif len(commands_list) > 8:
                commands_str += f"\n+ {len(commands_list) - 8} more..."
            
            embed.add_field(
                name=f"{category}",
                value=f"{description}\n{commands_str}",
                inline=False
            )
        
        embed.add_field(
            name="Extra Info",
            value="• Use `/help <command>` for detailed info\n"
                "• Buy items from `/shop` with Coins\n"
                "• Activate boosters with `/use`\n"
                "• Check active auctions with `/auctions`",
            inline=False
        )
        
        return embed
    
    def create_command_help_embed(self, command_name: str) -> discord.Embed:
        """Create a detailed help embed for a specific command"""
        command_info = self.commands_info.get(command_name.lower())
        
        if not command_info:
            embed = discord.Embed(
                title="Command Not Found",
                description=f"The command `{command_name}` doesn't exist.\nUse `/help` to see all available commands.",
                color=discord.Color.red()
            )
            return embed
        
        # Determine embed color based on category
        category_colors = {
            "Leveling": discord.Color.blue(),
            "Shop": discord.Color.green(),
            "Custom Roles": discord.Color.purple(),
            "Auctions": discord.Color.gold(),
        }
        
        color = category_colors.get(command_info["category"], discord.Color.blue())
        
        usage_command = command_info['usage'].split()[0]

        embed = discord.Embed(
            title=f"Help: `{usage_command}`",
            description=command_info["description"],
            color=color
        )
        
        # Add usage
        embed.add_field(
            name="Usage",
            value=f"`{command_info['usage']}`",
            inline=False
        )
        
        # Add examples if available
        if "examples" in command_info and command_info["examples"]:
            examples_text = "\n".join([f"• {ex}" for ex in command_info["examples"]])
            embed.add_field(
                name="Examples",
                value=examples_text,
                inline=False
            )
        
        # Add aliases if available
        if "aliases" in command_info and command_info["aliases"]:
            aliases_text = ", ".join([f"`{alias}`" for alias in command_info["aliases"]])
            embed.add_field(
                name="Aliases",
                value=aliases_text,
                inline=True
            )
        
        # Add permissions if required
        if "permissions" in command_info:
            embed.add_field(
                name="Required Permission",
                value=command_info["permissions"],
                inline=True
            )
        
        # Add category
        embed.add_field(
            name="Category",
            value=command_info["category"],
            inline=True
        )
        
        # Add notes if available
        if "notes" in command_info:
            embed.add_field(
                name="Additional Info",
                value=command_info["notes"],
                inline=False
            )

        return embed
    
    @app_commands.command(name="help", description="Get help with bot commands")
    @app_commands.describe(command="The specific command to get help with (optional)")
    async def help_command(
        self, 
        interaction: discord.Interaction, 
        command: Optional[str] = None
    ):
        if command:
            embed = self.create_command_help_embed(command)
        else:
            embed = self.create_general_help_embed()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="commands", description="List all available commands by category")
    async def commands_list(self, interaction: discord.Interaction):
        """Alternative command to show all commands organized by category"""
        embed = self.create_general_help_embed()
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCommand(bot))