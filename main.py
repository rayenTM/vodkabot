import asyncio
import logging
import os
import random

import discord
import discord.utils
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()
token = os.getenv('DISCORD_TOKEN')
channel_id = int(os.getenv('WELCOME_CHANNEL_ID'))
secret_role = os.getenv('SECRET_ROLE')
owner_id = os.getenv('OWNER_ID')
guild_id = int(os.getenv('GUILD_ID'))
suggestion_channel_id = int(os.getenv('SUGGESTION_CHANNEL_ID'))

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

###
### Bot Startup Commands ###
###
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        # Prevent Duplicate Commands (Global vs Guild)
        # We will sync ONLY to the specific guild for development (updates are instant)
        # and explicitly CLEAR global commands to remove the duplicates.
        
        if guild_id:
            guild_obj = discord.Object(id=guild_id)
            
            # 1. Copy all commands to our Guild
            bot.tree.copy_global_to(guild=guild_obj)
            
            # 2. Clear Global commands (removes "ghost" global duplicates)
            # This is necessary because previous runs might have synced globally.
            # We want to use ONLY the guild-level commands for development.
            bot.tree.clear_commands(guild=None)
            
            # 3. Sync!
            # A) Global -> Empty (Removes duplicates from Discord)
            await bot.tree.sync() # This clears the global list on Discord
            
            # B) Guild -> Full (Updates our guild instantly)
            await bot.tree.sync(guild=guild_obj)
            
            print(f"Synced commands to Guild ID: {guild_id} (Global wiped to prevent dupe)")
        else:
            # Fallback to Global Sync if no Guild ID
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s) globally")
            
    except Exception as e:
        print(e)


###
### Member Events ###
###
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"Welcome to the server, {member.mention}!")
    else:
        print(f"Error: Could not find channel {channel_id}. Check the ID!")

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"Goodbye, {member.display_name}!")



###
### Roll Dice Command ###
###
@bot.tree.command(name="roll", description="Roll a specific die")
@app_commands.choices(sides=[
    app_commands.Choice(name="d4", value=4),
    app_commands.Choice(name="d6", value=6),
    app_commands.Choice(name="d8", value=8),
    app_commands.Choice(name="d10", value=10),
    app_commands.Choice(name="d12", value=12),
    app_commands.Choice(name="d20", value=20),
    app_commands.Choice(name="d100", value=100),
])
async def roll(interaction: discord.Interaction, sides: app_commands.Choice[int]):
    # Generate the random roll result
    result = random.randint(1, sides.value)
    
    # Send a formatted response back to the user
    await interaction.response.send_message(
        f"🎲 {interaction.user.mention} rolled a **{sides.name}** and got: **{result}**!"
    )




###
### About Command ### THIS PROBABLY ISNT PEP COMPLIANT BUT THATS OKAY
###
@bot.tree.command(name="about", description="Details bot version and author")
async def about(interaction: discord.Interaction):

    # embed = discord.Embed(title="About", description="This is a test bot created by Rayen/Akina.", color=discord.Color.green())
    channel_url = f"https://discord.com/channels/{guild_id}/{suggestion_channel_id}"
    
    embed = discord.Embed(
        title="Vodka(Bot) ver. 1.5 BETA",
        description="I am Vodka! Ready to go full throttle?",
        color=discord.Color.blue() # You can also use a hex value, e.g., 0x00ff00
    )

    # Add fields
    # Fetch owner from environment variable
    owner_id_str = os.getenv('OWNER_ID')
    
    if owner_id_str:
        try:
            # fetch_user makes an API call to get the user even if they aren't in the cache
            creator = await interaction.client.fetch_user(int(owner_id_str))
            embed.set_author(name=creator.name, icon_url=creator.avatar.url)
        except Exception:
             # Fallback if ID is invalid or user not found
             embed.set_author(name="Rayen/Akina", icon_url=None)
    else:
        embed.set_author(name="Rayen/Akina", icon_url=None)

    embed.add_field(name="Main Features", value="* Welcome/Leave Messages\n* Dice Roller\n* Replies to certain messages!", inline=False)
    embed.add_field(name="Upcoming Features", value="* Umadle (Umawordle) \n* And other fun games!", inline=False)
    embed.add_field(name="GitHub", value=f"[Made using Python, Git, and Docker!](https://github.com/rayenTM/vodkabot)\n* Feel free to make suggestions [here]({channel_url})!", inline=False)


    embed.set_thumbnail(url="https://preview.redd.it/vodka-deserve-better-spotlight-position-in-the-anime-game-v0-3mxt0waxb6tf1.png?auto=webp&s=0b7eaa7490ccaebe659b7ef1860838fb642c6b22") # Replace with a valid image URL
    embed.set_image(url="https://upload.wikimedia.org/wikipedia/commons/1/15/Vodka%28horse%29_20070527R1.jpg") # Replace with a valid image URL=
    embed.set_footer(
        text="Did you know? I love horses! So you also have the real Vodka here too since I'm the developer. 🐴",
        icon_url="https://gametora.com/images/umamusume/characters/chara_stand_1009_100901.png" # Optional: URL for a footer icon
    )

    # Send the embed to the channel
    await interaction.response.send_message(embed=embed)




###
### Load Cogs ###
###
async def load():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')




###
### Main Function ###
###
async def main():

    discord.utils.setup_logging(handler=handler, level=logging.DEBUG)

    async with bot:
        await load()
        await bot.start(token)





### Run Bot ###
asyncio.run(main())
