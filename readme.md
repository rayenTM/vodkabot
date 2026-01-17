# VodkaDiscordPy (VodkaBot) v2.0

A feature-rich Discord bot built with `discord.py`, designed for fun, server utility, and community engagement.

## Features

- **Leveling System**: XP tracking, level-up notifications, and configurable role rewards.
- **Minigames**:
    - **Horsele**: A horse-themed Wordle-style guessing game (`/horsele`).
    - **Dice Roller**: Roll various dice (d4-d100) with `/roll`.
- **Role Management**: Interactive menus for users to self-assign color roles, pronouns, and hobby roles.
- **Admin Dashboard**: Centralized control panel (`/admin`) to manage bot settings, levels, and roles.
- **Welcome & Leave Messages**: Automatically greets new members and bids farewell.
- **Fun Commands**:
    - `/secret`: Check for secret role ownership.
    - Context-aware replies.
- **About Command**: `/about` displays bot information and credits.

## Setup Instructions

### Prerequisites
- Python 3.9+
- A Discord Bot Token (from the [Discord Developer Portal](https://discord.com/developers/applications))
- Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/rayenTM/vodkabot.git
    cd vodka-discord-bot
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the root directory and add the following:
    ```env
    DISCORD_TOKEN=your_discord_bot_token
    GUILD_ID=your_guild_id
    WELCOME_CHANNEL_ID=your_welcome_channel_id
    SUGGESTION_CHANNEL_ID=your_suggestion_channel_id
    OWNER_ID=your_user_id
    SECRET_ROLE=role_id_for_secret_commands
    ```

5.  **Run the bot:**
    ```bash
    python main.py
    ```

### Running with Docker

1.  **Build the image:**
    ```bash
    docker-compose build
    ```

2.  **Run the container:**
    ```bash
    docker-compose up -d
    ```

## Project Structure

- `main.py`: Entry point. Handles startup and global commands.
- `cogs/`:
    - `admin_menu.py`: Centralized admin dashboard.
    - `levels.py`: Leveling system and XP logic.
    - `roles.py`: Persistent role assignment views.
    - `horsele.py`: Horse Wordle minigame.
    - `pingauth.py`: Latency command (legacy admin tools).
    - `testcommands.py`: Experimental commands.
- `docs/`: Detailed documentation.

For more details on the Cogs, see [Cogs Documentation](docs/cogs.md).
