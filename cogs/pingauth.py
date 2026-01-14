import discord
from discord import app_commands
from discord.ext import commands
import os

secret_role = int(os.getenv('SECRET_ROLE'))

class PingAuth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Logged in as {self.bot.user} (ID: {self.bot.user.id}) in cog {self.__class__.__name__}')

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # verifying if the user has the role
        role = discord.utils.get(interaction.user.roles, id=secret_role)
        if role:
            return True
        else:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return False
    

    @app_commands.command(name="ping", description="Sends the bot's latency (ping) in milliseconds. Requires Admin Role.")
    async def ping(self, interaction: discord.Interaction):
        """
        Sends the bot's latency (ping) in milliseconds. Requires Admin Role.

    This command is useful for checking the bot's reaction time and connection status.
    """
        ping_embed = discord.Embed(title="Ping", description=f"🏓 {round(self.bot.latency * 1000)} ms.", color=discord.Color.green())
        await interaction.response.send_message(embed=ping_embed)

async def setup(bot):
    await bot.add_cog(PingAuth(bot))




### DEPRECATED COMMANDS ###

    # @commands.command()
    # async def cogping(self, ctx): # Pass both self and ctx, no error but commmand doesn't work
    #     """
    #     Sends the bot's latency (ping) in milliseconds. Requires Admin Role.

    # This command is useful for checking the bot's reaction time and connection status.
    # """
    #     ping_embed = discord.Embed(title="Ping", description=f"🏓 {round(self.bot.latency * 1000)} ms.", color=discord.Color.green())
    #     await ctx.send(embed=ping_embed)
