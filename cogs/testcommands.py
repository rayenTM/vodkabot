import discord
from discord import app_commands
from discord.ext import commands
import os

secret_role = int(os.getenv('SECRET_ROLE'))

class SecretAuth(commands.Cog):
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
    
    @app_commands.command(name="secret", description="This command checks if you have the required secret role.")
    async def secret(self, interaction: discord.Interaction):
        """This command checks if you have the required secret role.""" # This describes the command on client interface
        await interaction.response.send_message("You have the secret role!")


    @commands.hybrid_command()
    async def test(self, ctx):
        await ctx.send("This is a hybrid command!")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Don't respond to ourselves
        if message.author == self.bot.user:
            return
            
        if "i love vodka" in message.content.lower():
            await message.channel.send(f"i love vodka too {message.author.mention}!")
        elif "i hate vodka" in message.content.lower():
            # await message.delete() DELETED FOR NOW, MIGHT ADD BACK LATER
            await message.channel.send(f"what are you talking about, {message.author.mention}!?")
        
        # NOTE: Do NOT call bot.process_commands(message) here.
        # Event listeners run *in addition* to the main bot logic.
        # If you call it here, commands might run twice!

async def setup(bot):
    await bot.add_cog(SecretAuth(bot))