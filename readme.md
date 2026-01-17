# VodkaDiscordPy (VodkaBot)

A feature-rich Discord bot built with `discord.py`, designed for fun and server utility.

## Features

- **Welcome & Leave Messages**: Automatically greets new members and bids farewell to those who leave.
- **Dice Roller**: Roll various dice (d4, d6, d8, d10, d12, d20, d100) with the `/roll` command.
- **Role Management**: Interactive menu for users to self-assign color roles and hobby roles.
- **Admin Tools**:
    - `/ping`: Check bot latency (Admin only).
    - `/rolemenu`: Spawn the role selection menu (Admin only).
- **Fun Commands**:
    - `/secret`: Check for secret role ownership.
    - Context-aware replies (e.g., mention "i love vodka").
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

- `main.py`: Entry point of the bot. Handles startup, event listeners, and global commands.
- `cogs/`: Directory containing Cog extensions.
    - `pingauth.py`: Latency command with role-based restrictions.
    - `roles.py`: Persistent role assignment view (Self-assignable roles).
    - `testcommands.py`: Experimental and secret commands.
- `docs/`: Detailed documentation for specific components.

For more details on the Cogs, see [Cogs Documentation](docs/cogs.md).
