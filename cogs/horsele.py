import discord
from discord import app_commands
from discord.ext import commands
from typing import List

TARGET_WORD = "HORSE"

class Horsele(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="horsele", description="Play a game of Horsele! (The answer is always HORSE)")
    async def horsele_command(self, interaction: discord.Interaction):
        view = HorseleView()
        await interaction.response.send_message(embed=view.get_embed(), view=view)


class HorseleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.guesses: List[str] = []
        self.ended = False

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Horsele", description="Guess the 5-letter word!", color=discord.Color.green())
        
        board_str = ""
        for guess in self.guesses:
            line = self.format_guess(guess)
            board_str += line + "\n"
        
        # Determine how many empty rows are left
        remaining_rows = 6 - len(self.guesses)
        for _ in range(remaining_rows):
            board_str += "⬛ ⬛ ⬛ ⬛ ⬛\n"
            
        embed.description = board_str
        
        if self.ended:
            if self.guesses and self.guesses[-1] == TARGET_WORD:
                embed.set_footer(text="You Won! 🐴")
            else:
                embed.set_footer(text=f"You Lost! The word was {TARGET_WORD} (obviously).")
                
        return embed

    def format_guess(self, guess: str) -> str:
        # Use simple frequency counters for the logic (logic for duplicates)
        target_freq = {}
        for char in TARGET_WORD:
            target_freq[char] = target_freq.get(char, 0) + 1
            
        result = [""] * 5
        guess_upper = guess.upper()
        
        # First Pass: Green
        for i in range(5):
            letter = guess_upper[i]
            if letter == TARGET_WORD[i]:
                result[i] = "🟩"
                target_freq[letter] -= 1
        
        # Second Pass: Yellow
        for i in range(5):
            if result[i] != "":
                continue
                
            letter = guess_upper[i]
            if letter in target_freq and target_freq[letter] > 0:
                result[i] = "🟨"
                target_freq[letter] -= 1
            else:
                result[i] = "⬛"
                
        return " ".join(result)

    @discord.ui.button(label="Guess", style=discord.ButtonStyle.primary, emoji="🐴")
    async def guess_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ended:
            await interaction.response.send_message("The game is over!", ephemeral=True)
            return
        
        await interaction.response.send_modal(GuessModal(self))

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.danger, emoji="✖️")
    async def quit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.ended:
            await interaction.response.send_message("The game is already over.", ephemeral=True)
            return

        self.ended = True
        self.stop()
        
        # Disable buttons
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class GuessModal(discord.ui.Modal, title="Enter your guess"):
    guess_input = discord.ui.TextInput(
        label="5-Letter Word",
        style=discord.TextStyle.short,
        placeholder="HORSE",
        required=True,
        max_length=5,
        min_length=5
    )

    def __init__(self, view: HorseleView):
        super().__init__()
        self.game_view = view

    async def on_submit(self, interaction: discord.Interaction):
        guess = self.guess_input.value.upper()
        
        # Basic Validation
        if len(guess) != 5:
            await interaction.response.send_message("Must be exactly 5 letters!", ephemeral=True)
            return
            
        if not guess.isalpha():
            await interaction.response.send_message("Only letters are allowed!", ephemeral=True)
            return

        # Add guess
        self.game_view.guesses.append(guess)
        
        # Check Win/Loss
        if guess == TARGET_WORD:
            self.game_view.ended = True
            for child in self.game_view.children:
                child.disabled = True
            self.game_view.stop()
            
        elif len(self.game_view.guesses) >= 6:
            self.game_view.ended = True
            for child in self.game_view.children:
                child.disabled = True
            self.game_view.stop()
            
        await interaction.response.edit_message(embed=self.game_view.get_embed(), view=self.game_view)


async def setup(bot):
    await bot.add_cog(Horsele(bot))
