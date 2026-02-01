import discord
from discord import app_commands
from discord.ext import commands
from typing import List
import json
import random
import os

DATA_FILE = "data/wordle_words.json"

class Wordle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.words = self.load_words()

    def load_words(self) -> List[str]:
        if not os.path.exists(DATA_FILE):
            print(f"Warning: {DATA_FILE} not found. Using fallback list.")
            return ["HORSE", "APPLE", "HEART"]
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading words: {e}")
            return ["HORSE"]

    @app_commands.command(name="wordle", description="Play a game of Wordle with a random word!")
    async def wordle_command(self, interaction: discord.Interaction):
        if not self.words:
             await interaction.response.send_message("Word list is empty! validation failed.", ephemeral=True)
             return
             
        target_word = random.choice(self.words)
        view = WordleView(target_word)
        await interaction.response.send_message(embed=view.get_embed(), view=view)


class WordleView(discord.ui.View):
    def __init__(self, target_word: str):
        super().__init__(timeout=None)
        self.target_word = target_word.upper()
        self.guesses: List[str] = []
        self.ended = False

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Wordle", description="Guess the 5-letter word!", color=discord.Color.blue())
        
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
            if self.guesses and self.guesses[-1] == self.target_word:
                embed.set_footer(text=f"You Won! The word was {self.target_word} 🎉")
                embed.color = discord.Color.green()
            else:
                embed.set_footer(text=f"You Lost! The word was {self.target_word}.")
                embed.color = discord.Color.red()
                
        return embed

    def format_guess(self, guess: str) -> str:
        # Frequency counter for the target word to handle duplicates correctly
        target_freq = {}
        for char in self.target_word:
            target_freq[char] = target_freq.get(char, 0) + 1
            
        result = [""] * 5
        guess_upper = guess.upper()
        
        # First Pass: Green (Correct position)
        for i in range(5):
            letter = guess_upper[i]
            if letter == self.target_word[i]:
                result[i] = "🟩"
                target_freq[letter] -= 1
        
        # Second Pass: Yellow (Wrong position but in word)
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

    @discord.ui.button(label="Guess", style=discord.ButtonStyle.primary, emoji="❓")
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
        placeholder="WORDL",
        required=True,
        max_length=5,
        min_length=5
    )

    def __init__(self, view: WordleView):
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
        if guess == self.game_view.target_word:
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
    await bot.add_cog(Wordle(bot))
