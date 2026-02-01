import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
import math
import time

# Database file path
DB_FILE = "/app/data/levels.db" if os.path.exists("/app/data") else "./data/levels.db"

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.cooldowns = {} # user_id -> timestamp

    def get_xp_for_next_level(self, current_level: int) -> int:
        """
        Quadratic Formula: 5 * (L^2) + 50 * L + 100
        L=1 -> 155
        L=2 -> 220
        L=10 -> 1100
        """
        return 5 * (current_level ** 2) + 50 * current_level + 100

    def get_total_xp_for_level(self, target_level: int) -> int:
        """Sum of XP needed for all levels up to target_level - 1"""
        total = 0
        for i in range(1, target_level):
            total += self.get_xp_for_next_level(i)
        return total

    # --- Public Admin Methods (API) ---

    # --- Helper Methods ---

    def calculate_xp_for_level(self, level: int) -> int:
        """
        Calculates the TOTAL cumulative XP required to reach a specific level.
        Uses the MEE6 formula: Sum of (5*L^2 + 50*L + 100) for L=0 to level-1.
        """
        total_xp = 0
        for i in range(level):
            total_xp += 5 * (i ** 2) + 50 * i + 100
        return total_xp

    def calculate_level_from_xp(self, xp: int) -> int:
        """
        Calculates the level corresponding to a given amount of XP.
        """
        level = 0
        while True:
            xp_needed = 5 * (level ** 2) + 50 * level + 100
            if xp >= xp_needed:
                xp -= xp_needed
                level += 1
            else:
                return level

    def calculate_xp_step(self, level: int) -> int:
        """Returns the XP required to go from current level to next."""
        return 5 * (level ** 2) + 50 * level + 100

    # --- Public Admin Methods (API) ---

    async def admin_give_xp(self, user_id: int, guild_id: int, amount: int):
        """Adds (or removes) XP and returns the new total XP."""
        await self.db.execute("""
            INSERT INTO users (user_id, guild_id, xp, level)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + ?
        """, (user_id, guild_id, amount, amount))
        await self.db.commit()
        
        async with self.db.execute("SELECT xp FROM users WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                new_xp = row['xp']
                correct_level = self.calculate_level_from_xp(new_xp)
                await self.db.execute("UPDATE users SET level = ? WHERE user_id = ? AND guild_id = ?", (correct_level, user_id, guild_id))
                await self.db.commit()
                return new_xp
            return 0

    async def admin_set_level(self, user_id: int, guild_id: int, level: int):
        """Sets a user's level and resets XP to minimum for that level."""
        required_xp = self.calculate_xp_for_level(level)
            
        await self.db.execute("""
            INSERT INTO users (user_id, guild_id, xp, level)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = ?, level = ?
        """, (user_id, guild_id, required_xp, level, required_xp, level))
        await self.db.commit()
        return required_xp

    async def admin_sync_xp(self, channel, limit: int = 1000) -> int:
        """Scans channel history and backfills XP. Returns count of users updated."""
        user_counts = {}
        async for message in channel.history(limit=limit):
            if message.author.bot: continue
            uid = message.author.id
            user_counts[uid] = user_counts.get(uid, 0) + 1
            
        if not user_counts: return 0

        for user_id, count in user_counts.items():
            xp_to_add = count * 10
            await self.db.execute("""
                INSERT INTO users (user_id, guild_id, xp, level)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + ?
            """, (user_id, channel.guild.id, xp_to_add, xp_to_add))
            
            # Recalculate level to ensure it matches new XP
            async with self.db.execute("SELECT xp FROM users WHERE user_id = ? AND guild_id = ?", (user_id, channel.guild.id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    new_xp = row['xp']
                    # Formula: MEE6
                    correct_level = self.calculate_level_from_xp(new_xp)
                    await self.db.execute("UPDATE users SET level = ? WHERE user_id = ? AND guild_id = ?", (correct_level, user_id, channel.guild.id))

        await self.db.commit()
        return len(user_counts)

    async def admin_add_reward(self, guild_id: int, level: int, role_id: int):
        """Adds a level reward."""
        await self.db.execute("""
            INSERT INTO level_rewards (guild_id, level, role_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, level) DO UPDATE SET role_id = ?
        """, (guild_id, level, role_id, role_id))
        await self.db.commit()

    async def admin_remove_reward(self, guild_id: int, level: int):
        """Removes a level reward."""
        await self.db.execute("DELETE FROM level_rewards WHERE guild_id = ? AND level = ?", (guild_id, level))
        await self.db.commit()

    async def get_rewards_config(self, guild_id: int):
        """Returns list of dicts {level, role_id}."""
        async with self.db.execute("SELECT level, role_id FROM level_rewards WHERE guild_id = ? ORDER BY level ASC", (guild_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"level": r['level'], "role_id": r['role_id']} for r in rows]

    async def get_guild_xp_rate(self, guild_id: int) -> int:
        """Fetches the XP rate for a guild, defaulting to 10."""
        async with self.db.execute("SELECT xp_rate FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
            return row['xp_rate'] if row else 10

    async def set_guild_xp_rate(self, guild_id: int, rate: int):
        """Sets the XP rate for a guild."""
        await self.db.execute("""
            INSERT INTO guild_settings (guild_id, xp_rate)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET xp_rate = ?
        """, (guild_id, rate, rate))
        await self.db.commit()


    async def cog_load(self):
        """
        Called when the Cog is loaded. We set up the database here.
        This is an Async operation, which is why we use aiosqlite.
        """
        # Connect to the SQLite database
        # This creates the file if it doesn't exist.
        
        # Ensure directory exists
        db_dir = os.path.dirname(DB_FILE)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self.db = await aiosqlite.connect(DB_FILE)
        
        # Enable row factory to get results as accessible objects/dicts instead of just tuples
        self.db.row_factory = aiosqlite.Row

        # Create the table if it doesn't exist
        # CHECK: We use IF NOT EXISTS so this is safe to run every time.
        # columns:
        #   user_id: The Discord User ID (Primary Key - must be unique)
        #   guild_id: The Server ID (Composite key with user usually, but for simplicity we filter by it)
        #   xp: Total experience points
        #   level: Current level
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                guild_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        # Create table for level rewards
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS level_rewards (
                guild_id INTEGER,
                level INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, level)
            )
        """)

        # Create table for guild settings (e.g. XP rate)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                xp_rate INTEGER DEFAULT 10,
                xp_cooldown INTEGER DEFAULT 10
            )
        """)

        # Migration: Add xp_cooldown column if it doesn't exist (for existing DBs)
        try:
            await self.db.execute("ALTER TABLE guild_settings ADD COLUMN xp_cooldown INTEGER DEFAULT 10")
        except Exception:
            pass # Column likely already exists
        
        
        await self.db.commit()
        print("Levels Cog: Database connected and table verified.")

    async def cog_unload(self):
        """Close the database connection when the Cog is unloaded"""
        if self.db:
            await self.db.close()

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listen to every message to award XP.
        """
        # 1. Ignore bots (including ourselves) to prevent infinite loops
        if message.author.bot:
            return
        
        # 2. Ignore DMs
        if not message.guild:
            return

        # --- Cooldown Check ---
        now = time.time()
        
        # Fetch guild cooldown setting
        xp_cooldown = 10 # Default
        async with self.db.execute("SELECT xp_cooldown FROM guild_settings WHERE guild_id = ?", (message.guild.id,)) as cursor:
            row = await cursor.fetchone()
            if row and row['xp_cooldown'] is not None:
                xp_cooldown = row['xp_cooldown']

        last_xp = self.cooldowns.get(message.author.id, 0)
        if now - last_xp < xp_cooldown:
            return
            
        self.cooldowns[message.author.id] = now
        # ----------------------

        # 3. Add XP
        # We award customized XP per message (default 10).
        xp_gain = await self.get_guild_xp_rate(message.guild.id)
        
        # SQL: UPSERT (Insert or Update)
        # We try to Insert the user. If they exist (Conflict on Primary Key), we just Update their XP.
        cursor = await self.db.execute("""
            INSERT INTO users (user_id, guild_id, xp, level)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = xp + ?
        """, (message.author.id, message.guild.id, xp_gain, xp_gain))
        
        # 4. Check for Level Up
        # Just for efficiency, we only fetch the new values to check level up
        await self.db.commit()
        
        async with self.db.execute("""
            SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?
        """, (message.author.id, message.guild.id)) as cursor:
            row = await cursor.fetchone()
            if row:
                current_xp = row['xp']
                current_level = row['level']
                
                # Check actual level based on XP
                calc_level = self.calculate_level_from_xp(current_xp)
                
                if calc_level > current_level:
                    await self.db.execute("UPDATE users SET level = ? WHERE user_id = ? AND guild_id = ?", (calc_level, message.author.id, message.guild.id))
                    await self.db.commit()
                    
                    await message.channel.send(f"🎉 {message.author.mention} has leveled up to **Level {calc_level}**!")

                    # Check for Role Rewards
                    async with self.db.execute("SELECT role_id FROM level_rewards WHERE guild_id = ? AND level = ?", (message.guild.id, calc_level)) as cursor:
                        reward_row = await cursor.fetchone()
                        if reward_row:
                            role_id = reward_row['role_id']
                            role = message.guild.get_role(role_id)
                            if role:
                                try:
                                    await message.author.add_roles(role)
                                    await message.channel.send(f"🎁 You've been awarded the **{role.name}** role!")
                                except discord.Forbidden:
                                    await message.channel.send("⚠️ I tried to give you a reward role, but I don't have permission! Please check my role hierarchy.")
                                except discord.HTTPException:
                                    pass # Ignore other errors for now

    # --- Commands ---

    @app_commands.command(name="rank", description="Check your current rank and XP")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        """
        Fetch data from SQLite and display it.
        """
        target = member or interaction.user
        
        async with self.db.execute("""
            SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?
        """, (target.id, interaction.guild.id)) as cursor:
            row = await cursor.fetchone()
            
        if row:
            xp = row['xp']
            level = row['level']
            
            # Show progress to next level
            # Calculate XP needed for NEXT level (step cost)
            step_cost = self.get_xp_for_next_level(level)
            
            # Calculate Total XP at start of current level
            current_level_start_xp = self.get_total_xp_for_level(level)
            
            # Calculate XP gained WITHIN this level
            xp_in_this_level = xp - current_level_start_xp
            
            # Progress Bar Calculation
            # Constraint: 0 <= percent <= 1
            if step_cost > 0:
                progress_percent = min(max(xp_in_this_level / step_cost, 0), 1)
            else:
                progress_percent = 1.0

            bar_length = 15
            filled_length = int(bar_length * progress_percent)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            
            embed = discord.Embed(title=f"Rank: {target.display_name}", color=discord.Color.blue())
            embed.set_thumbnail(url=target.avatar.url if target.avatar else None)
            
            embed.add_field(name="Level", value=str(level), inline=True)
            embed.add_field(name="XP Progress", value=f"{xp_in_this_level} / {step_cost}", inline=True)
            
            # Progress Bar Field
            embed.add_field(name="Progress", value=f"`{bar}` {int(progress_percent * 100)}%", inline=False)
             
            embed.set_footer(text=f"Total Lifetime XP: {xp}")
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {target.display_name} hasn't sent any messages yet!", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the top 10 chatters")
    async def leaderboard(self, interaction: discord.Interaction):
        """
        SQL makes sorting easy using 'ORDER BY'.
        """
        async with self.db.execute("""
            SELECT user_id, xp, level FROM users 
            WHERE guild_id = ? 
            ORDER BY xp DESC 
            LIMIT 10
        """, (interaction.guild.id,)) as cursor:
            rows = await cursor.fetchall()
            
        if not rows:
            await interaction.response.send_message("No data yet!", ephemeral=True)
            return

        embed = discord.Embed(title="🏆 Server Leaderboard", color=discord.Color.gold())
        description = ""
        
        for index, row in enumerate(rows, start=1):
            user_id = row['user_id']
            # We try to fetch member from cache mainly
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            
            description += f"**{index}. {name}** - Lvl {row['level']} ({row['xp']} XP)\n"
            
        embed.description = description
        await interaction.response.send_message(embed=embed)
    @app_commands.command(name="sync_xp", description="[Admin] Scan chat history to backfill XP")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_xp(self, interaction: discord.Interaction, limit: int = 1000):
        """
        scans the current channel history and awards XP retroactively.
        """
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"🔄 Starting sync... Scanning last {limit} messages. This might take a moment.")
        
        count_updated = await self.admin_sync_xp(interaction.channel, limit)

        await interaction.followup.send(f"✅ Sync Complete! Updated XP for {count_updated} users based on {limit} messages.")
    # --- Level Management Commands ---
    
    level_group = app_commands.Group(name="level", description="Manage level rewards")

    @level_group.command(name="set_reward", description="Set a role reward for a level")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def set_reward(self, interaction: discord.Interaction, level: int, role: discord.Role):
        """
        Configure a role to be given when a user reaches a specific level.
        """
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"❌ I cannot assign the role {role.mention} because it is higher than or equal to my highest role.", ephemeral=True)
            return

        await self.admin_add_reward(interaction.guild.id, level, role.id)
        
        await interaction.response.send_message(f"✅ Level {level} reward set to {role.mention}!", ephemeral=True)

    @level_group.command(name="remove_reward", description="Remove a reward for a level")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def remove_reward(self, interaction: discord.Interaction, level: int):
        """
        Remove a configured role reward for a specific level.
        """
        await self.admin_remove_reward(interaction.guild.id, level)
        
        await interaction.response.send_message(f"✅ Removed reward for Level {level}.", ephemeral=True)

    @level_group.command(name="rewards", description="List all level rewards")
    async def list_rewards(self, interaction: discord.Interaction):
        """
        List all configured rewards for this server.
        """
        rows = await self.get_rewards_config(interaction.guild.id)
            
        if not rows:
            await interaction.response.send_message("No level rewards configured yet.", ephemeral=True)
            return

        embed = discord.Embed(title="🎁 Level Rewards", color=discord.Color.purple())
        description = ""
        for row in rows:
            role = interaction.guild.get_role(row['role_id'])
            role_name = role.mention if role else f"Deleted Role ({row['role_id']})"
            description += f"**Level {row['level']}**: {role_name}\n"
            
        embed.description = description
        await interaction.response.send_message(embed=embed)

    @level_group.command(name="give_xp", description="Give (or take) XP from a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def give_xp(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """
        Manually add or remove XP from a user. 
        """
        if member.bot:
            await interaction.response.send_message("🤖 Bots don't need XP!", ephemeral=True)
            return

        new_xp = await self.admin_give_xp(member.id, interaction.guild.id, amount)
        await interaction.response.send_message(f"✅ Adjusted {member.mention}'s XP by {amount}. New Total: {new_xp}", ephemeral=True)

    @level_group.command(name="set_level", description="Set a user's level directly")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_level(self, interaction: discord.Interaction, member: discord.Member, level: int):
        """
        Force set a user's level. This will reset their XP to the minimum required for that level.
        """
        if level < 1:
            await interaction.response.send_message("❌ Level must be at least 1.", ephemeral=True)
            return
            
        required_xp = await self.admin_set_level(member.id, interaction.guild.id, level)
        
        await interaction.response.send_message(f"✅ Set {member.mention} to **Level {level}** (XP set to {required_xp}).", ephemeral=True)

    @level_group.command(name="set_xp_rate", description="Set XP per message. Leave empty to reset to default (10).")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_xp_rate(self, interaction: discord.Interaction, amount: int = None):
        """
        Configure how much XP is given per message for this server.
        If amount is not provided, resets to default (10).
        """
        if amount is None:
             await self.set_guild_xp_rate(interaction.guild.id, 10)
             await interaction.response.send_message("✅ XP Rate **reset** to default (**10 XP** per message).", ephemeral=True)
             return

        if amount < 1:
            await interaction.response.send_message("❌ XP rate must be at least 1.", ephemeral=True)
            return

        await self.set_guild_xp_rate(interaction.guild.id, amount)
        await interaction.response.send_message(f"✅ XP Rate set to **{amount} XP** per message.", ephemeral=True)

    @level_group.command(name="set_cooldown", description="Set XP cooldown in seconds. Default 10.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_cooldown(self, interaction: discord.Interaction, seconds: int = 10):
        """
        Configure the cooldown between XP gains (in seconds).
        """
        if seconds < 0:
            await interaction.response.send_message("❌ Cooldown cannot be negative.", ephemeral=True)
            return

        await self.db.execute("""
            INSERT INTO guild_settings (guild_id, xp_rate, xp_cooldown)
            VALUES (?, 10, ?)
            ON CONFLICT(guild_id) DO UPDATE SET xp_cooldown = ?
        """, (interaction.guild.id, seconds, seconds))
        await self.db.commit()
        
        await interaction.response.send_message(f"✅ XP Cooldown set to **{seconds} seconds**.", ephemeral=True)

    @level_group.command(name="reset", description="Reset a user's XP to the base requirement for their current level")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, interaction: discord.Interaction, member: discord.Member):
        """
        Resets a user's XP to the exact amount required for their current level.
        Useful for fixing glitched XP states.
        """
        if member.bot:
            await interaction.response.send_message("🤖 Bots don't need XP resets!", ephemeral=True)
            return

        # Fetch current level
        async with self.db.execute("SELECT level FROM users WHERE user_id = ? AND guild_id = ?", (member.id, interaction.guild.id)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            await interaction.response.send_message(f"❌ {member.display_name} has no data to reset.", ephemeral=True)
            return

        current_level = row['level']
        
        # Reuse set_level to force the XP reset
        required_xp = await self.admin_set_level(member.id, interaction.guild.id, current_level)
        
        await interaction.response.send_message(f"✅ Reset {member.mention}'s XP to **{required_xp}** (Base for Level {current_level}).", ephemeral=True)

    @level_group.command(name="recalculate", description="Recalculate a user's level based on their XP")
    @app_commands.checks.has_permissions(administrator=True)
    async def recalculate(self, interaction: discord.Interaction, member: discord.Member):
        """
        Recalculates the user's level based on their current XP using the quadratic formula.
        """
        if member.bot:
            await interaction.response.send_message("🤖 Bots don't have levels!", ephemeral=True)
            return

        async with self.db.execute("SELECT xp FROM users WHERE user_id = ? AND guild_id = ?", (member.id, interaction.guild.id)) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            await interaction.response.send_message(f"❌ {member.display_name} has no data.", ephemeral=True)
            return

        current_xp = row['xp']
        current_xp = row['xp']
        # Formula: MEE6
        correct_level = self.calculate_level_from_xp(current_xp)

        await self.db.execute("UPDATE users SET level = ? WHERE user_id = ? AND guild_id = ?", (correct_level, member.id, interaction.guild.id))
        await self.db.commit()

        await interaction.response.send_message(f"✅ Recalculated {member.mention}: **Level {correct_level}** ({current_xp} XP).", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Levels(bot))
