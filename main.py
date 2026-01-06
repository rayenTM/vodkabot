import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os


load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.event
async def on_member_join(member):
    await member.send(f"Welcome to the server, {member.name}!")

@bot.hybrid_command()
async def test(ctx):
    await ctx.send("This is a hybrid command!")



@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if "i love vodka" in message.content.lower():
        await message.channel.send(f"i love vodka too {message.author.mention}!")
    elif "i hate vodka" in message.content.lower():
        await message.delete()
        await message.channel.send(f"what are you talking about, {message.author.mention}!")
    await bot.process_commands(message) # Needed, or else the commands won't work


secret_role = "Admin"

@bot.hybrid_command()
@commands.has_role(secret_role)
async def secret(ctx):
    """This command checks if you have the required secret role.""" # This describes the command on client interface
    await ctx.send("You have the secret role!")

@bot.hybrid_command()
@commands.has_role(secret_role)
async def ping(ctx):
    """
    Sends the bot's latency (ping) in milliseconds.

    This command is useful for checking the bot's reaction time and connection status.
    """
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f'🏓 {latency_ms} ms.')


@bot.command() # Testing command to see if it works
async def foo(ctx, arg):
    await ctx.send(arg)



bot.run(token, log_handler=handler, log_level=logging.DEBUG)
